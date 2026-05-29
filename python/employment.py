# Container for the Employment module. See the Estimates-Program wiki page for
# more details: Wiki page TBD

import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)


def run_employment(year: int, debug: bool):
    """Control function to create jobs data by industry_code at the MGRA level.

    Get the LEHD LODES data, aggregate to the MGRA level using the block to MGRA
    crosswalk, then apply control totals from QCEW using integerization.

    Functionality is split apart for code encapsulation (function inputs not included):
        _get_jobs_inputs - Get all input data related to jobs, including LODES data,
            block to MGRA crosswalk, and control totals from QCEW. Then process the
            LODES data to the MGRA level by industry_code.
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

    jobs_outputs = _create_jobs_output(jobs_inputs, year)
    _validate_jobs_outputs(jobs_outputs)

    _insert_jobs(jobs_inputs, jobs_outputs, debug)


def _get_lodes_data(year: int) -> pd.DataFrame:
    """Retrieve LEHD LODES data for a specified year and split industry_code 72 into
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
                max_lookback=2,
                sql=sql.text(file.read()),
                con=con,
                params={"year": year},
            )

    # Split industry_code 72 and combine with other industries
    lodes_72_split = lodes_data.loc[lambda df: df["industry_code"] == "72"].merge(
        split_naics_72, on="block", how="left"
    )

    combined_data = pd.concat(
        [
            lodes_data.loc[lambda df: df["industry_code"] != "72"],
            lodes_72_split.assign(
                industry_code="721", jobs=lambda df: df["jobs"] * df["pct_721"]
            ),
            lodes_72_split.assign(
                industry_code="722", jobs=lambda df: df["jobs"] * df["pct_722"]
            ),
        ],
        ignore_index=True,
    )[["year", "block", "industry_code", "jobs"]]

    return combined_data


def _aggregate_lodes_to_mgra(
    combined_data: pd.DataFrame, xref: pd.DataFrame, year: int
) -> pd.DataFrame:
    """Aggregate LODES data to MGRA level using allocation percentages.

    This function allocates jobs from Census blocks to MGRAs using distributions from
    the California Employment Development Department (EDD) point-level dataset. Blocks
    with no EDD data available use a simple land area intersection to allocate jobs to
    MGRAs.

    Args:
        combined_data: LODES data with columns: year, block, industry_code, jobs
        xref: Crosswalk with columns: block, mgra, pct_edd, pct_area, edd_flag
        year: The year for which to aggregate data

    Returns:
        Aggregated data at MGRA level with columns: run_id, year, mgra,
            industry_code, value
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
    unique_industries = combined_data["industry_code"].unique()
    jobs = (
        mgra_data.merge(pd.DataFrame({"industry_code": unique_industries}), how="cross")
        .assign(year=year)
        .merge(
            combined_data.merge(xref, on="block", how="inner")
            .assign(
                value=lambda df: df["jobs"]
                * np.where(df["edd_flag"] == 1, df["pct_edd"], df["pct_area"])
            )
            .groupby(["year", "mgra", "industry_code"], as_index=False)["value"]
            .sum(),
            on=["year", "mgra", "industry_code"],
            how="left",
        )
        .fillna({"value": 0})
        .assign(run_id=utils.RUN_ID)[
            ["run_id", "year", "mgra", "industry_code", "value"]
        ]
    )

    return jobs


def _distribute_self_emp_to_mgra(
    bg_data: pd.DataFrame, xref: pd.DataFrame
) -> pd.DataFrame:
    """Distribute self-employed block group data to MGRA level using allocation
        percentages.

    Args:
        bg_data: DataFrame with block group self-employed data. Must include columns:
            year, blockgroup, industry_code, value
        xref: Crosswalk DataFrame with columns: blockgroup, mgra, flag, pct_18_64,
            pct_pop, pct_split

    Returns:
        Self-Emp Data at MGRA level with columns: run_id, year, mgra, industry_code, value
    """
    # Merge block group data to MGRA crosswalk
    merged = bg_data.merge(xref, on="blockgroup", how="inner")

    # Calculate weighted value based on flag
    merged = merged.assign(
        weighted_value=np.select(
            [
                merged["flag"] == "pct_18_64",
                merged["flag"] == "pct_pop",
                merged["flag"] == "pct_split",
            ],
            [
                merged["value"] * merged["pct_18_64"],
                merged["value"] * merged["pct_pop"],
                merged["value"] * merged["pct_split"],
            ],
            default=np.nan,
        )
    )

    if merged["weighted_value"].isna().any():
        raise ValueError(
            "Unexpected allocation flag found; expected one of {'pct_18_64', 'pct_pop', 'pct_split'}"
        )

    # Group by year, mgra, industry_code and sum, then assign run_id and reorder columns
    self_emp = (
        merged.groupby(["year", "mgra", "industry_code"], as_index=False)[
            "weighted_value"
        ]
        .sum()
        .rename(columns={"weighted_value": "value"})
        .assign(run_id=utils.RUN_ID)
    )[["run_id", "year", "mgra", "industry_code", "value"]]

    return self_emp


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
        # Get regional employment control totals from QCEW
        with open(utils.SQL_FOLDER / "employment/get_region_qcew.sql") as file:
            jobs_inputs["control_totals"] = utils.read_sql_query_fallback(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "year": year,
                },
            )

        # Get self-employed totals and append to control_totals
        with open(utils.SQL_FOLDER / "employment/get_region_self_emp.sql") as file:
            self_emp_control = utils.read_sql_query_fallback(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "year": year,
                },
            )

            jobs_inputs["control_totals"] = pd.concat(
                [jobs_inputs["control_totals"], self_emp_control],
                ignore_index=True,
            )

            jobs_inputs["control_totals"]["run_id"] = utils.RUN_ID

        # Get self-employed block group data
        with open(utils.SQL_FOLDER / "employment/get_B24080.sql") as file:
            jobs_inputs["B24080"] = utils.read_sql_query_fallback(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "year": year,
                },
            )

        # Get block group to MGRA crosswalk
        with open(utils.SQL_FOLDER / "employment/xref_bg_to_mgra.sql") as file:
            jobs_inputs["xref_bg_to_mgra"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

    with utils.GIS_ENGINE.connect() as con:
        # Get crosswalk from Census blocks to MGRAs
        with open(utils.SQL_FOLDER / "employment/xref_block_to_mgra.sql") as file:
            jobs_inputs["xref_block_to_mgra"] = utils.read_sql_query_fallback(
                max_lookback=2,
                sql=sql.text(file.read()),
                con=con,
                params={
                    "series": utils.SERIES,
                    "year": year,
                },
            )

        # Get military employment data and append to control_totals
        with open(utils.SQL_FOLDER / "employment/get_military_employment.sql") as file:
            jobs_inputs["military_emp"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "series": utils.SERIES,
                },
            )

        military_control_totals = (
            jobs_inputs["military_emp"]
            .groupby(["run_id", "year", "industry_code", "metric"], as_index=False)[
                "value"
            ]
            .sum()
        )[["run_id", "year", "industry_code", "metric", "value"]]

        jobs_inputs["control_totals"] = pd.concat(
            [jobs_inputs["control_totals"], military_control_totals],
            ignore_index=True,
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
    # Self Employed only includes block groups with self-employed individuals therefore
    # no row count validation performed
    tests.validate_data(
        "Self-employed block group data",
        jobs_inputs["B24080"],
        negative={},
        null={},
    )
    # No row count validation performed as xref is many-to-many
    tests.validate_data(
        "xref_block_to_mgra",
        jobs_inputs["xref_block_to_mgra"],
        negative={},
        null={},
    )
    # No row count validation performed as xref is many-to-many
    tests.validate_data(
        "xref_bg_to_mgra",
        jobs_inputs["xref_bg_to_mgra"],
        negative={},
        null={},
    )
    tests.validate_data(
        "Military employment data",
        jobs_inputs["military_emp"],
        row_count={"key_columns": {"mgra"}},
        negative={},
        null={},
    )
    tests.validate_data(
        "Jobs control totals",
        jobs_inputs["control_totals"],
        row_count={"key_columns": {"industry_code"}},
        negative={},
        null={},
    )
    


def _create_jobs_output(
    jobs_inputs: dict[str, pd.DataFrame], year: int
) -> dict[str, pd.DataFrame]:
    """Apply control totals to employment data using utils.integerize_1d().

    Args:
        jobs_inputs: A dictionary containing input DataFrames related to jobs

    Returns:
        Controlled employment data.
    """
    # Create MGRA level jobs data by combining LODES and self-employment data
    mgra_jobs = pd.concat(
        [
            # Aggregate LODES jobs to MGRA level
            _aggregate_lodes_to_mgra(
                jobs_inputs["lodes_data"], jobs_inputs["xref_block_to_mgra"], year
            ),
            # Distribute self-employment data to MGRA level
            _distribute_self_emp_to_mgra(
                jobs_inputs["B24080"], jobs_inputs["xref_bg_to_mgra"]
            ),
            # Include military employment at MGRA level
            jobs_inputs["military_emp"][
                ["run_id", "year", "mgra", "industry_code", "value"]
            ],
        ],
        ignore_index=True,
    ).sort_values(by=["mgra", "industry_code"])

    # Create list to store controlled values for each industry
    results = []

    # Apply integerize_1d to each industry_code
    for industry_code in mgra_jobs["industry_code"].unique():
        # Filter for this industry_code
        naics_mask = mgra_jobs.loc[mgra_jobs["industry_code"] == industry_code]

        # Get control value and apply integerize_1d
        control_value = (
            jobs_inputs["control_totals"]
            .loc[
                jobs_inputs["control_totals"]["industry_code"] == industry_code, "value"
            ]
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
        row_count={"key_columns": {"mgra", "industry_code"}},
        negative={},
        null={},
    )


def _insert_jobs(
    jobs_inputs: dict[str, pd.DataFrame],
    jobs_outputs: dict[str, pd.DataFrame],
    debug: bool,
) -> None:
    """Insert input and output data related to jobs to the database."""

    # Save locally if in debug mode
    if debug:
        jobs_inputs["control_totals"].to_csv(
            utils.DEBUG_OUTPUT_FOLDER / "inputs_controls_jobs.csv", index=False
        )
        jobs_outputs["results"].to_csv(
            utils.DEBUG_OUTPUT_FOLDER / "outputs_jobs.csv", index=False
        )

    # Otherwise, insert to database
    else:
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
