import pathlib
import sqlalchemy as sql
import yaml
from python.parsers import parse_config, parse_mgra_version, parse_run_id

#########
# PATHS #
#########

# Store project root folder
ROOT_FOLDER = pathlib.Path(__file__).parent.resolve().parent
SQL_FOLDER = ROOT_FOLDER / "sql"

##################
# CONFIGURATIONS #
##################

# Load secrets YAML file
try:
    with open(ROOT_FOLDER / "secrets.yml", "r") as file:
        _secrets = yaml.safe_load(file)
except IOError:
    raise IOError("secrets.yml does not exist, see README.md")

# Load configuration YAML file
try:
    with open(ROOT_FOLDER / "config.yml", "r") as file:
        _config = yaml.safe_load(file)
except IOError:
    raise IOError("config.yml does not exist, see README.md")

# Parse the configuration YAML file and validate its contents
parse_config(_config)


####################
# GLOBAL VARIABLES #
####################

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

GIS_ENGINE = sql.create_engine(
    "mssql+pyodbc://@"
    + _secrets["sql"]["gis"]["server"]
    + "/"
    + _secrets["sql"]["gis"]["database"]
    + "?trusted_connection=yes&driver="
    + "ODBC Driver 17 for SQL Server",
    fast_executemany=True,
)

RUN_ID = parse_run_id(_config)
MGRA_VERSION = parse_mgra_version(RUN_ID)
