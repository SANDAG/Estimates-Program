import pathlib
import sqlalchemy as sql
import yaml
import python.parsers as parsers

#########
# PATHS #
#########

# Store project root folder
ROOT_FOLDER = pathlib.Path(__file__).parent.resolve().parent
SQL_FOLDER = ROOT_FOLDER / "sql"


#####################
# SQL CONFIGURATION #
#####################

# Load secrets YAML file
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

GIS_ENGINE = sql.create_engine(
    "mssql+pyodbc://@"
    + _secrets["sql"]["gis"]["server"]
    + "/"
    + _secrets["sql"]["gis"]["database"]
    + "?trusted_connection=yes&driver="
    + "ODBC Driver 17 for SQL Server",
    fast_executemany=True,
)

#########################
# RUNTIME CONFIGURATION #
#########################

# Load configuration YAML file
try:
    with open(ROOT_FOLDER / "config.yml", "r") as file:
        config = yaml.safe_load(file)
except IOError:
    raise IOError("config.yml does not exist, see README.md")

# Initialize input parser
# Parse the configuration YAML file and validate its contents
input_parser = parsers.InputParser(config=config, engine=ESTIMATES_ENGINE)
input_parser.parse_config()

RUN_INSTRUCTIONS = input_parser.run_instructions
RUN_ID = input_parser.run_id
MGRA_VERSION = input_parser.mgra_version
