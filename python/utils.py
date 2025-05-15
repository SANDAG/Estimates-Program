import iteround
import pathlib
import yaml
import warnings
import pandas as pd
import sqlalchemy as sql

import python.parsers as parsers


#########
# PATHS #
#########

# Store project root folder
ROOT_FOLDER = pathlib.Path(__file__).parent.resolve().parent
SQL_FOLDER = ROOT_FOLDER / "sql"


#####################
# SQL CONFIGURATION #
#####################

# Load secrets YAML file
try:
    with open(ROOT_FOLDER / "secrets.yml", "r") as file:
        _secrets = yaml.safe_load(file)
except IOError:
    raise IOError("secrets.yml does not exist, see README.md")

# Create SQLAlchemy engine(s)
ESTIMATES_ENGINE = sql.create_engine(
    "mssql+pyodbc://@"
    + _secrets["sql"]["estimates"]["server"]
    + "/"
    + _secrets["sql"]["estimates"]["database"]
    + "?trusted_connection=yes&driver="
    + "ODBC Driver 17 for SQL Server",
    fast_executemany=True,
)

GIS_ENGINE = sql.create_engine(
    "mssql+pyodbc://@"
    + _secrets["sql"]["gis"]["server"]
    + "/"
    + _secrets["sql"]["gis"]["database"]
    + "?trusted_connection=yes&driver="
    + "ODBC Driver 17 for SQL Server",
    fast_executemany=True,
)

# Other SQL configuration
GIS_SERVER = _secrets["sql"]["gis"]["server"]


#########################
# RUNTIME CONFIGURATION #
#########################

# Load configuration YAML file
try:
    with open(ROOT_FOLDER / "config.yml", "r") as file:
        config = yaml.safe_load(file)
except IOError:
    raise IOError("config.yml does not exist, see README.md")

# Initialize input parser
# Parse the configuration YAML file and validate its contents
input_parser = parsers.InputParser(config=config, engine=ESTIMATES_ENGINE)
input_parser.parse_config()

# Get data from the parsed and validated configuration file
RUN_INSTRUCTIONS = input_parser.run_instructions
RUN_ID = input_parser.run_id
MGRA_VERSION = input_parser.mgra_version


#####################
# UTILITY FUNCTIONS #
#####################


def integerize_2d(
    df: pd.DataFrame, row_crtls: list, col_crtls: list, condition: str = "exact"
) -> pd.DataFrame:
    """Integerize values in a DataFrame based on marginal control totals.

    Default behavior is to match the marginal controls exactly. If the
    condition is set to "less than", the function will adjust values such that
    the row values are less than or equal to the row marginal controls. The
    column values always match the column marginal controls.

    Args:
        df (pd.DataFrame): DataFrame containing the values to be integerized.
        row_crtls (list): Row marginal control totals.
        col_crtls (list): Column marginal control totals.
        condition (str): Condition for integerization. Options are 'exact' or
            'less than'. Default is 'exact'.

    Returns:
        pd.DataFrame: DataFrame with integerized values.
    """
    # Ensure the marginal controls match dimensions of the DataFrame
    if df.shape[0] != len(row_crtls) or df.shape[1] != len(col_crtls):
        raise ValueError("Marginal controls do not match DataFrame dimensions.")

    # Condition parameter checks
    if condition not in ["exact", "less than"]:
        raise ValueError("Condition must be 'exact' or 'less than'.")
    elif condition == "exact" and sum(row_crtls) != sum(col_crtls):
        raise ValueError("Marginal controls are inconsistent for 'exact' match.")
    elif condition == "less than" and sum(col_crtls) > sum(row_crtls):
        raise ValueError("Marginal controls are inconsistent for 'less than' match.")

    # Intialize list to store column adjustments made
    adjustments = [0] * df.shape[1]

    # Safe round the columns to match the marginal controls
    for i, col in enumerate(df.columns):

        # If control is zero set column to zero
        if col_crtls[i] == 0:
            df[col] == 0

        # If the column has non-zero positive values
        elif any(df[col] > 0):
            # Remove 0s from consideration and use the largest strategy to avoid negative values
            values = iteround.saferound(
                df.loc[df[col] > 0, col],
                places=0,
                topline=col_crtls[i],
                strategy="largest",
            )

            # If any negatives exist
            if min(values) < 0:
                # Track column adjustments
                adjustments[i] -= abs(sum([value for value in values if value < 0]))
                # Set all negative values to 0
                values = [value if value > 0 else 0 for value in values]

            # Set the column to the saferounded values
            df.loc[df[col] > 0, col] = values
        # If control is non-zero and and column has no non-zero positive values
        else:
            # Safe round the values
            values = iteround.saferound(
                df[col],
                places=0,
                topline=col_crtls[i],
                strategy="largest",
            )

            # If any negatives exist
            if min(values) < 0:
                # Track column adjustments
                adjustments[i] -= abs(sum([value for value in values if value < 0]))
                # Set all negative values to 0
                values = [value if value > 0 else 0 for value in values]

            # Set the column to the saferounded values
            df[col] = values

    # Calculate deviations from the row marginal controls
    row_devs = df.sum(axis=1) - row_crtls

    # Calculate the deviation condition
    if condition == "exact":
        any_deviation = max(map(abs, row_devs)) > 0
    elif condition == "less than":
        any_deviation = max(row_devs) > 0
    else:
        raise ValueError("Condition must be 'exact' or 'less than'.")

    # While there are deviations to adjust
    relax_skip_condition = False
    while any_deviation or max(map(abs, adjustments)) > 0:
        # For rows with + deviation
        for i, row in enumerate(row_devs):
            if row > 0:
                # Check for columns with available negative adjustments
                cols = [j for j, v in enumerate(adjustments) if v < 0]

                # If all values in adjustment columns are 0 allow all columns to be adjusted
                if len(cols) == 0 or df.iloc[i, cols].max() == 0:
                    cols = list(range(len(adjustments)))

                # Calculate adjustment as minimum of total possible and smallest positive non-zero column value
                # Adjust the column value downward and store adjustments made for that column
                col_idx = df.iloc[i, cols].where(df.iloc[i, cols] > 0).idxmin()
                j = df.columns.get_loc(col_idx)
                adjustment = min(row, df.iat[i, j])
                df.iat[i, j] -= adjustment
                adjustments[j] += adjustment

        # For rows with - deviation
        for i, row in enumerate(row_devs):
            # Check for columns with available positive adjustments
            if max(adjustments) > 0:
                if row < 0:
                    # Restrict to columns with available positive adjustments
                    cols = [j for j, v in enumerate(adjustments) if v > 0]

                    # If all values in adjustment columns are 0 skip the row
                    if not relax_skip_condition:
                        if df.iloc[i, cols].max() == 0:
                            continue

                    # Find the column with the largest value and available adjustment
                    # Calculate adjustment as minimum of total possible row and column adjustments
                    # Adjust the column value upward and store adjustments made for that column
                    col_idx = df.iloc[i, cols].idxmax()
                    j = df.columns.get_loc(col_idx)
                    adjustment = min(abs(row), adjustments[j])
                    df.iat[i, j] += adjustment
                    adjustments[j] -= adjustment
            else:
                break

        # If no changes were made avoid infinite loop
        if row_devs.equals(df.sum(axis=1) - row_crtls):
            # The first time no deviations are adjusted relax the skip condition
            # For rows with - deviations allow positive adjustments to zero-valued columns
            if relax_skip_condition:
                raise ValueError("No adjustments made. Check marginal controls.")
            else:
                relax_skip_condition = True
                warnings.warn("Skip condition relaxed for 2d-integerizer.")
        else:
            # Recalulate the row deviations
            row_devs = df.sum(axis=1) - row_crtls

        # Recalculate the deviation condition
        if condition == "exact":
            any_deviation = max(map(abs, row_devs)) > 0
        elif condition == "less than":
            any_deviation = max(row_devs) > 0
        else:
            raise ValueError("Condition must be 'exact' or 'less than'.")

    return df
