# Python script to automatically run QA/QC scripts and report out the results.
# Additionally, for ASE data, it flags rows which had a significant change, see
# the below Excel sheet for additional details:
# https://github.com/SANDAG/Series-15-Urban-Development-Model/blob/main/Other/Significant%20Change.xlsx

# Main configuration, what run_id to operate on
RUN_ID = 231

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
    + "?driver=ODBC Driver 18 for SQL Server"
    + "&TrustServerCertificate=yes",
    fast_executemany=True,
)

# Some helpful parameters
with ESTIMATES_ENGINE.connect() as con:
    start_year = con.execute(
        sql.text("SELECT [start_year] FROM [metadata].[run] WHERE [run_id] = :run_id"),
        {"run_id": RUN_ID},
    ).scalar()

    end_year = con.execute(
        sql.text("SELECT [end_year] FROM [metadata].[run] WHERE [run_id] = :run_id"),
        {"run_id": RUN_ID},
    ).scalar()

    series = con.execute(
        sql.text("SELECT [series] FROM [metadata].[run] WHERE [run_id] = :run_id"),
        {"run_id": RUN_ID},
    ).scalar()

# Store a list of the scripts to run. It is assumed that each script only takes in
# a parameter for [run_id]. It is also assumed that rows of data will only be returned
# if there is an error, in which case it will be printed out
qa_qc_scripts = {
    "Check jurisdiction control totals": "check_controls_jurisdiction.sql",
    "Check region ASE controls": "check_controls_region_ase.sql",
    "Check region job control totals": "check_controls_region_jobs.sql",
    "Check cross-table pop by type": "check_cross_table_pop_by_type.sql",
    "Check cross-table total hh": "check_cross_table_total_hh.sql",
    "Check MGRA restrictions": "check_mgra_restrictions.sql",
    "Check every HH has HS": "check_every_hh_has_hs.sql",
    "Check every HHP has HH": "check_every_hhp_has_hh.sql",
    "Check implied HHP vs actual HHP": "check_implied_hhp_vs_actual_hhp.sql",
    "Check householders vs households": "check_householders_vs_households.sql",
    "Check implied workers vs persons 18+": "check_implied_workers.sql",
    "Check households by workers vs households by size": "check_hhworkers_hhsize.sql",
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

# For all variables, we can also do some simple year over year analysis and flag
# where there are large changes. Note, the geography below can be configured to any
# column of [dim].[vi_mgra_denormalize]. Smaller geographies are more likely to include
# spurious results, but larger geographies may hide some large changes
geography = "jurisdiction"

# Pulling all the data for each variable is not so simple, so we need to have this
# configuration. Each SQL script should return a table with columns [year],
# [jurisdiction], [metric], and [value]
variable_config = {
    "housing units by type": "check_yoy_hs_by_type.sql",
    "households by type": "check_yoy_hh_by_type.sql",
    "population by type": "check_yoy_pop_by_type.sql",
    "population by ASE": "check_yoy_pop_by_ase.sql",
    "jobs by ownership/industry": "check_yoy_jobs_by_sector.sql",
}

# Do the large change threshold analysis
for variable, path in variable_config.items():
    print(f"Check large changes in {variable} at the {geography} level")

    # Stop this check if there is only on year of data available
    if start_year == end_year:
        print("\tCannot run check, only one year of data available")

    # Pull the data then pivot out the year
    with ESTIMATES_ENGINE.connect() as con:
        with open(path) as file:
            data = (
                pd.read_sql_query(
                    sql=sql.text(file.read()),
                    con=con,
                    params={"run_id": RUN_ID, "series": series, "geography": geography},
                )
                .pivot_table(
                    columns="year",
                    index=[geography, "metric"],
                    values="value",
                    aggfunc="sum",
                )
                .reset_index(drop=False)
            )

    # For every pair of consecutive years, compute if there was a significant
    # change. Note that to avoid log(0) or divide by zero errors, we replace all
    # zeros with tiny values
    results_no_zero = data.copy(deep=True).replace(0, 0.0001)
    flagged_rows = np.full(data.shape[0], False)
    for year in range(start_year, end_year):
        abs_diff = (
            (results_no_zero[year + 1] - results_no_zero[year]).abs().replace(0, 0.0001)
        )
        scaled_pct = 100 * np.log(abs_diff) / results_no_zero[year]
        measure = np.exp(5.9317 * (np.log(abs_diff) ** -0.596))
        flagged_rows = flagged_rows | (measure < scaled_pct)

    # Print different error messages based on the number of flagged rows
    if flagged_rows.sum() > 0:
        print(f"\t{flagged_rows.sum()} warning rows returned")
        print(textwrap.indent(data[flagged_rows].to_string(index=False), "\t"))
    else:
        print("\tNo error rows returned")
    print()
