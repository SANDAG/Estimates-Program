# Container for the Staging module. See the Estimates-Program wiki page for more
# details:
# https://github.com/SANDAG/Estimates-Program/wiki/Staging

import sqlalchemy as sql
import python.utils as utils


def run_staging() -> None:
    """Orchestrator function for the staging module

    At least for now, all this function does is mark the run as being completed in the
    [metadata].[run] table.
    """
    with utils.ESTIMATES_ENGINE.connect() as con:
        script = sql.text(
            f"UPDATE [metadata].[run] "
            f"SET [complete] = 1 "
            f"WHERE [run_id] = {utils.RUN_ID};"
        )
        con.execute(script)
        con.commit()
