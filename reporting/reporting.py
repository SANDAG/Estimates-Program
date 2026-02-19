# Python script to automatically run QA/QC scripts and report out the results.
# Additionally, for ASE data, it flags rows which had a significant change, see
# the below Excel sheet for additional details:
# https://github.com/SANDAG/Series-15-Urban-Development-Model/blob/main/Other/Significant%20Change.xlsx

# Main configuration, what run_id to operate on
RUN_ID = 245

# We cannot import python.utils, as just importing will cause a new [run_id]` value and
# new log file to be created. Instead, copy what we need for now :(
import tomllib
import pathlib
import textwrap
import sqlalchemy as sql
import pandas as pd
import numpy as np

ROOT_FOLDER = pathlib.Path(__file__).parent.resolve().parent
try:
    with open(ROOT_FOLDER / "secrets.toml", "rb") as file:
        _secrets = tomllib.load(file)
except IOError:
    raise IOError("secrets.toml does not exist, see README.md")

# Create SQLAlchemy engine(s)
ESTIMATES_ENGINE = sql.create_engine(
    "mssql+pyodbc://@"
    + _secrets["sql"]["estimates"]["server"]
    + "/"
    + _secrets["sql"]["estimates"]["database"]
    + "?trusted_connection=yes&driver="
    + "ODBC Driver 17 for SQL Server",
    fast_executemany=True,
)

# Store a list of the scripts to run. It is assumed that each script only takes in
# a parameter for [run_id]. It is also assumed that rows of data will only be returned
# if there is an error, in which case it will be printed out
qa_qc_scripts = {
    "Check city control totals": "check_controls_city.sql",
    "Check region ASE controls": "check_controls_region_ase.sql",
    "Check cross-table pop by type": "check_cross_table_pop_by_type.sql",
    "Check cross-table total hh": "check_cross_table_total_hh.sql",
    "Check MGRA restrictions": "check_mgra_restrictions.sql",
    "Check every HH has HS": "check_every_hh_has_hs.sql",
    "Check every HHP has HH": "check_every_hhp_has_hh.sql",
    "Check implied HHP vs actual HHP": "check_implied_hhp_vs_actual_hhp.sql",
    "Check householders vs households": "check_householders_vs_households.sql",
}

# Run each script, printing out status messages if necessary:
with ESTIMATES_ENGINE.connect() as con:
    for script_name, file_path in qa_qc_scripts.items():
        print(script_name)
        with open(file_path) as file:
            results = pd.read_sql_query(
                sql=sql.text(file.read()), con=con, params={"run_id": RUN_ID}
            )
            if results.shape[0] > 0:
                print(f"\t{results.shape[0]} error rows returned")
                print(textwrap.indent(results.to_string(index=False), "\t"))
            else:
                print("\tNo error rows returned")
        print()

# For the ASE script, there's not really a solid threshold for errors, so instead we
# get all the rows and do some Python processing to pick out Geography/ASE combinations
# which may be flagged
with ESTIMATES_ENGINE.connect() as con:
    print("Check large changes in ASE pop")

    # First, get the start/end year for this run_id
    start_year = con.execute(
        sql.text(f"SELECT [start_year] FROM [metadata].[run] WHERE [run_id] = {RUN_ID}")
    ).scalar()
    end_year = con.execute(
        sql.text(f"SELECT [end_year] FROM [metadata].[run] WHERE [run_id] = {RUN_ID}")
    ).scalar()
    years = ", ".join([f"[{year}]" for year in range(start_year, end_year + 1)])

    # Stop this check if there is only on year of data available
    if start_year == end_year:
        print("\tCannot run check, only one year of data available")
    else:

        # Then, pull the data. Because a certain someone hates dynamic SQL, we cannot
        # pivot out the years in SQL and instead have to do it in Python
        with open("check_ase_at_jurisdiction.sql") as file:
            results = (
                pd.read_sql_query(
                    sql=sql.text(file.read()),
                    con=con,
                    params={
                        "run_id": RUN_ID,
                        "pop_type": "Total",
                    },
                )
                .pivot_table(
                    columns="year",
                    index=["jurisdiction", "metric"],
                    values="value",
                    aggfunc="sum",
                )
                .reset_index(drop=False)
            )

        # For every pair of consecutive years, compute if there was a significant
        # change. Note that to avoid log(0) or divide by zero errors, we replace all
        # zeros with tiny values
        results_no_zero = results.copy(deep=True).replace(0, 0.0001)
        flagged_rows = np.full(results.shape[0], False)
        for year in range(start_year, end_year):
            abs_diff = (
                (results_no_zero[year + 1] - results_no_zero[year])
                .abs()
                .replace(0, 0.0001)
            )
            scaled_pct = 100 * np.log(abs_diff) / results_no_zero[year]
            measure = np.exp(5.9317 * (np.log(abs_diff) ** -0.596))
            flagged_rows = flagged_rows | (measure < scaled_pct)

        # Print different error messages based on the number of flagged rows
        if flagged_rows.sum() > 0:
            print(f"\t{flagged_rows.sum()} warning rows returned")
            print(textwrap.indent(results[flagged_rows].to_string(index=False), "\t"))
        else:
            print("\tNo error rows returned")
    print()
