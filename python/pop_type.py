"""Population by type estimates module."""

import iteround
import pandas as pd
import sqlalchemy as sql
import python.utils as utils


def insert_gq(year: int) -> None:
    """Insert group quarters by MGRA for a given year.

    This function takes raw MGRA group quarters data by type, scales it to
    match total group quarters controls at the city level from the
    California Department of Finance and integerizes the results. The results
    are then inserted into the production database along with the controls.

    Args:
        year (int): estimates year
    """
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

    # Control and integerize group quarters data
    for city in gq["city"].unique():
        values = gq[gq["city"] == city]["value"]
        control = city_controls[city_controls["city"] == city]["value"].values[0]

        # Scale values to match control
        if control > 0:
            values = control / values.sum() * values
            values = iteround.saferound(values, places=0)
            values = [int(f) for f in values]
        else:
            values = 0

        # Update values in the DataFrame
        gq.loc[gq["city"] == city, "value"] = values

    # Insert controls and group quarters results to database
    with utils.ESTIMATES_ENGINE.connect() as conn:
        city_controls.to_sql(
            name="controls_city",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )

        gq.drop(columns="city").to_sql(
            name="gq",
            con=conn,
            schema="outputs",
            if_exists="append",
            index=False,
        )
