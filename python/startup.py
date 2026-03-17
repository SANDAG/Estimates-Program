# Container for the Startup module. See the Estimates-Program wiki page for more
# details: https://github.com/SANDAG/Estimates-Program/wiki/Startup

import sqlalchemy as sql
import python.utils as utils


def run_startup(debug: bool):
    """Control function to call the correct functions in the correct order"""
    # Startup requires no input data
    # Startup requires no processing of input data
    _insert_outputs(debug)


def _insert_outputs(debug: bool):
    """Insert output data related to the Startup module"""

    # Skip insertion if running in debug mode
    if debug:
        return

    # Insert the MGRA geography
    with utils.ESTIMATES_ENGINE.connect() as con:
        with open(utils.SQL_FOLDER / "insert_mgra.sql") as file:
            query = sql.text(file.read())
            con.execute(query, {"run_id": utils.RUN_ID, "mgra": utils.MGRA_VERSION})
            con.commit()
