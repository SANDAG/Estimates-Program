# Container for the Startup module. See the Estimates-Program wiki page for more
# details: https://github.com/SANDAG/Estimates-Program/wiki/Startup

import pandas as pd
import sqlalchemy as sql

import python.utils as utils
import python.tests as tests


def run_startup(debug: bool):
    """Orchestrator function to grab MGRA data, validate, and insert.

    Inserts MGRA geography data from SANDAG's GeoAnalyst database into the
    production database. The data could be directly inserted via a single SQL
    statement but it is instead brought into Python to allow for validation
    and to be written out to csv files for debugging purposes.

    Functionality is segmented into functions for code encapsulation:
        _get_startup_inputs - Get MGRA data from GeoAnalyst
        _validate_startup_inputs - Validate MGRA data
        _insert_startup_outputs - Insert MGRA data to the production database

    Args:
        debug (bool): Whether to run in debug mode
    """
    mgra = _get_startup_inputs()
    _validate_startup_inputs(mgra)

    _insert_startup_outputs(mgra, debug)


def _get_startup_inputs() -> pd.DataFrame:
    """Get input data related to the Startup module"""
    with utils.ESTIMATES_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "startup/get_mgra.sql") as file:
            mgra = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=con,
                params={
                    "run_id": utils.RUN_ID,
                    "mgra_version": utils.MGRA_VERSION,
                    "insert_switch": 0,  # return tabular data only
                },  # type: ignore
            )

    return mgra


def _validate_startup_inputs(mgra: pd.DataFrame) -> None:
    """Validate input data related to the Startup module"""
    tests.validate_data(
        "MGRA Geography",
        mgra,
        row_count={"key_columns": {"mgra"}},
        negative={},
        null={},
    )


def _insert_startup_outputs(mgra: pd.DataFrame, debug: bool) -> None:
    """Insert output data related to the Startup module"""
    # Save locally if in debug mode
    if debug:
        mgra.to_csv(utils.DEBUG_OUTPUT_FOLDER / "inputs_mgra.csv", index=False)
    else:
        # Insert the MGRA geography to the database
        with utils.ESTIMATES_ENGINE.connect() as con:
            with open(utils.SQL_FOLDER / "startup/get_mgra.sql") as file:
                query = sql.text(file.read())
                con.execute(
                    query,
                    {
                        "run_id": utils.RUN_ID,
                        "mgra_version": utils.MGRA_VERSION,
                        "insert_switch": 1,  # write data to database
                    },
                )
                con.commit()
