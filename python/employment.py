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
        year (int): estimates year
    """

    # Check MGRA version and raise error if not 'mgra15'
    if utils.MGRA_VERSION != "mgra15":
        raise ValueError(
            f"Employment module only works with MGRA_VERSION = 'mgra15'. "
            f"Current MGRA_VERSION is '{utils.MGRA_VERSION}'."
        )

    jobs_inputs = _get_jobs_inputs(year)
    _validate_jobs_inputs(jobs_inputs)

    jobs_outputs = _create_jobs_output(jobs_inputs)
    _validate_jobs_outputs(jobs_outputs)

    _insert_jobs(jobs_inputs, jobs_outputs)


def get_LODES_data(year: int) -> pd.DataFrame:
    """Retrieve LEHD LODES data for a specified year and split naics_code 72 into
        721 and 722 using split percentages.

    Args:
        year (int): The year for which to retrieve LEHD LODES data.
    Returns:
        pd.DataFrame: A DataFrame containing the combined LEHD LODES data with naics
    """

    with utils.LEHD_ENGINE.connect() as con:
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

    # Separate naics_code 72 from other industries
    lodes_72 = lodes_data[lodes_data["naics_code"] == "72"].copy()
    lodes_other = lodes_data[lodes_data["naics_code"] != "72"].copy()

    # Join naics_code 72 data with split percentages
    lodes_72_split = lodes_72.merge(split_naics_72, on="block", how="left")

    # Create rows for naics_code 721
    lodes_721 = lodes_72_split[["year", "block"]].copy()
    lodes_721["naics_code"] = "721"
    lodes_721["jobs"] = lodes_72_split["jobs"] * lodes_72_split["pct_721"]

    # Create rows for naics_code 722
    lodes_722 = lodes_72_split[["year", "block"]].copy()
    lodes_722["naics_code"] = "722"
    lodes_722["jobs"] = lodes_72_split["jobs"] * lodes_72_split["pct_722"]

    # Combine all data
    combined_data = pd.concat([lodes_other, lodes_721, lodes_722], ignore_index=True)
    combined_data = combined_data[["year", "block", "naics_code", "jobs"]]

    return combined_data


def aggregate_lodes_to_mgra(
    combined_data: pd.DataFrame, xref: pd.DataFrame, year: int
) -> pd.DataFrame:
    """Aggregate LODES data to MGRA level using allocation percentages.

    Args:
        combined_data (pd.DataFrame): LODES data with columns: year, block, naics_code, jobs
        xref (pd.DataFrame): Crosswalk with columns: block, mgra, allocation_pct
        year (int): The year for which to aggregate data

    Returns:
        pd.DataFrame: Aggregated data at MGRA level with columns: year, mgra, naics_code, jobs
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
    jobs = mgra_data.merge(pd.DataFrame({"naics_code": unique_industries}), how="cross")
    jobs["year"] = year
    jobs = jobs[["year", "mgra", "naics_code"]]

    # Join combined_data to xref and calculate allocated jobs
    lehd_to_mgra = combined_data.merge(xref, on="block", how="inner")
    lehd_to_mgra["value"] = lehd_to_mgra["jobs"] * lehd_to_mgra["allocation_pct"]

    # Join summed data to jobs, keeping all MGRAs and naics codes
    jobs = jobs.merge(
        lehd_to_mgra.groupby(["year", "mgra", "naics_code"], as_index=False)[
            "value"
        ].sum(),
        on=["year", "mgra", "naics_code"],
        how="left",
    )
    jobs["value"] = jobs["value"].fillna(0)
    jobs["run_id"] = utils.RUN_ID
    jobs = jobs[["run_id", "year", "mgra", "naics_code", "value"]]

    return jobs


def _get_jobs_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get input data related to jobs for a specified year.

    Args:
        year (int): The year for which to retrieve input data.
    Returns:
        dict[str, pd.DataFrame]: A dictionary containing input DataFrames related to jobs.
    """
    # Store results here
    jobs_inputs = {}

    jobs_inputs["LODES_data"] = get_LODES_data(year)

    with utils.LEHD_ENGINE.connect() as con:
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

    jobs_inputs["lehd_jobs"] = aggregate_lodes_to_mgra(
        jobs_inputs["LODES_data"], jobs_inputs["xref_block_to_mgra"], year
    )

    return jobs_inputs


def _validate_jobs_inputs(jobs_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate the jobs input data"""
    # LODES data does not have any row_count check as the number of rows can vary by
    # year because blocks are only included in LEHD LODES dataif there are any jobs
    # present in the block. Only place this explanation exists is in a note in this webpage:
    # https://lehd.ces.census.gov/data/lehd-code-samples/sections/lodes/basic_examples.html
    tests.validate_data(
        "LEHD LODES data",
        jobs_inputs["LODES_data"],
        negative={},
        null={},
    )
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
        original_data (pd.DataFrame): LEHD LODES data at MGRA level.
        control_totals (pd.DataFrame): Employment control totals from QCEW.
        generator (np.random.Generator): NumPy random number generator.

    Returns:
        pd.DataFrame: Controlled employment data.
    """
    jobs_outputs = {}
    # Create a copy of original_data for controlled results
    jobs_outputs["results"] = jobs_inputs["lehd_jobs"].copy()

    # Get unique industry codes
    naics_codes = jobs_inputs["lehd_jobs"]["naics_code"].unique()

    # Order jobs_inputs["lehd_jobs"] by "mgra", "naics_code"
    jobs_inputs["lehd_jobs"] = jobs_inputs["lehd_jobs"].sort_values(
        by=["mgra", "naics_code"]
    )

    # Apply integerize_1d to each industry code
    for naics_code in naics_codes:
        # Filter original data for this industry
        industry_mask = jobs_inputs["lehd_jobs"]["naics_code"] == naics_code

        # Get control value for this industry
        control_value = jobs_inputs["control_totals"][
            jobs_inputs["control_totals"]["naics_code"] == naics_code
        ]["value"].iloc[0]

        # Apply integerize_1d and update controlled_data
        jobs_outputs["results"].loc[industry_mask, "value"] = utils.integerize_1d(
            data=jobs_inputs["lehd_jobs"].loc[industry_mask, "value"],
            control=control_value,
            methodology="weighted_random",
            generator=generator,
        )

    return jobs_outputs


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
