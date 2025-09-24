# Container for the Staging module. See the Estimates-Program wiki page for more
# details:
# https://github.com/SANDAG/Estimates-Program/wiki/Staging

import sqlalchemy as sql
import python.utils as utils


def run_staging() -> None:
    """Orchestrator function for the staging module

    Mark the run as being completed and update the end date.
    """
    with utils.ESTIMATES_ENGINE.connect() as con:
        script = sql.text(
            f"UPDATE [metadata].[run] "
            f"SET [complete] = 1, [end_date] = GETDATE() "
            f"WHERE [run_id] = {utils.RUN_ID};"
        )
        con.execute(script)
        con.commit()
