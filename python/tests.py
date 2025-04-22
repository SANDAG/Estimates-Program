# Testing suite for the entire Estimates Program project. At least for now, all tests
# are integration tests, in the sense that they run on actual module inputs and outputs.

# TODO: Integration with the Python logging library. The idea is that critical errors
# will both raise an error and be logged, while warnings will only be logged

import textwrap
import math
import pandas as pd

import python.utils as utils

#####################
# HELPFUL CONSTANTS #
#####################

# Within each kind of count, the key is the column name (must exactly match with input
# data) and the value is the exact number of unique values that should be in that
# column
_DISTINCT_COUNTS = {
    "constants": {
        "gq_type": 4,
        "structure_type": 4,
    },
    "mgra15": {
        "mgra": 24321,
        "2010_tract": 627,
        "2020_tract": 736,
        "city": 19,
    },
}

# For ease of access, combine the constants part of the dictionary with the current
# MGRA series
_DISTINCT_COUNTS = _DISTINCT_COUNTS["constants"] | _DISTINCT_COUNTS[utils.MGRA_VERSION]


#########
# TESTS #
#########


def validate_row_count(
    table_name: str, data: pd.DataFrame, key_columns: set[str], year: int = None
) -> None:
    """Verify that the provided data has the correct number of rows

    The correct number of rows is determined by the input 'key_columns', under the
    assumption that input data has functionally the SQL CROSS JOIN of 'key_columns'. The
    number of values in each key column is determined by the variable above labeled
    '_DISTINCT_COUNTS'

    Args:
        table_name: The name of the table. The only purpose of this is to make error
            messages more descriptive
        data: The data to check. Key columns are determined by the intersection of
            data column names and the columns defined in _ROW_COUNTS
        key_columns: The columns of key values which must be fully represented in the
            data
        year (optional): Used only if checking Census Tract columns, as 2010 CTs and
            2020 CTs have different geometry counts

    Returns:
        True if the row counts of the provided data are valid, False otherwise
    """
    # Make sure that 'year' is provided if 'tract' is a 'key_column'
    if "tract" in key_columns and year is None:
        raise ValueError(
            f"'{table_name}' contains the column 'tract', but no 'year' is provided. "
            f"As such, 'tests.py' cannot determine the Census year of 'tract'"
        )

    # Verify that the provided key columns actually exist and we have data for them
    for column in key_columns:
        if column not in data.columns:
            raise ValueError(
                f"'{table_name}' is missing the required key column {column}"
            )
        if column not in _DISTINCT_COUNTS.keys() and column != "tract":
            raise ValueError(
                f"'tests.py' is missing data for the key column {column}. Fill in the "
                f"corresponding value in the variable '_DISTINCT_COUNTS'"
            )

    # Collect the number of unique values in each key column, accounting for the fact
    # that the number of tracts changes depending on the year
    unique_key_values = {}
    for column in key_columns:
        if column == "tract":
            unique_key_values["tract"] = _DISTINCT_COUNTS[f"{year // 10 * 10}_tract"]
        else:
            unique_key_values[column] = _DISTINCT_COUNTS[column]

    # Check that the total number of rows is correct, assuming that we do the CROSS JOIN
    # of all keys columns
    n_rows = math.prod(unique_key_values.values())
    if data.shape[0] != n_rows:
        row_count_explanation = " x ".join(
            [f"{value:,} {column}" for column, value in unique_key_values.items()]
        )
        raise ValueError(
            f"'{table_name}' should have {n_rows} rows ({row_count_explanation}) but "
            f"it has {data.shape[0]}"
        )


def validate_negative_null(
    table_name: str,
    data: pd.DataFrame,
    negative_ok: list[str] = None,
    null_ok: list[str] = None,
) -> None:
    """Verify that the provided data does not contain negative/null values

    Serves as a wrapper function for the individual checks of '_validate_negative()' and
    '_validate_null()'. See the individual sub_functions for more details.

    Args:
        table_name: The name of the table. The only purpose of this is to make error
            messages more descriptive
        data: The data to check
        negative_ok (optional): Columns where negative values are allowed
        null_ok (optional): Columns where null values are allowed

    Raises:
        ValueError: When negative values are encountered in columns where they are
            not allowed.
    """
    # Avoid issues with mutable default parameter values
    if negative_ok is None:
        negative_ok = []
    if null_ok is None:
        null_ok = []

    # Call the individual tests
    _validate_negative(table_name, data, negative_ok)
    _validate_null(table_name, data, null_ok)


def _validate_negative(
    table_name: str, data: pd.DataFrame, negative_ok: list[str]
) -> None:
    """Verify that the provided data does not contain negative values

    Checks will be performed on all columns unless they are explicitly passed into the
    function as being allowed to have negative values. Note that the negative value
    check will automatically skip any non-numeric columns

    Args:
        table_name: The name of the table. The only purpose of this is to make error
            messages more descriptive
        data: The data to check
        negative_ok (optional): Columns where negative values are allowed

    Raises:
        ValueError: When negative values are encountered in columns where they are
            not allowed.
    """
    # Check each column of the input data
    for column in data.columns:

        # Check for negative values except for those columns which are explicitly
        # allowed to be negative
        if column not in negative_ok:
            if pd.api.types.is_numeric_dtype(data[column]) and (data[column] < 0).any():
                error = (
                    f"'{table_name}' contains negative values in the column '{column}'. "
                    f"Some of the associated rows are:\n"
                    + textwrap.indent(data[data[column] < 0].head(5).to_string(), "\t")
                )
                raise ValueError(error)


def _validate_null(table_name: str, data: pd.DataFrame, null_ok: list[str]) -> None:
    """Verify that the provided data does not contain null values

    Checks will be performed on all columns unless they are explicitly passed into the
    function as being allowed to have null values

    Args:
        table_name: The name of the table. The only purpose of this is to make error
            messages more descriptive
        data: The data to check
        null_ok (optional): Columns where null values are allowed

    Raises:
        ValueError: When null values are encountered in columns where they are
            not allowed.
    """
    # Check each column of the input data
    for column in data.columns:

        # Check for null values except for those columns which are explicitly allowed to
        # have null values
        if column not in null_ok:
            if (data[column].isna()).any():
                error = (
                    f"'{table_name}' contains null values in the column '{column}'. "
                    f"Some of the associated rows are:\n"
                    + textwrap.indent(
                        data[data[column].isna()].head(5).to_string(), "\t"
                    )
                )
                raise ValueError(error)
