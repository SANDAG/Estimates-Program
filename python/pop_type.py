# Container for the Population by Type module. See the Estimates-Program wiki page for
# more details: https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Type

import iteround
import pandas as pd
import sqlalchemy as sql
import python.utils as utils


def run_pop(year: int):
    """Control function to create population by type data

    Gets GQ data from SANDAG's GQ point database and controls to DOF E-5 city level
    group quarters counts. Results are inserted into the production database

    Functionality is split apart for code encapsulation (function inputs not included):
        _get_inputs() - Get city level group quarter controls (DOF E-5) and GQ point
            data pre-aggregated into MGRAs
        _create_outputs() - Control MGRA level GQ data to the city level group quarter
            controls
        _insert_outputs() - Store both the city level control data and controlled MGRA
            level GQ data into the production database

    Args:
        year (int): estimates year
    """
    # Start with Group Quarters
    gq_inputs = _get_gq_inputs(year)
    gq_outputs = _create_gq_outputs(gq_inputs)
    _insert_gq_outputs(year, gq_outputs)

    # Then do Household Population
    hhp_inputs = _get_hhp_inputs(year)
    hhp = _create_hhp_outputs(hhp_inputs)
    _insert_hhp_outputs(year, hhp_inputs, hhp)


def _get_gq_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get input data related to the Population by Type module"""

    # Store all intput data here
    gq_inputs = {}

    with utils.ESTIMATES_ENGINE.connect() as conn:
        # Get city total group quarters controls
        with open(utils.SQL_FOLDER / "pop_type/get_city_controls_gq.sql") as file:
            gq_inputs["city_controls"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

        # Get raw group quarters data
        with open(utils.SQL_FOLDER / "pop_type/get_mgra_gq.sql") as file:
            gq_inputs["gq"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "mgra_version": utils.MGRA_VERSION,
                    "gis_server": utils.GIS_SERVER,
                },
            )

    return gq_inputs


def _create_gq_outputs(gq_inputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Create output data related to the Population by Type module"""

    # Control and integerize group quarters data
    for city in gq_inputs["gq"]["city"].unique():
        values = gq_inputs["gq"][gq_inputs["gq"]["city"] == city]["value"]
        control = gq_inputs["city_controls"][
            gq_inputs["city_controls"]["city"] == city
        ]["value"].values[0]

        # Scale values to match control
        if control > 0:
            values = control / values.sum() * values
            values = iteround.saferound(values, places=0)
            values = [int(f) for f in values]
        else:
            values = 0

        # Update values in the DataFrame
        gq_inputs["gq"].loc[gq_inputs["gq"]["city"] == city, "value"] = values

    # The variable is still called gq_inputs but it has been modified into the output
    # data
    return gq_inputs


def _insert_gq_outputs(year: int, gq_outputs: dict[str, pd.DataFrame]) -> None:
    """Insert output data related to the Population by Type module"""

    # Insert controls and group quarters results to database
    with utils.ESTIMATES_ENGINE.connect() as conn:
        gq_outputs["city_controls"].to_sql(
            name="controls_city",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        gq_outputs["gq"].drop(columns="city").to_sql(
            name="gq",
            con=conn,
            schema="outputs",
            if_exists="append",
            index=False,
        )


def _get_hhp_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get input data related to the Population by Type module"""

    # Store all intput data here
    hhp_inputs = {}

    with utils.ESTIMATES_ENGINE.connect() as conn:
        # Get city total household population controls
        with open(utils.SQL_FOLDER / "pop_type/get_city_controls_hhp.sql") as file:
            hhp_inputs["city_controls"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

        # Get tract level household size controls
        with open(utils.SQL_FOLDER / "pop_type/get_tract_controls_hhs.sql") as file:
            hhp_inputs["tract_controls"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

        # Get MGRA level households
        with open(utils.SQL_FOLDER / "pop_type/get_mgra_hh.sql") as file:
            hhp_inputs["mgra_hh"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "mgra_version": utils.MGRA_VERSION,
                },
            )

    return hhp_inputs


def _calculate_hhp_adjustment(hhp: int, hh: int) -> int:
    """Calculate adjustments to make to household population.

    Function determines amount of adjustment needed to ensure consistency between
    household population and households. This means:
    * Household population is never negative
    * If there are no households, then there is no household population
    * If there are households, there is at least one household population per household

    Args:
        hhp: Household population
        hh: Households

    Returns:
        The amount of adjustment needed
    """
    if (hhp < 0) or (hhp > 0 and hh == 0):
        return -1 * hhp
    elif hh > 0 and (hhp < hh):
        return hh - hhp
    else:
        return 0


def _create_hhp_outputs(hhp_inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Calculate MGRA level household population controlled to DOF"""

    # Load input data into separate variables for cleaner manipulation
    city_controls = hhp_inputs["city_controls"]
    tract_controls = hhp_inputs["tract_controls"]
    hh = hhp_inputs["mgra_hh"]

    # Control the household population in each city to DOF. Store results separately
    # and join together at the end for cleaner code
    results = []
    for city in hh["city"].unique():

        # Get an initial decimal estimate of the household population in each MGRA by
        # applying tract level household size to MGRA level households
        hhp = (
            hh[hh["city"] == city]
            .merge(tract_controls, on=["run_id", "year", "tract"])
            .rename(columns={"hh": "value_hh", "value": "value_hhs"})
            .assign(value_hhp=lambda df: df["value_hh"] * df["value_hhs"])
            .drop(columns=["tract", "value_hhs"])
        )

        # Compute the difference between our initial estimate of hhp and the control
        # value from DOF
        current_hhp = hhp["value_hhp"].sum()
        control_hhp = city_controls[city_controls["city"] == city]["value"].values[0]
        multiplier = control_hhp / current_hhp
        hhp["value_hhp"] *= multiplier

        # Integerize household population while preserving the total amount
        hhp["value_hhp"] = iteround.saferound(hhp["value_hhp"], places=0)

        # Reallocate household population where it is less than zero or where there is
        # household population but no households
        hhp["adjustment"] = hhp.apply(
            lambda x: _calculate_hhp_adjustment(hhp=x["value_hhp"], hh=x["value_hh"]),
            axis=1,
        )
        hhp["value_hhp"] = hhp["value_hhp"] + hhp["adjustment"]
        adjustment = hhp["adjustment"].sum()
        hhp.drop(columns="adjustment", inplace=True)

        # Add/subtract household population across all MGRAs until the amount to adjust
        # is zero
        while adjustment != 0:

            # If the adjustment amount is positive, that means we need to subtract
            # household population from MGRAs to exactly match control totals. We cannot
            # decrease household population to be below the number of households
            if adjustment > 0:
                condition = hhp["value_hhp"] > hhp["value_hh"]
                factor = -1

            # If adjustment is negative, that means we need to add household population
            # to MGRAs to exactly match control totals. We are free to add household
            # population anywhere except for where there are no households
            else:
                condition = hhp["value_hh"] > 0
                factor = 1

            # Adjust MGRAs prioritizing those with the largest amount of households
            records = int(min(len(hhp.index), abs(adjustment)))
            if records > 0:
                indices = (
                    hhp[condition]
                    .sort_values(by="value_hh", ascending=False)
                    .head(records)
                    .index
                )

                hhp.loc[indices, "value_hhp"] += factor

                # Recalculate total adjustment number
                adjustment += records * factor
            else:
                raise ValueError("Cannot balance households.")

        # Append results for this city
        results.append(
            hhp.drop(columns=["city", "value_hh"]).rename(
                columns={"value_hhp": "value"}
            )
        )

    # UNION ALL the results for each city together
    return pd.concat(results, ignore_index=True)


def _insert_hhp_outputs(
    year: int, hhp_inputs: dict[str, pd.DataFrame], hhp: pd.DataFrame
) -> None:
    """Insert data related to household population"""

    # Insert controls and group quarters results to database
    with utils.ESTIMATES_ENGINE.connect() as conn:
        hhp_inputs["city_controls"].to_sql(
            name="controls_city",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        hhp_inputs["tract_controls"].assign(metric="Household Size").to_sql(
            name="controls_tract",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        hhp.to_sql(
            name="hhp", con=conn, schema="outputs", if_exists="append", index=False
        )
