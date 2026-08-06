# Python script to automatically run various QA/QC code and report out the results.
# This is split into two sections, one which simply runs SQL scripts that return error
# rows, and the second which does year-over-year analysis of all variables to find
# geographies with "significant change". "Significant change" is pretty arbitrary, but
# some experimentation was done to justify the magic formulas and numbers in:
# https://github.com/SANDAG/Series-15-Urban-Development-Model/blob/main/Other/Significant%20Change.xlsx

# We cannot import python.utils, as just importing will cause a new [run_id]` value and
# new log file to be created. Instead, copy what we need for now :(
import tomllib
import pathlib
import textwrap
import sqlalchemy as sql
import pandas as pd
import numpy as np

#################
# CONFIGURATION #
#################

# The run_id where all data will be pulled from
RUN_ID = 231

# For YOY analysis, we require data to be grouped at some geography for analysis. The
# geography below can be configured to any column of [dim].[vi_mgra_denormalize].
# Be aware that smaller geographies are more likely to include spurious results, but
# larger geographies may hide some large changes
geography = "jurisdiction"

############
# SETTINGS #
############

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

# Some helpful parameters directly derived from run_id
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
# if there is an error. Naturally, that means if there is no error from the check, then
# the SQL script should return zero rows of data
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

# For YOY analysis, we need to coerce different structured tables all into the same
# format. The following SQL scripts are used to pull data grouped at the configured
# geography with the exact columns of [year], [{geography}], [metric], and [value]
yoy_config = {
    "housing units by type": "check_yoy_hs_by_type.sql",
    "households by type": "check_yoy_hh_by_type.sql",
    "population by type": "check_yoy_pop_by_type.sql",
    "population by ASE": "check_yoy_pop_by_ase.sql",
    "jobs by ownership/industry": "check_yoy_jobs_by_sector.sql",
}

##################
# REPORTING CODE #
##################

# Run each SQL script. If the script returns rows, report out a custom error message
# with every invalid row. If the script doesn't return anything, then there are no
# errors
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


# Run the YOY threshold analysis
for variable, path in yoy_config.items():
    print(f"Check large changes in {variable} at the {geography} level")

    # Stop this check if there is only one year of data available
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
            (results_no_zero[year + 1] - results_no_zero[year]).abs()
            # The replace() is to prevent the same log(0) or divide by zero error
            # when the geography/metric has no change over the time period
            .replace(0, 0.0001)
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
