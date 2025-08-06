import logging
import math
import pathlib
import yaml

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


###########
# LOGGING #
###########

# Create a console handler
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)

# Create a file handler
_file_handler = logging.FileHandler(
    filename=ROOT_FOLDER / "log.txt", mode="w", encoding="utf-8"
)
_file_handler.setLevel(logging.DEBUG)

# Set up root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[_console_handler, _file_handler],
)

# Create logger for this module
logger = logging.getLogger(__name__)
logger.info("Initialize log file")


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

logger.info(
    f"RUN_ID: {RUN_ID}, MGRA_VERSION: {MGRA_VERSION}, YEARS: {RUN_INSTRUCTIONS["years"]}"
)

##############################
# UTILITY LISTS AND MAPPINGS #
##############################

HOUSEHOLD_SIZES = list(range(1, 8))

INCOME_CATEGORIES = [
    "Less than $15,000",
    "$15,000 to $29,999",
    "$30,000 to $44,999",
    "$45,000 to $59,999",
    "$60,000 to $74,999",
    "$75,000 to $99,999",
    "$100,000 to $124,999",
    "$125,000 to $149,999",
    "$150,000 to $199,999",
    "$200,000 or more",
]

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


def display_ascii_art(filename: str) -> None:
    """Displays ASCII art from a text file."""
    try:
        with open(filename, "r") as file:
            for line in file:
                print(line, end="")
            print()  # Ensure a newline after the ASCII art
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")


def integerize_1d(
    data: np.ndarray | list | pd.Series,
    control: int | float | None = None,
    methodology: str = "largest_difference",
    generator: np.random.Generator = None,
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
        data (np.ndarray | list | pd.Series): An array-like structure of float or
            integer values
        control (int | float | None): Optional control value to scale the input data
            such that the final sum of the elements exactly the control value. If not
            value is provided, then the sum of the input data will be preserved
        methodology (str): How to adjust for rounding error. Defaults to
            "largest_difference". Valid inputs are:
            * "largest": Adjust rounding error by decreasing the largest values until
              the control value is hit
            * "smallest": Adjust rounding error by decreasing the smallest non-zero
              until the control value is hit
            * "largest_difference": Adjust rounding error by decreasing the rounded
              values with the largest change from the original values until the control
              value is hit
            * "weighted_random": Adjust rounding error by decreasing the rounded values
              randomly, with more weight given to those that had a larger change. This
              methodology requires the "generator" parameter to be provided
        generator (np.random.Generator): A seeded random generator used to select values
            to change. This is intentionally required from outside the function, as if
            this function created a new seeded generator upon every call, it could
            consistently choose the same categories due to the same random state

    Returns:
        np.ndarray: Integerized data preserving sum or control value

    Raises:
        TypeError: If any of the input variables don't match the correct type
        ValueError: If negative values are encountered in the input variables
        ValueError: If no control value is provided and the input data does not sum to
            an integer
    """
    # Check rounding error methodology
    allowed_methodology = [
        "largest",
        "smallest",
        "largest_difference",
        "weighted_random",
    ]
    if methodology not in allowed_methodology:
        raise ValueError(
            f"Input parameter 'methodology' must be one of {str(allowed_methodology)}"
        )

    # Check a random generator is passed if we are doing "weighted_random"
    if methodology == "weighted_random":
        if generator is None:
            raise ValueError(
                f"Input parameter 'generator' must be provided when the 'methodology' "
                f"is '{methodology}'"
            )
        if type(generator) != np.random.Generator:
            raise ValueError(
                f"Input parameter 'generator' must be of type 'np.random.Generator', "
                f"not {type(generator)}"
            )

    # Check class of input data. If not a np.ndarray, convert to one
    if not isinstance(data, (np.ndarray, list, pd.Series)):
        raise TypeError(
            f"Input parameter 'data' is of type {type(data)}, "
            f"when it must be one of pd.Series, np.ndarray, or list"
        )
    if isinstance(data, list):
        data = np.array(data)
    elif isinstance(data, pd.Series):
        data = data.to_numpy()

    # Confirm no negative values are passed
    if np.any(data < 0):
        raise ValueError("Input parameter 'data' contains negative values")
    if control is not None and control < 0:
        raise ValueError(f"Input parameter 'control' is negative: {control}")

    # If no control provided preserve current sum
    if control is None:
        control = np.sum(data)

    # Ensure control is an integer
    if not math.isclose(control, round(control)):  # type: ignore
        raise ValueError(f"Input parameter 'control' must be integer: {control}")
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
    unrounded_data = data * control / np.sum(data)

    # Round every value up
    rounded_data = np.ceil(unrounded_data).astype(int)

    # Get difference between control and post-rounding sum.
    # Since data was rounded up, it is guaranteed to be the
    # same or larger than control, making diff non-negative.
    diff = int(np.sum(rounded_data) - control)

    # Adjust values to match difference
    if diff == 0:
        return rounded_data
    else:

        # Find the index values for the n largest data points
        if methodology == "largest":
            to_decrease = np.argsort(rounded_data, stable=True)[-diff:]

        # Find the index values for the n smallest non-zero data points
        elif methodology == "smallest":
            # Find and store all non-zero values/indices
            non_zero_indices = np.flatnonzero(rounded_data)
            non_zero_values = rounded_data[non_zero_indices]

            # Get index values of the n smallest non-zero data points
            n_smallest_non_zero = np.argsort(non_zero_values, stable=True)[:diff]

            # The index values correspond to non_zero_values, not to the original data.
            # Use the reverse lookup to get the indices of the original data
            to_decrease = non_zero_indices[n_smallest_non_zero]

        # Find the index values for the n data points with the largest change after
        # rounding
        elif methodology == "largest_difference":
            rounding_difference = rounded_data - unrounded_data
            to_decrease = np.argsort(rounding_difference, stable=True)[-diff:]

        # Find n random index values weighted on which had the largest change after
        # rounding
        elif methodology == "weighted_random":
            rounding_difference = rounded_data - unrounded_data
            to_decrease = generator.choice(
                a=rounding_difference.size,
                size=diff,
                replace=False,
                p=rounding_difference / rounding_difference.sum(),
            )

        # Decrease n-largest data points by one to match control
        np.add.at(rounded_data, to_decrease, -1)

        # Double check no negatives are present
        if np.any(rounded_data < 0):
            raise ValueError("Negative values encountered in integerized data")

        # Return the data
        return rounded_data.astype(int)


def integerize_2d(
    data: np.ndarray,
    row_ctrls: np.ndarray,
    col_ctrls: np.ndarray,
    condition: str = "exact",
    nearest_neighbors: list[int] | None = None,
    suppress_warnings: bool = False,
) -> np.ndarray:
    """Safe rounding of 2-dimensional array-like structures.

    After some basic input data validation, column data is rounded preserving
    column control totals, then rounding error is corrected for row controls.

    Preserving column control total while correcting rounding error for row
    controls is done using an integer reallocation process. Rows with +
    deviations have their smallest non-zero column adjusted downwards in
    increments of -1. Rows with - deviation have their largest non-zero column
    that was adjusted downwards for rows with + deviation adjusted upwards in
    increments of +1. This is repeated until all rows are either equal to or
    less than their row control total, depending on the 'condition' parameter.

    For rows with - deviation, is not always possible to find non-zero columns
    that were adjusted downward for rows with + deviation. Subsequently, the
    non-zero requirement is relaxed first to a 'Nearest Neighbors' strategy.
    Under this strategy, zero-valued columns with non-zero columns in a
    'neighborhood' around them are eligible for upwards adjustment. Multiple
    values for the 'neighborhood' are explored as each fails, provided by the
    'nearest_neighbors' input parameter. If all 'neighborhood' values fail,
    the non-zero requirement is completely abandoned and all columns that were
    adjusted downward for rows with + deviation are allowed. As the
    'Nearest Neighbors' strategy looks in a neighborhood of nearby columns,
    column ordering in the array is a critical component to the strategy.

    Args:
        data (np.ndarray): An array-like structure of float or integer values
        row_ctrls (np.ndarray): 1-dimensional array-like structure of float or
            integer values
        col_ctrls (np.ndarray): 1-dimensional array-like structure of float or
            integer values
        condition (str, optional): Control matching condition. Must be one of
            ['exact', 'less than']. Defaults to "exact".
        nearest_neighbors (list[int], optional): List of integer values to use as
            neighborhood for 'Nearest Neighbors' relaxation. Defaults to [1].
        suppress_warnings (bool, optional): If True, suppresses warnings about
            relaxing the skip condition. Defaults to False.
    Returns:
        np.ndarray: Integerized data preserving control values
    """
    # Take deep copy of input array to avoid altering original
    array_2d = data.copy(order="K")

    # Ensure input arrays are of correct dimensions
    if array_2d.ndim != 2:
        raise ValueError("Input data array must be 2-dimensional")
    if row_ctrls.ndim != 1:
        raise ValueError("Row controls must be 1-dimensional")
    if col_ctrls.ndim != 1:
        raise ValueError("Column controls must be 1-dimensional")

    # Ensure marginal control dimensions match input data array
    if array_2d.shape[0] != row_ctrls.shape[0]:
        raise ValueError("Row controls do not match input data array dimensions")
    if array_2d.shape[1] != col_ctrls.shape[0]:
        raise ValueError("Column controls do not match input data array dimensions")

    # Ensure condition parameter is set properly
    if condition == "exact":
        if np.sum(row_ctrls) != np.sum(col_ctrls):
            raise ValueError("Marginal controls inconsistent for 'exact' match")
    elif condition == "less than":
        if np.sum(row_ctrls) < np.sum(col_ctrls):
            raise ValueError("Marginal controls inconsistent for 'less than' match")
    else:
        raise ValueError("condition must be one of ['exact', 'less than']")

    # Ensure nearest_neighbors parameter is set properly
    if nearest_neighbors is None:
        nearest_neighbors = [1]
    if not isinstance(nearest_neighbors, list) or not all(
        isinstance(n, int) for n in nearest_neighbors
    ):
        raise ValueError("nearest_neighbors must be a list of integers")
    if len(nearest_neighbors) == 0:
        raise ValueError("nearest_neighbors list must contain at least one value")
    nearest_neighbors.sort()

    # Round columns of the input data array to match marginal controls
    for col_idx in range(array_2d.shape[1]):
        array_2d[:, col_idx] = integerize_1d(array_2d[:, col_idx], col_ctrls[col_idx])

    # Calculate deviations from row marginal controls
    deviations = np.sum(array_2d, axis=1) - row_ctrls

    # Initialize tracker of column adjustments made
    adjustments = np.zeros(col_ctrls.shape[0])

    # Set deviation condition
    if condition == "exact":
        any_deviation = np.max(np.abs(deviations)) > 0
    elif condition == "less than":
        any_deviation = np.max(deviations) > 0
    else:
        raise ValueError("condition must be one of ['exact', 'less than']")

    # Initialize skip condition relaxation switch
    relax_skip_condition = None

    # While there are deviations to adjust
    while any_deviation:
        # For rows with + deviation
        for row_idx in range(deviations.shape[0]):
            if deviations[row_idx] > 0:
                # Check for columns with available negative adjustments
                cols = list(np.where(adjustments < 0)[0])
                # If no columns available with negative adjustments
                # Or all values are 0 allow all columns to be adjusted
                if len(cols) == 0 or np.max(array_2d[row_idx, cols]) == 0:
                    cols = list(range(adjustments.shape[0]))

                # Calculate minimum of total possible row adjustment
                # And smallest positive non-zero column value
                min_value = np.min(array_2d[row_idx, cols][array_2d[row_idx, cols] > 0])
                col_idx = np.where(array_2d[row_idx] == min_value)[0][0]

                # Adjust value downward and store adjustment made
                array_2d[row_idx, col_idx] -= 1
                adjustments[col_idx] += 1

        # For rows with - deviation
        for row_idx in range(deviations.shape[0]):
            # Check for columns with available positive adjustments
            if np.max(adjustments) > 0:
                if deviations[row_idx] < 0:
                    # Restrict to columns with available positive adjustments
                    cols = list(np.where(adjustments > 0)[0])

                    # Further restrict adjustable columns depending on skip condition
                    # Default skip condition: only allow columns with non-zero values
                    if relax_skip_condition is None:
                        if np.max(array_2d[row_idx, cols]) == 0:
                            continue
                    # Nearest Neighbors skip condition: allow columns to be adjusted
                    # if and only if any neighboring columns are non-zero
                    elif relax_skip_condition == "Nearest Neighbors":
                        for col in cols:
                            low_neighbor = max(0, col - neighborhood)
                            high_neighbor = min(array_2d.shape[1], col + neighborhood)

                            if np.any(
                                array_2d[row_idx, low_neighbor:high_neighbor] > 0
                            ):
                                pass
                            else:
                                cols.remove(col)
                        if len(cols) == 0:
                            continue
                    # Allow all Columns skip condition: allow all columns to be adjusted
                    elif relax_skip_condition == "Allow all Columns":
                        pass

                    # Find first eligible column with maximum value
                    max_value = np.max(array_2d[row_idx, cols])
                    for col_idx in np.where(array_2d[row_idx] == max_value)[0]:
                        if col_idx in cols:
                            break

                    # Adjust value upward and store adjustment made
                    array_2d[row_idx, col_idx] += 1
                    adjustments[col_idx] -= 1

        # If no changes were made avoid infinite loop
        if np.array_equal(deviations, np.sum(array_2d, axis=1) - row_ctrls):
            # First time no deviations are adjusted relax skip condition
            # For rows with - deviations allow adjustment to zero-valued columns
            # If any nearest-neighbors are non-zero
            if relax_skip_condition is None:
                relax_skip_condition = "Nearest Neighbors"
                neighborhood = nearest_neighbors[0]  # use first value in list
                if not suppress_warnings:
                    logger.warning(
                        f"Skip condition relaxed to '{relax_skip_condition}' for 2-d integerizer."
                        f" Neighborhood set to (+/-) {neighborhood}."
                    )
            # If condition has already been relaxed to nearest neighbors
            # Set neighborhood to next value in the list of integers
            # If nearest_neighbors is exhausted, allow adjustment to all columns
            elif relax_skip_condition == "Nearest Neighbors":
                relax_skip_condition = "Allow all Columns"
                msg = f"Skip condition relaxed to '{relax_skip_condition}' for 2d-integerizer."
                for n in nearest_neighbors:
                    if n > neighborhood:
                        relax_skip_condition = "Nearest Neighbors"
                        neighborhood = n
                        msg = f" Neighborhood increased to (+/-) {neighborhood}."
                        break
                if not suppress_warnings:
                    logger.warning(msg)
            # If condition has already been relaxed to allow all columns raise error
            elif relax_skip_condition == "Allow all Columns":
                raise ValueError(
                    "No adjustments able to be made. Check marginal controls."
                )

        # Recalculate the row deviations
        deviations = np.sum(array_2d, axis=1) - row_ctrls

        # Recalculate the deviation condition
        if condition == "exact":
            any_deviation = np.max(np.abs(deviations)) > 0
        elif condition == "less than":
            any_deviation = np.max(deviations) > 0
        else:
            raise ValueError("condition must be one of ['exact', 'less than']")

    return array_2d


def read_sql_query_acs(**kwargs: dict) -> pd.DataFrame:
    """Read SQL query allowing for dynamic year adjustment.

    This function executes a SQL query using pandas read_sql_query allowing
    for dynamic adjustment of the 'year' parameter in the query. If the query
    returns a message indicating that the ACS 5-Year Table does not exist for
    a given year, it will automatically decrement the year by one and re-run
    the query. Note this function is specific to ACS 5-Year Tables and
    requires the SQL query file to return a DataFrame with a single column
    called 'msg' with the text 'ACS 5-Year Table does not exist' when no data
    is found for the specified year.

    Args:
        kwargs (dict): Keyword arguments for pd.read_sql_query

    Returns:
        pd.DataFrame: Result of the SQL query
    """
    df = pd.read_sql_query(**kwargs)  # type: ignore

    # Check if returned DataFrame contains SQL message
    if df.columns.tolist() == ["msg"]:
        msg = df["msg"].values[0]
        if msg == "ACS 5-Year Table does not exist" and "year" in kwargs["params"]:
            # If the table does not exist run query for prior year
            kwargs["params"]["year"] -= 1

            logger.warning(
                "Re-running ACS SQL query with 'year' set to: "
                + str(kwargs["params"]["year"])
            )

            df = pd.read_sql_query(**kwargs)  # type: ignore

            # If the year column exists, set it to the original year
            if "year" in df.columns:
                df["year"] = kwargs["params"]["year"] + 1
        else:
            # Raise error if the message is not expected
            raise ValueError(f"SQL query returned a message: {msg}.")

    return df
