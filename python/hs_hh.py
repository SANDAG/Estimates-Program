"""Housing stock and household estimates module."""

import sqlalchemy as sql
import python.utils as utils


def insert_hs(year: int) -> None:
    """Insert housing stock by MGRA for a given year."""
    with utils.ESTIMATES_ENGINE.connect() as conn:
        with open(utils.SQL_FOLDER / "hs_hh/insert_hs.sql") as file:
            query = sql.text(file.read())
            conn.execute(
                query,
                {
                    "run_id": utils.RUN_ID,
                    "year": year,
                    "gis_server": utils.GIS_SERVER,
                },
            )
            conn.commit()
