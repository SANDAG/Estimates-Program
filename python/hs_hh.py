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
        _create_hh - Calculate households by MGRA applying occupancy
            controls, integerization, and reallocation
        _insert_hh - Insert occupancy controls and households by MGRA to
            production database

    A single utility function is also defined:
        _calculate_hh_adjustment - Calculate adjustments to make to households

    Args:
        year (int): estimates year
    """
    # Create and insert housing stock by MGRA to production database
    _insert_hs(year=year)

    # Get housing stock and occupancy controls
    hh_inputs = _get_hh_inputs(year=year)

    # Calculate households by MGRA
    hh = _create_hh(inputs=hh_inputs)

    # Insert occupancy controls and households by MGRA to production database
    _insert_hh(inputs=hh_inputs, outputs=hh)


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


def _insert_hs(year: int) -> None:
    """Insert housing stock by MGRA for a given year."""
    with utils.ESTIMATES_ENGINE.connect() as conn:
        with open(utils.SQL_FOLDER / "hs_hh/create_mgra_hs.sql") as file:
            query = sql.text(file.read())
            conn.execute(
                query,
                {
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "gis_server": utils.GIS_SERVER,
                },
            )
            conn.commit()


def _get_hh_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get housing stock and occupancy controls."""
    with utils.ESTIMATES_ENGINE.connect() as conn:
        # Get city occupancy controls
        with open(utils.SQL_FOLDER / "hs_hh/get_city_controls_hh.sql") as file:
            city_controls = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )
        tests.validate_row_count("City Controls Households", city_controls, {"city"})
        tests.validate_negative_null("City Controls Households", city_controls)

        # Get tract occupancy controls
        with open(utils.SQL_FOLDER / "hs_hh/get_tract_controls_hh.sql") as file:
            tract_controls = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )
        tests.validate_row_count(
            "Tract Controls Occupancy Rate",
            tract_controls,
            {"tract", "structure_type"},
            year,
        )
        tests.validate_negative_null("Tract Controls Occupancy Rate", tract_controls)

        # Get housing stock output data
        with open(utils.SQL_FOLDER / "hs_hh/get_mgra_hs.sql") as file:
            hs = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "mgra_version": utils.MGRA_VERSION,
                },
            )
        tests.validate_row_count("MGRA Housing Stock", hs, {"mgra", "structure_type"})
        tests.validate_negative_null("MGRA Housing Stock", hs)

    return {
        "city_controls": city_controls,
        "tract_controls": tract_controls,
        "hs": hs,
    }


def _create_hh(inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Calculate households by MGRA."""
    city_controls = inputs["city_controls"]
    tract_controls = inputs["tract_controls"]
    hs = inputs["hs"]

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

    return pd.concat(result, ignore_index=True)


def _insert_hh(inputs: dict[str, pd.DataFrame], outputs: pd.DataFrame) -> None:
    """Insert occupancy controls and households results to database."""
    with utils.ESTIMATES_ENGINE.connect() as conn:
        inputs["city_controls"].to_sql(
            name="controls_city",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        inputs["tract_controls"].assign(
            metric=lambda x: "Occupancy Rate - " + x["structure_type"]
        ).drop(columns="structure_type").to_sql(
            name="controls_tract",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        tests.validate_row_count("MGRA Households", outputs, {"mgra", "structure_type"})
        tests.validate_negative_null("MGRA Households", outputs)
        outputs.to_sql(
            name="hh",
            con=conn,
            schema="outputs",
            if_exists="append",
            index=False,
        )
