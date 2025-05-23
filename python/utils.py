import math
import pathlib
import yaml
import warnings

import numpy as np
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

# Temporary file staging location for SQL BULK Inserts
BULK_INSERT_STAGING = pathlib.Path(_secrets["sql"]["staging"])


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

# Minimum and maximum age values for each age group
AGE_MAPPING = {
    "Under 5": {"min": 0, "max": 4},
    "5 to 9": {"min": 5, "max": 9},
    "10 to 14": {"min": 10, "max": 14},
    "15 to 17": {"min": 15, "max": 17},
    "18 and 19": {"min": 18, "max": 19},
    "20 to 24": {"min": 20, "max": 24},
    "25 to 29": {"min": 25, "max": 29},
    "30 to 34": {"min": 30, "max": 34},
    "35 to 39": {"min": 35, "max": 39},
    "40 to 44": {"min": 40, "max": 44},
    "45 to 49": {"min": 45, "max": 49},
    "50 to 54": {"min": 50, "max": 54},
    "55 to 59": {"min": 55, "max": 59},
    "60 and 61": {"min": 60, "max": 61},
    "62 to 64": {"min": 62, "max": 64},
    "65 to 69": {"min": 65, "max": 69},
    "70 to 74": {"min": 70, "max": 74},
    "75 to 79": {"min": 75, "max": 79},
    "80 to 84": {"min": 80, "max": 84},
    "85 and Older": {"min": 85, "max": 100},
}


#####################
# UTILITY FUNCTIONS #
#####################


def integerize_1d(
    data: np.ndarray | list | pd.Series, control: int | float | None = None
) -> np.ndarray:
    """Safe rounding of 1-dimensional array-like structures.

    After some basic input data validation, data is rounded, then rounding error is
    corrected. If input control is zero, the output is also all zero. If input control
    is non-zero but all data is zero, values at the front of the array will be increased
    by one

    Instead of using a basic round, this function instead always rounds up, assuming
    there is any non-zero decimal part. This ensures that when small values (less than
    .5) are passed in, we do not round them down to zero. This greatly helps balance
    and control our tightly restricted data, as simply having values be one instead of
    zero gives us much more flexibility in manual adjustment.

    Args:
        data: An array-like structure of float or integer values
        control: Optional control value to scale the input data such that the final sum
            of the elements exactly the control value. If not value is provided, then
            the sum of the input data will be preserved

    Returns:
        np.ndarray: Integerized data preserving sum or control value

    Raises:
        TypeError: If any of the input variables don't match the correct type
        ValueError: If negative values are encountered in the input variables
        ValueError: If no control value is provided and the input data does not sum to
            an integer
    """
    # Check class of input data. If not a np.ndarray, convert to one
    if not isinstance(data, (np.ndarray, list, pd.Series)):
        raise TypeError(
            f"Input data is of type {type(data)} when it should be one of pd.Series, "
            f"np.ndarray, or list"
        )
    if isinstance(data, list):
        data = np.array(data)
    elif isinstance(data, pd.Series):
        data = data.to_numpy()

    # Confirm no negative values are passed
    if np.any(data < 0):
        raise ValueError("Input variable 'data' contains negative values")
    if control is not None and control < 0:
        raise ValueError("Input variable 'control' contains is negative")

    # If no control provided preserve current sum
    if control is None:
        control = np.sum(data)

    # Ensure control is an integer
    if not math.isclose(control, round(control)):  # type: ignore
        raise ValueError(f"Control must be integer: {control}")
    else:
        control = int(round(control))  # type: ignore

    # Override if control is zero
    if control == 0:
        data.fill(0)
        return data

    # Override if control is not zero, but all input data is zero
    if control is not None and control != 0 and np.all(data == 0):
        np.add.at(data, np.arange(control), 1)
        return data

    # Scale data to match the control
    data = data * control / np.sum(data)

    # Round every value up
    data = np.ceil(data)

    # Get difference between control and post-rounding sum.
    # Since data was rounded up, it is guaranteed to be the
    # same or larger than control, making diff non-negative.
    diff = int(np.sum(data) - control)

    # Adjust values to match difference
    if diff == 0:
        return data
    else:
        # Find the index values for the n-largest data points
        # Where n is equal to the difference
        to_decrease = np.argsort(data, stable=True)[-diff:]

        # Decrease n-largest data points by one to match control
        np.add.at(data, to_decrease, -1)

        # Double check no negatives are present
        if np.any(data < 0):
            raise ValueError("Negative values encountered in integerized data")

        # Return the data
        return data.astype(int)


def integerize_2d(
    data: np.ndarray,
    row_ctrls: np.ndarray,
    col_ctrls: np.ndarray,
    condition: str = "exact",
) -> np.ndarray:
    # Take deep copy of input array to avoid altering original
    array_2d = np.copy(data)

    # Ensure input arrays are of correct dimensions
    assert array_2d.ndim == 2, "input data array must be 2-dimensional"
    assert row_ctrls.ndim == 1, "row controls must be 1-dimensional"
    assert col_ctrls.ndim == 1, "column controls must be 1-dimensional"

    # Ensure marginal control dimensions match input data array
    assert (
        array_2d.shape[0] == row_ctrls.shape[0]
    ), "row controls do not match input data array dimensions"

    assert (
        array_2d.shape[1] == col_ctrls.shape[0]
    ), "column controls do not match input data array dimensions"

    # Ensure condition parameter is set properly
    if condition == "exact":
        assert np.sum(row_ctrls) == np.sum(
            col_ctrls
        ), "marginal controls inconsistent for 'exact' match"
    elif condition == "less than":
        assert np.sum(row_ctrls) >= np.sum(
            col_ctrls
        ), "marginal controls inconsistent for 'less than' match"
    else:
        assert condition in [
            "exact",
            "less than",
        ], "condition must be one of ['exact', 'less than']"

    # Round columns of the input data array to match marginal controls
    for col_idx in range(array_2d.shape[1]):
        array_2d[:, col_idx] = integerize_1d(array_2d[:, col_idx], col_ctrls[col_idx])

    # Calculate deviations from row marginal controls
    deviations = np.sum(array_2d, axis=1) - row_ctrls

    # Intialize tracker of column adjustments made
    adjustments = np.zeros(col_ctrls.shape[0])

    # Set deviation condition
    if condition == "exact":
        any_deviation = np.max(np.abs(deviations)) > 0
    elif condition == "less than":
        any_deviation = np.max(deviations) > 0
    else:
        raise ValueError("condition must be one of ['exact', 'less than']")

    # Initialize skip condition relaxation switch
    relax_skip_condition = False

    # While there are deviations to adjust
    while any_deviation:
        # For rows with + deviation
        for row_idx in range(deviations.shape[0]):
            if deviations[row_idx] > 0:
                # Check for columns with available negative adjustments
                cols = list(np.where(adjustments < 0)[0])
                # If no columns available with negativwe adjustments
                # Or all values are 0 allow all columns to be adjusted
                if len(cols) == 0 or np.max(array_2d[row_idx, cols]) == 0:
                    cols = list(range(adjustments.shape[0]))

                # Calculate minimum of total possible row adjustment
                # And smallest positive non-zero column value
                min_value = np.min(array_2d[row_idx, cols][array_2d[row_idx, cols] > 0])
                col_idx = np.where(array_2d[row_idx] == min_value)[0][0]
                adjustment = min(deviations[row_idx], array_2d[row_idx, col_idx])

                # Adjust value downward and store adjustment made
                array_2d[row_idx, col_idx] -= adjustment
                adjustments[col_idx] += adjustment

        # For rows with - deviation
        for row_idx in range(deviations.shape[0]):
            # Check for columns with available positive adjustments
            if np.max(adjustments) > 0:
                if deviations[row_idx] < 0:
                    # Restrict to columns with available positive adjustments
                    cols = list(np.where(adjustments > 0)[0])

                    # Depending on skip condition
                    # Either allow or do not allow zero-values to be adjusted
                    # Find the largest column with available adjustment
                    # Calculate minimum of possible row and column adjustments
                    if not relax_skip_condition:
                        if np.max(array_2d[row_idx, cols]) == 0:
                            continue

                    # Find first eligible column with maximum value
                    max_value = np.max(array_2d[row_idx, cols])
                    for col_idx in np.where(array_2d[row_idx] == max_value)[0]:
                        if col_idx in cols:
                            break

                    # Adjust value upward and store adjustment made
                    adjustment = min(np.abs(deviations[row_idx]), adjustments[col_idx])
                    array_2d[row_idx, col_idx] += adjustment
                    adjustments[col_idx] -= adjustment

        # If no changes were made avoid infinite loop
        if np.array_equal(deviations, np.sum(array_2d, axis=1) - row_ctrls):
            # First time no deviations are adjusted relax skip condition
            # For rows with - deviations allow adjustment to zero-valued columns
            # If condition has already been relaxed raise error
            if relax_skip_condition:
                raise ValueError("No adjustments made. Check marginal controls.")
            else:
                relax_skip_condition = True
                warnings.warn("Skip condition relaxed for 2d-integerizer.")

        # Recalulate the row deviations
        deviations = np.sum(array_2d, axis=1) - row_ctrls

        # Recalculate the deviation condition
        if condition == "exact":
            any_deviation = np.max(np.abs(deviations)) > 0
        elif condition == "less than":
            any_deviation = np.max(deviations) > 0
        else:
            raise ValueError("condition must be one of ['exact', 'less than']")

    return array_2d
