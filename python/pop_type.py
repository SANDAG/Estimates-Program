# Container for the Population by Type module. See the Estimates-Program wiki page for
# more details: https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Type

import iteround
import pandas as pd
import sqlalchemy as sql

import python.utils as utils
import python.tests as tests


def run_pop(year: int):
    """Control function to create population by type (GQ and HHP) data

    Get MGRA group quarters input data, create the output data, then load both into the
    production database. Also get MGRA household population input data, create the
    output data, then load both into the production database. See the wiki linked at the
    top of this file for additional details.

    Functionality is split apart for code encapsulation (function inputs not included):
        _get_gq_inputs() - Get city level group quarter controls (DOF E-5) and GQ point
            data pre-aggregated into MGRAs
        _create_gq_outputs() - Control MGRA level GQ data to the city level group
            quarter controls
        _insert_gq_outputs() - Store both the city level control data and controlled
            MGRA level GQ data into the production database
        _get_hhp_inputs() - Get city level household population controls (DOF E-5),
            MGRA level households, and tract level household size
        _create_hhp_outputs() - Compute MGRA household population, then control to
            city level household population
        _insert_hhp_outputs() - Store certain household population input/output data to
            the production database

    Args:
        year (int): estimates year
    """
    # Start with Group Quarters
    gq_inputs = _get_gq_inputs(year)
    gq = _create_gq_outputs(gq_inputs)
    _insert_gq_data(gq_inputs, gq)

    # Then do Household Population
    hhp_inputs = _get_hhp_inputs(year)
    hhp = _create_hhp_outputs(hhp_inputs)
    _insert_hhp_data(hhp_inputs, hhp)


def _get_gq_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get input data related to MGRA group quarters"""

    with utils.ESTIMATES_ENGINE.connect() as conn:
        # Get city total group quarters controls
        with open(utils.SQL_FOLDER / "pop_type/get_city_controls_gq.sql") as file:
            city_controls = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )
        tests.validate_row_count("City Controls GQ", city_controls, {"city"})
        tests.validate_negative_null("City Controls GQ", city_controls)

        # Get raw group quarters data
        with open(utils.SQL_FOLDER / "pop_type/get_mgra_gq.sql") as file:
            gq = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "mgra_version": utils.MGRA_VERSION,
                    "gis_server": utils.GIS_SERVER,
                },
            )
        tests.validate_row_count("MGRA GQ raw", gq, {"mgra", "gq_type"})
        tests.validate_negative_null("MGRA GQ raw", gq)

    return {"city_controls": city_controls, "gq": gq}


def _create_gq_outputs(gq_inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create MGRA group quarters"""

    # Load input data into separate variables for cleaner manipulation
    city_controls = gq_inputs["city_controls"]
    gq = gq_inputs["gq"]

    # Store results here
    results = []

    # Control and integerize group quarters data
    for city in gq["city"].unique():

        # Copy the necessary input data for this city
        city_gq = gq[gq["city"] == city].copy(deep=True)
        city_control = city_controls[city_controls["city"] == city]["value"].values[0]

        # Scale values to match control
        if city_control > 0:
            multiplier = city_control / city_gq["value"].sum()
            city_gq["value"] *= multiplier
            city_gq["value"] = iteround.saferound(city_gq["value"], places=0)
        else:
            city_gq["value"] = 0

        # Store results for this city
        results.append(city_gq)

    # Combine the data for each city together
    return pd.concat(results, ignore_index=True)


def _insert_gq_data(gq_inputs: dict[str, pd.DataFrame], gq: pd.DataFrame) -> None:
    """Insert both input and output data for MGRA group quarters"""

    # Insert controls and group quarters results to database
    with utils.ESTIMATES_ENGINE.connect() as conn:
        gq_inputs["city_controls"].to_sql(
            name="controls_city",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        tests.validate_row_count("MGRA GQ controlled", gq, {"mgra", "gq_type"})
        tests.validate_negative_null("MGRA GQ controlled", gq)
        gq.drop(columns="city").to_sql(
            name="gq",
            con=conn,
            schema="outputs",
            if_exists="append",
            index=False,
        )


def _get_hhp_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get input data related to MGRA household population"""

    with utils.ESTIMATES_ENGINE.connect() as conn:
        # Get city total household population controls
        with open(utils.SQL_FOLDER / "pop_type/get_city_controls_hhp.sql") as file:
            city_controls = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )
        tests.validate_row_count("City Controls HHP", city_controls, {"city"})
        tests.validate_negative_null("City Controls HHP", city_controls)

        # Get tract level household size controls
        with open(utils.SQL_FOLDER / "pop_type/get_tract_controls_hhs.sql") as file:
            tract_controls = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )
        tests.validate_row_count("Tract Controls HHS", tract_controls, {"tract"}, year)
        tests.validate_negative_null("Tract Controls HHS", tract_controls)

        # Get MGRA level households
        with open(utils.SQL_FOLDER / "pop_type/get_mgra_hh.sql") as file:
            hh = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "mgra_version": utils.MGRA_VERSION,
                },
            )
        tests.validate_row_count("MGRA HH", hh, {"mgra"})
        tests.validate_negative_null("MGRA HH", hh)

    return {"city_controls": city_controls, "tract_controls": tract_controls, "hh": hh}


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
    hh = hhp_inputs["hh"]

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

        # Compute the difference between our initial estimate of HHP and the control
        # value from DOF
        current_hhp = hhp["value_hhp"].sum()
        control_hhp = city_controls[city_controls["city"] == city]["value"].values[0]
        multiplier = control_hhp / current_hhp
        hhp["value_hhp"] *= multiplier

        # Integerize household population while preserving the total amount
        hhp["value_hhp"] = iteround.saferound(hhp["value_hhp"], places=0)

        # Reallocate household population which contradicts the number of households.
        # See the _calculate_hhp_adjustment() function for exact situations
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
            # decrease household population to be below the number of households. Note
            # this also prevents decreasing household population to below zero
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


def _insert_hhp_data(hhp_inputs: dict[str, pd.DataFrame], hhp: pd.DataFrame) -> None:
    """Insert intput and output data related to household population"""

    # Insert input and output data to database
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

        tests.validate_row_count("MGRA HHP", hhp, {"mgra"})
        tests.validate_negative_null("MGRA HHP", hhp)
        hhp.to_sql(
            name="hhp", con=conn, schema="outputs", if_exists="append", index=False
        )
