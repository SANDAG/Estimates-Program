# Python script to automatically run QA/QC scripts and report out the results.
# Additionally, for ASE data, it flags rows which had a significant change, see
# the below Excel sheet for additional details:
# https://github.com/SANDAG/Series-15-Urban-Development-Model/blob/main/Other/Significant%20Change.xlsx

# Main configuration, what run_id to operate on
RUN_ID = 189

# We cannot import python.utils, as just importing will cause a new [run_id]` value and
# new log file to be created. Instead, copy what we need for now :(
import yaml
import pathlib
import textwrap
import sqlalchemy as sql
import pandas as pd

ROOT_FOLDER = pathlib.Path(__file__).parent.resolve().parent
try:
    with open(ROOT_FOLDER / "secrets.yml", "r") as file:
        _secrets = yaml.safe_load(file)
except IOError:
    raise IOError("secrets.yml does not exist, see README.md")

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
    "Check control totals": "check_control_totals.sql",
    "Check cross-table consistency": "check_cross_table_consistency.sql",
    "Check MGRA restrictions": "check_mgra_restrictions.sql",
    "Check valid places to live": "check_valid_places_to_live.sql",
    "Check hh and pop consistency": "check_consistency_between_hh_and_pop.sql",
}

# Run each script, printing out status messages if necessary:
with ESTIMATES_ENGINE.connect() as con:
    for script_name, file_path in qa_qc_scripts.items():
        print(script_name)
        with open(file_path) as file:
            results = pd.read_sql_query(
                sql=sql.text(file.read()), con=con, params={"run_id": RUN_ID}
            )
            if results.shape[0] > 5:
                print(f"\t{results.shape[0]} error rows returned, printing TOP(5)")
                print(textwrap.indent(results.head(5).to_string(index=False), "\t"))
            elif results.shape[0] > 0:
                print(f"\t{results.shape[0]} error rows returned")
                print(textwrap.indent(results.to_string(index=False), "\t"))
            else:
                print("\tNo error rows returned")
        print()
