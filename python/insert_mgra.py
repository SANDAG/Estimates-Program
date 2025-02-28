import sqlalchemy as sql
from python.utils import ESTIMATES_ENGINE, MGRA_VERSION, RUN_ID, SQL_FOLDER


def insert_mgra():
    """Insert the MGRA geography."""
    with ESTIMATES_ENGINE.connect() as conn:
        with open(SQL_FOLDER / "insert_mgra.sql") as file:
            query = sql.text(file.read())
            conn.execute(query, {"run_id": RUN_ID, "mgra": MGRA_VERSION})
            conn.commit()
