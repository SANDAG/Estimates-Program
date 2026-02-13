# Container for the Employment module. See the Estimates-Program wiki page for
# more details: Wiki page TBD

import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)


def run_employment(year: int):
    """Control function to create jobs data by naics_code (NAICS) at the MGRA level.

    Get the LEHD LODES data, aggregate to the MGRA level using the block to MGRA
    crosswalk, then apply control totals from QCEW using integerization.

    Functionality is split apart for code encapsulation (function inputs not included):
        _get_jobs_inputs - Get all input data related to jobs, including LODES data,
            block to MGRA crosswalk, and control totals from QCEW. Then process the
            LODES data to the MGRA level by naics_code.
        _validate_jobs_inputs - Validate the input tables from the above function
        _create_jobs_output - Apply control totals to employment data using
            utils.integerize_1d() and create output table
        _validate_jobs_outputs - Validate the output table from the above function
        _insert_jobs - Store input and output data related to jobs to the database.

    Args:
        year: estimates year
    """

    jobs_inputs = _get_jobs_inputs(year)
    _validate_jobs_inputs(jobs_inputs)

    jobs_outputs = _create_jobs_output(jobs_inputs)
    _validate_jobs_outputs(jobs_outputs)

    _insert_jobs(jobs_inputs, jobs_outputs)


def _get_lodes_data(year: int) -> pd.DataFrame:
    """Retrieve LEHD LODES data for a specified year and split naics_code 72 into
        721 and 722 using split percentages.

    Args:
        year: The year for which to retrieve LEHD LODES data.
    Returns:
        combined LEHD LODES data with naics
    """

    with utils.ESTIMATES_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "employment/get_lodes_data.sql") as file:
            lodes_data = utils.read_sql_query_fallback(
                max_lookback=2,
                sql=sql.text(file.read()),
                con=con,
                params={"year": year},
            )

    with utils.GIS_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "employment/get_naics72_split.sql") as file:
            split_naics_72 = utils.read_sql_query_fallback(
                max_lookback=3,
                sql=sql.text(file.read()),
                con=con,
                params={"year": year},
            )

    # Split naics_code 72 and combine with other industries
    lodes_72_split = lodes_data.loc[lambda df: df["naics_code"] == "72"].merge(
        split_naics_72, on="block", how="left"
    )

    combined_data = pd.concat(
        [
            lodes_data.loc[lambda df: df["naics_code"] != "72"],
            lodes_72_split.assign(
                naics_code="721", jobs=lambda df: df["jobs"] * df["pct_721"]
            ),
            lodes_72_split.assign(
                naics_code="722", jobs=lambda df: df["jobs"] * df["pct_722"]
            ),
        ],
        ignore_index=True,
    )[["year", "block", "naics_code", "jobs"]]

    return combined_data


def _aggregate_lodes_to_mgra(
    combined_data: pd.DataFrame, xref: pd.DataFrame, year: int
) -> pd.DataFrame:
    """Aggregate LODES data to MGRA level using allocation percentages.

    Args:
        combined_data: LODES data with columns: year, block, naics_code, jobs
        xref: Crosswalk with columns: block, mgra, allocation_pct
        year: The year for which to aggregate data

    Returns:
        Aggregated data at MGRA level with columns: run_id, year, mgra,
            naics_code, value
    """
    # Get MGRA data from SQL
    with utils.ESTIMATES_ENGINE.connect() as con:
        mgra_data = pd.read_sql_query(
            sql=sql.text(
                """
                SELECT DISTINCT [mgra]
                FROM [inputs].[mgra]
                WHERE run_id = :run_id
                ORDER BY [mgra]
                """
            ),
            con=con,
            params={"run_id": utils.RUN_ID},
        )

    # Get unique industry codes and cross join with MGRA data
    unique_industries = combined_data["naics_code"].unique()
    jobs = (
        mgra_data.merge(pd.DataFrame({"naics_code": unique_industries}), how="cross")
        .assign(year=year)
        .merge(
            combined_data.merge(xref, on="block", how="inner")
            .assign(value=lambda df: df["jobs"] * df["allocation_pct"])
            .groupby(["year", "mgra", "naics_code"], as_index=False)["value"]
            .sum(),
            on=["year", "mgra", "naics_code"],
            how="left",
        )
        .fillna({"value": 0})
        .assign(run_id=utils.RUN_ID)[["run_id", "year", "mgra", "naics_code", "value"]]
    )

    return jobs


def _get_jobs_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get input data related to jobs for a specified year.

    Args:
        year: The year for which to retrieve input data.
    Returns:
        input DataFrames related to jobs.
    """
    # Store results here
    jobs_inputs = {}

    jobs_inputs["lodes_data"] = _get_lodes_data(year)

    with utils.ESTIMATES_ENGINE.connect() as con:
        # get crosswalk from Census blocks to MGRAs
        with open(utils.SQL_FOLDER / "employment/xref_block_to_mgra.sql") as file:
            jobs_inputs["xref_block_to_mgra"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=con,
                params={"mgra_version": utils.MGRA_VERSION},
            )

        # get regional employment control totals from QCEW
        with open(utils.SQL_FOLDER / "employment/QCEW_control.sql") as file:
            jobs_inputs["control_totals"] = utils.read_sql_query_fallback(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "year": year,
                },
            )
    jobs_inputs["control_totals"]["run_id"] = utils.RUN_ID

    jobs_inputs["lehd_jobs"] = _aggregate_lodes_to_mgra(
        jobs_inputs["lodes_data"], jobs_inputs["xref_block_to_mgra"], year
    )

    return jobs_inputs


def _validate_jobs_inputs(jobs_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate the jobs input data"""
    # LODES only includes blocks with jobs therefore no row count validation performed
    # https://lehd.ces.census.gov/data/lehd-code-samples/sections/lodes/basic_examples.html
    tests.validate_data(
        "LEHD LODES data",
        jobs_inputs["lodes_data"],
        negative={},
        null={},
    )
    # No row count validation performed as xref is many-to-many
    # check
    tests.validate_data(
        "xref",
        jobs_inputs["xref_block_to_mgra"],
        negative={},
        null={},
    )
    tests.validate_data(
        "QCEW control totals",
        jobs_inputs["control_totals"],
        row_count={"key_columns": {"naics_code"}},
        negative={},
        null={},
    )
    tests.validate_data(
        "LEHD jobs at MGRA level",
        jobs_inputs["lehd_jobs"],
        row_count={"key_columns": {"mgra", "naics_code"}},
        negative={},
        null={},
    )


def _create_jobs_output(
    jobs_inputs: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Apply control totals to employment data using utils.integerize_1d().

    Args:
        jobs_inputs: A dictionary containing input DataFrames related to jobs

    Returns:
        Controlled employment data.
    """
    # Sort the input data and get unique naics codes
    sorted_jobs = jobs_inputs["lehd_jobs"].sort_values(by=["mgra", "naics_code"])
    naics_codes = sorted_jobs["naics_code"].unique()

    # Create list to store controlled values for each industry
    results = []

    # Apply integerize_1d to each naics code
    for naics_code in naics_codes:
        # Filter for this naics code
        naics_mask = sorted_jobs.query("naics_code == @naics_code")

        # Get control value and apply integerize_1d
        control_value = (
            jobs_inputs["control_totals"]
            .query("naics_code == @naics_code")["value"]
            .iloc[0]
        )

        results.append(
            naics_mask.assign(
                value=utils.integerize_1d(
                    data=naics_mask["value"],
                    control=control_value,
                    methodology="weighted_random",
                    generator=generator,
                )
            )
        )

    return {"results": pd.concat(results, ignore_index=True)}


def _validate_jobs_outputs(jobs_outputs: dict[str, pd.DataFrame]) -> None:
    """Validate the jobs output data"""
    tests.validate_data(
        "Controlled jobs data",
        jobs_outputs["results"],
        row_count={"key_columns": {"mgra", "naics_code"}},
        negative={},
        null={},
    )


def _insert_jobs(
    jobs_inputs: dict[str, pd.DataFrame], jobs_outputs: dict[str, pd.DataFrame]
) -> None:
    """Insert input and output data related to jobs to the database."""

    # Insert input and output data to database
    with utils.ESTIMATES_ENGINE.connect() as con:

        jobs_inputs["control_totals"].to_sql(
            name="controls_jobs",
            con=con,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        jobs_outputs["results"].to_sql(
            name="jobs", con=con, schema="outputs", if_exists="append", index=False
        )
