# Container for the Housing Stock and Households module. See the Estimates-Program wiki
# page for more details:
# https://github.com/SANDAG/Estimates-Program/wiki/Housing-and-Households

import iteround
import pandas as pd
import sqlalchemy as sql

import python.utils as utils
import python.tests as tests


def run_hs_hh(year: int) -> None:
    """Orchestrator function to calculate and insert housing stock and households.

    Inserts housing stock by MGRA from SANDAG's LUDU database for a given year
    into the production database. Then calculates households by MGRA using
    the housing stock by MGRA, applying both Census tract and jurisdiction-level
    occupancy controls, and then runs an integerization and reallocation
    procedure to produce total households by MGRA. Results are inserted into
    the production database.

    Functionality is segmented into functions for code encapsulation:
        _insert_hs - Insert housing stock by MGRA for a given year
        _get_hh_inputs - Get housing stock and occupancy controls
        _validate_hh_inputs - Validate the households input data from the above function
        _create_hh - Calculate households by MGRA applying occupancy
            controls, integerization, and reallocation
        _validate_hh_outputs - Validate the households output data from the above
            function
        _insert_hh - Insert occupancy controls and households by MGRA to
            production database

    A single utility function is also defined:
        _calculate_hh_adjustment - Calculate adjustments to make to households

    Args:
        year (int): estimates year
    """
    # Do housing stock and households at the same time. Note that we could directly
    # insert housing stock data from server --> server, however we pull the data into
    # Python to run additional checks
    hs_hh_inputs = _get_hs_hh_inputs(year)
    _validate_hs_hh_inputs(year, hs_hh_inputs)

    hs_hh_outputs = _create_hs_hh(hs_hh_inputs)
    _validate_hs_hh_outputs(hs_hh_outputs)

    _insert_hs_hh(hs_hh_inputs, hs_hh_outputs)


def _calculate_hh_adjustment(households: int, housing_stock: int) -> int:
    """Calculate adjustments to make to households.

    Function determines amount of adjustment needed to make to households
    to ensure that the number of households is not greater than the housing
    stock and that the number of households is not negative.

    Args:
        households (int): number of households
        housing_stock (int): number of housing units (stock)

    Returns:
        int: adjustment needed to make to households
    """
    if households > housing_stock:
        return -1 * (households - housing_stock)
    elif households < 0:
        return -1 * households
    else:
        return 0


def _get_hs_hh_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get housing stock and occupancy controls."""
    with utils.ESTIMATES_ENGINE.connect() as conn:
        # Store results here
        hs_hh_inputs = {}

        # Get MGRA level housing stock, aggregated from LUDU
        with open(utils.SQL_FOLDER / "hs_hh/get_mgra_hs.sql") as file:
            hs_hh_inputs["hs"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "mgra_version": utils.MGRA_VERSION,
                    "gis_server": utils.GIS_SERVER,
                },
            )

        # Get city occupancy controls
        with open(utils.SQL_FOLDER / "hs_hh/get_city_controls_hh.sql") as file:
            hs_hh_inputs["city_controls"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

        # Get tract occupancy controls
        with open(utils.SQL_FOLDER / "hs_hh/get_tract_controls_hh.sql") as file:
            hs_hh_inputs["tract_controls"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

    return hs_hh_inputs


def _validate_hs_hh_inputs(year: int, hs_hh_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate the household input data"""
    tests.validate_data(
        "MGRA Housing Stock",
        hs_hh_inputs["hs"],
        row_count={"key_columns": {"mgra", "structure_type"}},
        negative={},
        null={},
    )
    tests.validate_data(
        "City Controls Households",
        hs_hh_inputs["city_controls"],
        row_count={"key_columns": {"city"}},
        negative={},
        null={},
    )
    tests.validate_data(
        "Tract Controls Occupancy Rate",
        hs_hh_inputs["tract_controls"],
        row_count={"key_columns": {"tract", "structure_type"}, "year": year},
        negative={},
        null={},
    )


def _create_hs_hh(hs_hh_inputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Calculate households by MGRA."""
    city_controls = hs_hh_inputs["city_controls"]
    tract_controls = hs_hh_inputs["tract_controls"]
    hs = hs_hh_inputs["hs"]

    # Create, control, and integerize total households by MGRA for each city
    result = []
    for city in hs["city"].unique():
        # Apply tract-level occupancy controls by structure type
        hh = (
            hs[hs["city"] == city]
            .merge(
                right=tract_controls,
                on=["run_id", "year", "tract", "structure_type"],
                suffixes=["_hs", "_rate"],
            )
            .assign(value_hh=lambda x: x["value_hs"] * x["value_rate"])
            .drop(columns=["tract", "value_rate"])
        )

        # Compute overall occupancy rate and apply city occupancy control
        obs_rate = hh["value_hh"].sum() / hh["value_hs"].sum()
        city_rate = city_controls[city_controls["city"] == city]["value"].values[0]
        hh["value_hh"] *= city_rate / obs_rate

        # Integerize households preserving total
        hh["value_hh"] = iteround.saferound(hh["value_hh"], places=0)

        # Reallocate households where households > housing stock or < 0
        # Add/remove households tracking total adjustment number
        hh["adjustment"] = hh.apply(
            lambda x: _calculate_hh_adjustment(
                households=x["value_hh"], housing_stock=x["value_hs"]
            ),
            axis=1,
        )

        hh["value_hh"] = hh["value_hh"] + hh["adjustment"]
        adjustment = hh["adjustment"].sum()
        hh.drop(columns="adjustment", inplace=True)

        # Add/Subtract households across all possible records
        # Until total adjustment number has been reallocated
        while adjustment != 0:
            # If adjustment was positive then subtract
            if adjustment > 0:
                condition = hh["value_hh"] > 0
                factor = -1
            # If adjustment was negative then add
            elif adjustment < 0:
                condition = hh["value_hh"] < hh["value_hs"]
                factor = 1
            else:
                continue

            # Adjust possible records prioritizing the largest households
            records = int(min(len(hh.index), abs(adjustment)))
            if records > 0:
                indices = (
                    hh[condition]
                    .sort_values(by="value_hh", ascending=False)
                    .head(records)
                    .index
                )

                hh.loc[indices, "value_hh"] += factor

                # Recalculate total adjustment number
                adjustment += records * factor
            else:
                raise ValueError("Cannot balance households.")

        # Append city result to list
        result.append(
            hh.drop(columns=["city", "value_hs"]).rename(columns={"value_hh": "value"})
        )

    return {"hh": pd.concat(result, ignore_index=True)}


def _validate_hs_hh_outputs(hs_hh_outputs: dict[str, pd.DataFrame]) -> None:
    """Validate the household outputs data"""
    tests.validate_data(
        "MGRA Households",
        hs_hh_outputs["hh"],
        row_count={"key_columns": {"mgra", "structure_type"}},
        negative={},
        null={},
    )


def _insert_hs_hh(
    hs_hh_inputs: dict[str, pd.DataFrame], hs_hh_outputs: dict[str, pd.DataFrame]
) -> None:
    """Insert occupancy controls and households results to database."""
    with utils.ESTIMATES_ENGINE.connect() as conn:
        hs_hh_inputs["hs"].drop(columns=["tract", "city"]).to_sql(
            name="hs",
            con=conn,
            schema="outputs",
            if_exists="append",
            index=False,
        )
        hs_hh_inputs["city_controls"].to_sql(
            name="controls_city",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )
        hs_hh_inputs["tract_controls"].assign(
            metric=lambda x: "Occupancy Rate - " + x["structure_type"]
        ).drop(columns="structure_type").to_sql(
            name="controls_tract",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )
        hs_hh_outputs["hh"].to_sql(
            name="hh",
            con=conn,
            schema="outputs",
            if_exists="append",
            index=False,
        )
