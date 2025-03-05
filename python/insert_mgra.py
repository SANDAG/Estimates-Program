import sqlalchemy as sql
import python.utils as utils


def insert_mgra():
    """Insert the MGRA geography."""
    with utils.ESTIMATES_ENGINE.connect() as conn:
        with open(utils.SQL_FOLDER / "insert_mgra.sql") as file:
            query = sql.text(file.read())
            conn.execute(query, {"run_id": utils.RUN_ID, "mgra": utils.MGRA_VERSION})
            conn.commit()
