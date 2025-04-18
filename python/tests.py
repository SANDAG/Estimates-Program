# Testing suite for the entire Estimates Program project. At least for now, all tests
# are integration tests, in the sense that they run on actual module inputs and outputs.

# TODO: Integration with the Python logging library. The idea is that critical errors
# will both raise an error and be logged, while warnings will only be logged

import pandas as pd

import textwrap
import math

#####################
# HELPFUL CONSTANTS #
#####################

# The key is the column name and the value is the number of unique values there should
# be in the column
_ROW_COUNTS = {
    "city": 19,
    "mgra": 24321,
    "2010_tract": 627,
    "2020_tract": 736,
    "structure_type": 4,
    "gq_type": 4,
}


#########
# TESTS #
#########


def validate_row_count(
    table_name: str, data: pd.DataFrame, key_columns: list[str], year: int = None
) -> None:
    """Verify that the provided data has the correct number of rows

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
    # Verify that the provided key columns actually exist
    for column in key_columns:
        if column not in data.columns:
            raise ValueError(
                f"'{table_name}' is missing the required key column {column}"
            )

    # Slightly alter the tract column if it exists
    if "tract" in key_columns:
        census_year = year // 10 * 10
        data = data.rename(columns={"tract": f"{census_year}_tract"})
        key_columns.remove("tract")
        key_columns.append(f"{census_year}_tract")

    # Check that each key column has the correct number of unique values
    for column in key_columns:
        if data[column].nunique() != _ROW_COUNTS[column]:
            raise ValueError(
                f"'{table_name}' should have {_ROW_COUNTS[column]} unique values "
                f"in the column '{column}', but it has {data[column].nunique()}"
            )

    # Check that the total number of rows is correct, assuming that we do the CROSS JOIN
    # of all keys columns
    n_rows = math.prod(
        [value for column, value in _ROW_COUNTS.items() if column in key_columns]
    )
    if data.shape[0] != n_rows:
        row_count_explanation = " x ".join(
            [
                f"{value:,} {column}"
                for column, value in _ROW_COUNTS.items()
                if column in key_columns
            ]
        )
        raise ValueError(
            f"'{table_name}' should have {n_rows} rows "
            f"({row_count_explanation}) but it has {data.shape[0]}"
        )


def validate_negative_null(
    table_name: str,
    data: pd.DataFrame,
    negative_ok: list[str] = None,
    null_ok: list[str] = None,
) -> None:
    """Verify that the provided data does not contain negative/null values

    Checks will be performed on all columns unless they are explicitly passed into the
    function as being allowed to have negative/null values. Note that the negative
    value check only applies to columns of numeric data type

    Args:
        table_name: The name of the table. The only purpose of this is to make error
            messages more descriptive
        data: The data to check
        negative_ok (optional): Columns where negative values are allowed
        null_ok (optional): Columns where null values are allowed

    Raises:
        ValueError: When negative/null values are encountered in columns where they are
            not allowed.
    """
    # Avoid issues with mutable default parameter values
    if negative_ok is None:
        negative_ok = []
    if null_ok is None:
        null_ok = []

    # Check each column of the input data
    for column in data.columns:

        # Check for negative values except for those columns which are explicitly
        # allowed to be negative
        if column not in negative_ok:
            if pd.api.types.is_numeric_dtype(data[column]) and (data[column] < 0).any():
                error = (
                    f"'{table_name}' contains negative values in the column '{column}'. "
                    f"The associated rows are:\n"
                    + textwrap.indent(data[data[column] < 0].to_string(), "\t")
                )
                raise ValueError(error)

        # Check for null values except for those columns which are explicitly allowed to
        # have null values
        if column not in null_ok:
            if (data[column].isna()).any():
                error = (
                    f"'{table_name}' contains null values in the column '{column}'. "
                    f"The associated rows are:\n"
                    + textwrap.indent(data[data[column].isna()].to_string(), "\t")
                )
                raise ValueError(error)
