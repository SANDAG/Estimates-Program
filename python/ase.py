import iteround
import pandas as pd
import sqlalchemy as sql
import python.utils as utils


def _2d_integerize(
    df: pd.DataFrame, row_crtls: list, col_crtls: list, condition: str = "exact"
) -> pd.DataFrame:
    """Integerize values in a DataFrame based on marginal control totals.

    Default behavior is to match the marginal controls exactly. If the
    condition is set to "less than", the function will adjust values such that
    the row values are less than or equal to the row marginal controls. The
    column values always match the column marginal controls.

    Args:
        df (pd.DataFrame): DataFrame containing the values to be integerized.
        row_crtls (list): Row marginal control totals.
        col_crtls (list): Column marginal control totals.
        condition (str): Condition for integerization. Options are 'exact' or
            'less than'. Default is 'exact'.

    Returns:
        pd.DataFrame: DataFrame with integerized values.
    """
    # Ensure the marginal controls match dimensions of the DataFrame
    if df.shape[0] != len(row_crtls) or df.shape[1] != len(col_crtls):
        raise ValueError("Marginal controls do not match DataFrame dimensions.")

    # Condition parameter checks
    if condition not in ["exact", "less than"]:
        raise ValueError("Condition must be 'exact' or 'less than'.")
    elif condition == "exact" and sum(row_crtls) != sum(col_crtls):
        raise ValueError("Marginal controls are inconsistent for 'exact' match.")
    elif condition == "less than" and sum(col_crtls) > sum(row_crtls):
        raise ValueError("Marginal controls are inconsistent for 'less than' match.")

    # Safe round the columns to match the marginal controls
    for i, col in enumerate(df.columns):
        df[col] = iteround.saferound(df[col], places=0, topline=col_crtls[i])

    # Calculate deviations from the row marginal controls
    # Intialize list to store column adjustments made
    row_devs = df.sum(axis=1) - row_crtls
    adjustments = [0] * df.shape[1]

    # Calculate the deviation condition
    if condition == "exact":
        any_deviation = max(map(abs, row_devs)) > 0
    elif condition == "less than":
        any_deviation = max(row_devs) > 0
    else:
        raise ValueError("Condition must be 'exact' or 'less than'.")

    # While there are deviations to adjust
    while any_deviation or max(map(abs, adjustments)) > 0:
        # For rows with + deviation
        for i, row in enumerate(row_devs):
            if row > 0:
                # Calculate adjustment as minimum of total possible and smallest non-zero column value
                # Adjust the column value downward and store adjustments made for that column
                col_idx = df.iloc[i].where(df.iloc[i] > 0).idxmin(skipna=True)
                j = df.columns.get_loc(col_idx)
                adjustment = min(row, df.iat[i, j])
                df.iat[i, j] -= adjustment
                adjustments[j] += adjustment

        # For rows with - deviation
        for i, row in enumerate(row_devs):
            # Stop if no available column adjustments
            if max(adjustments) > 0:
                if row < 0:
                    # Restrict to columns with available adjustments
                    cols = [j for j, v in enumerate(adjustments) if v > 0]

                    # If all values in adjustment columns are 0 skip the row
                    if df.iloc[i, cols].max() <= 0:
                        continue
                    else:
                        # Find the column with the largest non-zero value and available adjustment
                        # Calculate adjustment as minimum of total possible row and column adjustments
                        # Adjust the column value upward and store adjustments made for that column
                        col_idx = df.iloc[i, cols].idxmax()
                        j = df.columns.get_loc(col_idx)
                        adjustment = min(abs(row), adjustments[j])
                        df.iat[i, j] += adjustment
                        adjustments[j] -= adjustment
            else:
                break

        # If no changes were made avoid infinite loop
        if row_devs.equals(df.sum(axis=1) - row_crtls):
            raise ValueError("No adjustments made. Check marginal controls.")
        else:
            # Recalulate the row deviations
            row_devs = df.sum(axis=1) - row_crtls

        # Recalculate the deviation condition
        if condition == "exact":
            any_deviation = max(map(abs, row_devs)) > 0
        elif condition == "less than":
            any_deviation = max(row_devs) > 0
        else:
            raise ValueError("Condition must be 'exact' or 'less than'.")

    return df


def _get_controls_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Get inputs required to calculate regional age/sex/ethnicity controls."""
    with utils.ESTIMATES_ENGINE.connect() as conn:
        # Get regional age/sex/ethnicity controls for total population
        with open(utils.SQL_FOLDER / "ase/get_region_ase_total.sql") as file:
            region_ase_total = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

        # Get regional age/sex/ethnicity group quarters distributions
        with open(utils.SQL_FOLDER / "ase/get_region_gq_ase_dist.sql") as file:
            region_gq_ase_dist = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

        # Get regional population by type output generated by Estimates program
        with open(utils.SQL_FOLDER / "ase/get_region_pop.sql") as file:
            region_pop = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=conn,
                params={
                    "run_id": utils.RUN_ID,
                    "year": year,
                },
            )

    return {
        "region_ase_total": region_ase_total,
        "region_gq_ase_dist": region_gq_ase_dist,
        "region_pop": region_pop,
    }


def _create_controls(controls_inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create regional age/sex/ethnicity controls by population type."""

    # Load input data into separate variables for cleaner manipulation
    region_ase_total = controls_inputs["region_ase_total"]
    region_gq_ase_dist = controls_inputs["region_gq_ase_dist"]
    region_pop = controls_inputs["region_pop"]

    # Scale the regional age/sex/ethnicity total controls to the regional population
    region_ase_total["population"] = iteround.saferound(
        region_ase_total["population"].astype(float),
        places=0,
        topline=region_pop["value"].sum(),
    )

    # Calculate the group quarters age/sex/ethnicity population
    gq_pop = region_gq_ase_dist.merge(
        right=region_pop, left_on="gq_type", right_on="pop_type"
    ).assign(value=lambda x: x["value"] * x["distribution"])

    # Integerize the group quarters age/sex/ethnicity population
    region_gq_ase = _2d_integerize(
        df=(
            gq_pop.sort_values(by=["pop_type"])
            .pivot(
                index=["age_group", "sex", "ethnicity"],
                columns="pop_type",
                values="value",
            )
            .sort_index()
            # .reset_index(drop=True)
        ),
        row_crtls=region_ase_total.sort_values(by=["age_group", "sex", "ethnicity"])[
            "population"
        ].to_list(),
        col_crtls=(
            region_pop[region_pop["pop_type"] != "Household Population"]
            .sort_values(by=["pop_type"])["value"]
            .to_list()
        ),
        condition="less than",
    )

    # Calculate the household age/sex/ethnicity population as the remainder
    # Return the regional age/sex/ethnicity controls by population type
    return (
        region_ase_total.merge(
            right=region_gq_ase.assign(gq=lambda x: x.sum(axis=1)).reset_index(),
            on=["age_group", "sex", "ethnicity"],
        )
        .assign(hhp=lambda x: x["population"] - x["gq"])
        .drop(columns=["population", "gq"])
        .rename(columns={"hhp": "Household Population"})
        .melt(
            id_vars=["run_id", "year", "age_group", "sex", "ethnicity"],
            var_name="pop_type",
        )
    )


def _insert_controls(outputs: pd.DataFrame) -> None:
    """Insert regional age/sex/ethnicity controls to database."""
    with utils.ESTIMATES_ENGINE.connect() as conn:
        outputs.to_sql(
            name="controls_ase",
            con=conn,
            schema="inputs",
            if_exists="append",
            index=False,
        )
