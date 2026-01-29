import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)

# Load configuration from YAML file
# with open("config.yaml", "r") as f:
#    config = yaml.safe_load(f)


def run_employment(year):
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

    # Load data from SQL
    original_data, control_totals = run_employment_sql(year)

    # Apply controls
    controlled_data = apply_employment_controls(
        original_data, control_totals, generator
    )

    # Export results
    output_filepath = utils.OUTPUT_FOLDER / f"controlled_data_{year}.csv"
    controlled_data.to_csv(output_filepath, index=False)

    return controlled_data


def run_employment_sql(year):
    """Load employment data from SQL queries.

    Args:
        year (int): The year for which to load employment data.

    Returns:
        tuple: A tuple containing (original_data, control_totals) as DataFrames.
    """
    with utils.LEHD_ENGINE.connect() as con:
        # Get LEHD LODES data at MGRA level
        with open(utils.SQL_FOLDER / "employment/LODES_to_MGRA.sql") as file:
            original_data = pd.read_sql(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "year": year,
                    "mgra_version": utils.MGRA_VERSION,
                },
            )

        # Get employment control totals from QCEW
        with open(utils.SQL_FOLDER / "employment/QCEW_control.sql") as file:
            control_totals = pd.read_sql(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "year": year,
                },
            )
    return original_data, control_totals


def apply_employment_controls(original_data, control_totals, generator):
    """Apply control totals to employment data using integerization.

    Args:
        original_data (pd.DataFrame): LEHD LODES data at MGRA level.
        control_totals (pd.DataFrame): Employment control totals from QCEW.
        generator: NumPy random number generator.

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
        ]["jobs"].iloc[0]

        # Apply integerize_1d and update controlled_data
        controlled_data.loc[industry_mask, "jobs"] = utils.integerize_1d(
            data=original_data.loc[industry_mask, "jobs"],
            control=control_value,
            methodology="weighted_random",
            generator=generator,
        )

    return controlled_data
