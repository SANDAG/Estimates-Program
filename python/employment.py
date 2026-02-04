import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)


def run_employment(year: int):
    """Run the Employment module for a specified year.

    This function processes employment data by applying control totals to
    LEHD LODES data at the MGRA level using integerization.

    Args:
        year (int): The year for which to run the Employment module.
    """

    # Check MGRA version and raise error if not 'mgra15'
    if utils.MGRA_VERSION != "mgra15":
        raise ValueError(
            f"Employment module only works with MGRA_VERSION = 'mgra15'. "
            f"Current MGRA_VERSION is '{utils.MGRA_VERSION}'."
        )

    LODES_data = get_LODES_data(year)

    xref = get_xref_block_to_mgra()

    lehd_jobs = aggregate_lodes_to_mgra(LODES_data, xref, year)

    control_totals = get_control_totals(year)

    controlled_data = apply_employment_controls(lehd_jobs, control_totals, generator)

    _insert_jobs(control_totals, controlled_data)


def get_LODES_data(year: int) -> pd.DataFrame:
    """Retrieve LEHD LODES data for a specified year.

    Args:
        year (int): The year for which to retrieve LEHD LODES data.
    """

    with utils.LEHD_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "employment/get_lodes_data.sql") as file:
            lodes_data = utils.read_sql_query_custom(
                sql=sql.text(file.read()),
                con=con,
                params={"year": year},
            )

    with utils.GIS_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "employment/get_naics72_split.sql") as file:
            split_naics_72 = utils.read_sql_query_custom(
                sql=sql.text(file.read()),
                con=con,
                params={"year": year},
            )

    # Separate industry_code 72 from other industries
    lodes_72 = lodes_data[lodes_data["industry_code"] == "72"].copy()
    lodes_other = lodes_data[lodes_data["industry_code"] != "72"].copy()

    # Join industry_code 72 data with split percentages
    lodes_72_split = lodes_72.merge(split_naics_72, on="block", how="left")

    # Create rows for industry_code 721
    lodes_721 = lodes_72_split[["year", "block"]].copy()
    lodes_721["industry_code"] = "721"
    lodes_721["jobs"] = lodes_72_split["jobs"] * lodes_72_split["pct_721"]

    # Create rows for industry_code 722
    lodes_722 = lodes_72_split[["year", "block"]].copy()
    lodes_722["industry_code"] = "722"
    lodes_722["jobs"] = lodes_72_split["jobs"] * lodes_72_split["pct_722"]

    # Combine all data
    combined_data = pd.concat([lodes_other, lodes_721, lodes_722], ignore_index=True)
    combined_data = combined_data[["year", "block", "industry_code", "jobs"]]

    return combined_data


def get_xref_block_to_mgra() -> pd.DataFrame:
    """Retrieve crosswalk from Census blocks to MGRAs.

    Returns:
        pd.DataFrame: A DataFrame containing the crosswalk from blocks to MGRAs.
    """

    with utils.LEHD_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "employment/xref_block_to_mgra.sql") as file:
            xref = utils.read_sql_query_custom(
                sql=sql.text(file.read()),
                con=con,
                params={"mgra_version": utils.MGRA_VERSION},
            )

    return xref


def aggregate_lodes_to_mgra(
    combined_data: pd.DataFrame, xref: pd.DataFrame, year: int
) -> pd.DataFrame:
    """Aggregate LODES data to MGRA level using allocation percentages.

    Args:
        combined_data (pd.DataFrame): LODES data with columns: year, block, industry_code, jobs
        xref (pd.DataFrame): Crosswalk with columns: block, mgra, allocation_pct
        year (int): The year for which to aggregate data

    Returns:
        pd.DataFrame: Aggregated data at MGRA level with columns: year, mgra, industry_code, jobs
    """
    # Get MGRA data from SQL
    with utils.LEHD_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "employment/get_mgra.sql") as file:
            mgra_data = utils.read_sql_query_custom(
                sql=sql.text(file.read()),
                con=con,
                params={"run_id": utils.RUN_ID},
            )

    # Get unique industry codes and cross join with MGRA data
    unique_industries = combined_data["industry_code"].unique()
    jobs_frame = (
        mgra_data.assign(key=1)
        .merge(
            pd.DataFrame({"industry_code": unique_industries, "key": 1}),
            on="key",
        )
        .drop("key", axis=1)
    )
    jobs_frame["year"] = year
    jobs_frame = jobs_frame[["year", "mgra", "industry_code"]]

    # Join combined_data to xref and calculate allocated jobs
    lehd_to_mgra = combined_data.merge(xref, on="block", how="inner")
    lehd_to_mgra["value"] = lehd_to_mgra["jobs"] * lehd_to_mgra["allocation_pct"]
    #    lehd_to_mgra = lehd_to_mgra[
    #        [
    #            "year",
    #            "block",
    #            "mgra",
    #            "industry_code",
    #            "jobs",
    #            "allocation_pct",
    #            "value",
    #        ]
    #    ]

    # Sum allocated jobs by year, mgra, and industry_code
    lehd_to_mgra_summed = lehd_to_mgra.groupby(
        ["year", "mgra", "industry_code"], as_index=False
    )["value"].sum()

    # Join summed data to jobs_frame, keeping all MGRAs and industry codes
    final_lehd_to_mgra = jobs_frame.merge(
        lehd_to_mgra_summed,
        on=["year", "mgra", "industry_code"],
        how="left",
    )
    final_lehd_to_mgra["value"] = final_lehd_to_mgra["value"].fillna(0)
    final_lehd_to_mgra["run_id"] = utils.RUN_ID  # Add run_id column
    final_lehd_to_mgra = final_lehd_to_mgra[
        ["run_id", "year", "mgra", "industry_code", "value"]
    ]

    return final_lehd_to_mgra


def get_control_totals(year: int) -> pd.DataFrame:
    """Load employment data from SQL queries.

    Args:
        year (int): The year for which to load employment data.

    Returns:
        pd.DataFrame: Employment control totals from QCEW.
    """
    with utils.LEHD_ENGINE.connect() as con:

        # Get employment control totals from QCEW
        with open(utils.SQL_FOLDER / "employment/QCEW_control.sql") as file:
            control_totals = pd.read_sql(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "year": year,
                },
            )

    control_totals["run_id"] = utils.RUN_ID  # Add run_id column

    return control_totals


def apply_employment_controls(
    original_data: pd.DataFrame,
    control_totals: pd.DataFrame,
    generator: np.random.Generator,
) -> pd.DataFrame:
    """Apply control totals to employment data using integerization.

    Args:
        original_data (pd.DataFrame): LEHD LODES data at MGRA level.
        control_totals (pd.DataFrame): Employment control totals from QCEW.
        generator (np.random.Generator): NumPy random number generator.

    Returns:
        pd.DataFrame: Controlled employment data.
    """
    # Create a copy of original_data for controlled results
    controlled_data = original_data.copy()

    # Get unique industry codes
    industry_codes = original_data["industry_code"].unique()

    # Apply integerize_1d to each industry code
    for industry_code in industry_codes:
        # Filter original data for this industry
        industry_mask = original_data["industry_code"] == industry_code

        # Get control value for this industry
        control_value = control_totals[
            control_totals["industry_code"] == industry_code
        ]["value"].iloc[0]

        # Apply integerize_1d and update controlled_data
        controlled_data.loc[industry_mask, "value"] = utils.integerize_1d(
            data=original_data.loc[industry_mask, "value"],
            control=control_value,
            methodology="weighted_random",
            generator=generator,
        )

    return controlled_data


def _insert_jobs(jobs_inputs: pd.DataFrame, jobs_outputs: pd.DataFrame) -> None:
    """Insert input and output data related to household population"""

    # Insert input and output data to database
    with utils.ESTIMATES_ENGINE.connect() as con:

        jobs_inputs.to_sql(
            name="controls_jobs",
            con=con,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        jobs_outputs.to_sql(
            name="jobs", con=con, schema="outputs", if_exists="append", index=False
        )
