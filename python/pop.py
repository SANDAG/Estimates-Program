# Container for the Population by Type module. See the Estimates-Program wiki page for
# more details: https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Type

import iteround
import pandas as pd
import sqlalchemy as sql
import python.utils as utils


def run_pop(year: int):
    """Control function to create population by type data

    TODO: Create household population

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
    pop_inputs = _get_inputs(year)
    pop_outputs = _create_outputs(year, pop_inputs)
    _insert_outputs(year, pop_outputs)


def _get_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get input data related to the Population by Type module"""

    # Store all intput data here
    pop_inputs = {}

    with utils.ESTIMATES_ENGINE.connect() as conn:
        # Get city total group quarters controls
        with open(utils.SQL_FOLDER / "pop_type/get_city_controls_gq.sql") as file:
            pop_inputs["city_controls"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

        # Get raw group quarters data
        with open(utils.SQL_FOLDER / "pop_type/get_mgra_gq.sql") as file:
            pop_inputs["gq"] = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "mgra_version": utils.MGRA_VERSION,
                    "gis_server": utils.GIS_SERVER,
                },
            )

    return pop_inputs


def _create_outputs(
    year: int, pop_inputs: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    """Create output data related to the Population by Type module"""

    # Control and integerize group quarters data
    for city in pop_inputs["gq"]["city"].unique():
        values = pop_inputs["gq"][pop_inputs["gq"]["city"] == city]["value"]
        control = pop_inputs["city_controls"][
            pop_inputs["city_controls"]["city"] == city
        ]["value"].values[0]

        # Scale values to match control
        if control > 0:
            values = control / values.sum() * values
            values = iteround.saferound(values, places=0)
            values = [int(f) for f in values]
        else:
            values = 0

        # Update values in the DataFrame
        pop_inputs["gq"].loc[pop_inputs["gq"]["city"] == city, "value"] = values

    # The variable is still called pop_inputs but it has been modified into the output
    # data
    return pop_inputs


def _insert_outputs(year: int, pop_outputs: dict[str, pd.DataFrame]) -> None:
    """Insert output data related to the Population by Type module"""

    # Insert controls and group quarters results to database
    with utils.ESTIMATES_ENGINE.connect() as conn:
        pop_outputs["city_controls"].to_sql(
            name="controls_city",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        pop_outputs["gq"].drop(columns="city").to_sql(
            name="gq",
            con=conn,
            schema="outputs",
            if_exists="append",
            index=False,
        )
