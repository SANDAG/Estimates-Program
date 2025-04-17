# Testing suite for the entire Estimates Program project. At least for now, all tests
# are integration tests, in the sense that they run on actual module inputs and outputs.

# TODO: Integration with the Python logging library. The idea is that critical errors
# will both raise an error and be logged, while warnings will only be logged

import pandas as pd
import typing
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
):
    """Check that the provided data has the correct number of rows

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
