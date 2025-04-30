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
        _get_gq_inputs - Get city level group quarter controls (DOF E-5) and GQ point
            data pre-aggregated into MGRAs
        _validate_gq_inputs - Validate the data from the above function
        _create_gq_outputs - Control MGRA level GQ data to the city level group
            quarter controls
        _validate_gq_outputs - Validate the data from the above function
        _insert_gq - Store both the city level control data and controlled
            MGRA level GQ data into the production database
        _get_hhp_inputs - Get city level household population controls (DOF E-5),
            MGRA level households, and tract level household size
        _validate_hhp_inputs - Validate the data from the above function
        _create_hhp_outputs - Compute MGRA household population, then control to
            city level household population
        _validate_hhp_outputs - Validate the data from the above function
        _insert_hhp - Store certain household population input/output data to
            the production database

    A single utility function is also defined:
        _calculate_hh_adjustment - Calculate adjustments to make to households

    Args:
        year (int): estimates year
    """
    # Start with Group Quarters
    gq_inputs = _get_gq_inputs(year)
    _validate_gq_inputs(gq_inputs)

    gq_outputs = _create_gq_outputs(gq_inputs)
    _validate_gq_outputs(gq_outputs)

    _insert_gq(gq_inputs, gq_outputs)

    # Then do Household Population
    hhp_inputs = _get_hhp_inputs(year)
    _validate_hhp_inputs(year, hhp_inputs)

    hhp_outputs = _create_hhp_outputs(hhp_inputs)
    _validate_hhp_outputs(hhp_outputs)

    _insert_hhp(hhp_inputs, hhp_outputs)


def _get_gq_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get input data related to MGRA group quarters"""
    # Store results here
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


def _validate_gq_inputs(gq_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate the GQ input data"""
    tests.validate_data(
        "City Controls GQ",
        gq_inputs["city_controls"],
        row_count={"key_columns": {"city"}},
        negative={},
        null={},
    )
    tests.validate_data(
        "MGRA GQ raw",
        gq_inputs["gq"],
        row_count={"key_columns": {"mgra", "gq_type"}},
        negative={},
        null={},
    )


def _create_gq_outputs(gq_inputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
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
    return {"gq": pd.concat(results, ignore_index=True)}


def _validate_gq_outputs(gq_outputs: dict[str, pd.DataFrame]) -> None:
    """Validate the GQ output data"""
    tests.validate_data(
        "MGRA GQ controlled",
        gq_outputs["gq"],
        row_count={"key_columns": {"mgra", "gq_type"}},
        negative={},
        null={},
    )


def _insert_gq(
    gq_inputs: dict[str, pd.DataFrame], gq_outputs: dict[str, pd.DataFrame]
) -> None:
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
        gq_outputs["gq"].drop(columns="city").to_sql(
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

    return {"city_controls": city_controls, "tract_controls": tract_controls, "hh": hh}


def _validate_hhp_inputs(year: int, hhp_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate the GQ input data"""

    tests.validate_data(
        "City Controls HHP",
        hhp_inputs["city_controls"],
        row_count={"key_columns": {"city"}},
        negative={},
        null={},
    )
    tests.validate_data(
        "Tract Controls HHP",
        hhp_inputs["tract_controls"],
        row_count={"key_columns": {"tract"}, "year": year},
        negative={},
        null={},
    )
    tests.validate_data(
        "MGRA HH",
        hhp_inputs["hh"],
        row_count={"key_columns": {"mgra"}},
        negative={},
        null={},
    )


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


def _create_hhp_outputs(hhp_inputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
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
    return {"hhp": pd.concat(results, ignore_index=True)}


def _validate_hhp_outputs(hhp_outputs: dict[str, pd.DataFrame]) -> None:
    """Validate the GQ output data"""
    tests.validate_data(
        "MGRA HHP",
        hhp_outputs["hhp"],
        row_count={"key_columns": {"mgra"}},
        negative={},
        null={},
    )


def _insert_hhp(
    hhp_inputs: dict[str, pd.DataFrame], hhp_outputs: dict[str, pd.DataFrame]
) -> None:
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
        hhp_outputs["hhp"].to_sql(
            name="hhp", con=conn, schema="outputs", if_exists="append", index=False
        )
