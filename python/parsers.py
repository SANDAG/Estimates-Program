import cerberus
import sqlalchemy as sql

_MODULES = [
    "startup",
    "housing_and_households",
    "population",
    "population_by_ase",
    "household_characteristics",
    "employment",
    "staging",
]


class InputParser:
    """A class to parse and validate input configurations.

    The final result of creating a class instance and running the 'parse_config()'
    function is:
    * (Class variable 'run_instructions') Explicit instructions on which modules to run
        on which years
    * (Class variable 'run_id') The value of 'run_id' to use
    * (Class variable 'mgra_version') The MGRA version to run on

    Attributes:
        _config (dict): The configuration dictionary to be parsed.
        _engine (sql.Engine): The SQL engine which corresponds to the Estimates database
        _start_year (int): Used to store the start_year, whether of a new run or an
            existing run
        _end_year (int): Used to store the end_year, whether of a new run or an
            existing run
        run_instructions (dict): Explicit instructions on which modules/years to run.
            The toml config file is parsed and this dictionary is filled no matter if
            run or debug mode is enabled
        run_id (int): The run identifier parsed from the configuration.
        mgra_version (int): The MGRA version we are running on. Depending on run mode,
            either pulled from the config file or pulled from the run metadata table

    Methods:
        parse_config(): Control function
        _check_run_id(): Checks if a run id exists in the database.
        _validate_config(): Validate the configuration file
        _parse_run_id(): Parses the run identifier from the configuration.
        _parse_mgra_version(): Parses the MGRA version from the run identifier.
    """

    def __init__(self, config: dict, engine: sql.Engine) -> None:
        """Initialize the InputParser with a configuration dictionary."""
        self._config = config
        self._engine = engine
        self._start_year = None
        self._end_year = None
        self.run_instructions = {}
        self.run_id = None
        self.mgra_version = None
        self.debug = False

    def parse_config(self) -> None:
        """Control flow to parse the runtime configuration

        First, the contents of the config file are validated. Then the run_id
        is validated, with the end result of either creating a new run_id or
        re-using a run_id for debugging purposes. Finally, the MGRA version is
        either pulled from the config file or from database

        Each of these tasks is contained in their own sub-function, see them
        for additional details

        Returns:
            None
        """
        self._validate_config()
        self.run_id = self._parse_run_id()
        self.mgra_version = self._parse_mgra_version()

        # Depending on what run mode we are using, our run instructions are slightly
        # different
        if self._config["run"]["enabled"]:
            self.run_instructions["years"] = list(
                range(
                    self._config["run"]["start_year"],
                    self._config["run"]["end_year"] + 1,
                )
            )
            for key in _MODULES:
                self.run_instructions[key] = True
        elif self._config["debug"]["enabled"]:
            self.debug = True
            self.run_instructions["years"] = [self._start_year]
            for key in _MODULES:
                self.run_instructions[key] = key == self._config["debug"]["module"]

    def _check_run_id(self, run_id: int) -> None:
        """Check if supplied run id exists in the database and is complete"""
        with self._engine.connect() as con:
            # Ensure supplied run id exists in the database
            query = sql.text(
                """
                    SELECT CASE WHEN EXISTS (
                        SELECT [run_id] 
                        FROM [metadata].[run] 
                        WHERE [run_id] = :run_id
                            AND [complete] = 1
                    ) THEN 1 ELSE 0 END
                """
            )

            exists = con.execute(query, {"run_id": run_id}).scalar()
            if exists == 0:
                raise ValueError(
                    f"Either the [run_id]={run_id} does not exist in the database or "
                    f"it is not marked as [complete]=1"
                )

    def _validate_config(self) -> None:
        """Validate the contents of the configuration dictionary

        Raises:
            ValueError: If any of the configuration values are invalid.
        """
        # Check we are running in either standard or debug mode
        if self._config["run"]["enabled"] and self._config["debug"]["enabled"]:
            raise ValueError("Cannot run in both 'debug' and 'run' mode")
        if not self._config["run"]["enabled"] and not self._config["debug"]["enabled"]:
            raise ValueError("Must run in one of 'debug' and 'run' mode")

        # Check all keys are present and key types using Cerberus. For help, see their
        # website here: https://docs.python-cerberus.org/usage.html
        min_max_years = [2010, 2024]
        versions = ["0.0.0-dev", "1.0.0", "1.1.0", "1.1.1-dev"]
        schema = {
            "run": {
                "type": "dict",
                "schema": {
                    "enabled": {"type": "boolean"},
                    "mgra": {"type": "string", "allowed": ["mgra15"]},
                    "start_year": {"type": "integer", "min": min_max_years[0]},
                    "end_year": {"type": "integer", "max": min_max_years[1]},
                    "version": {"type": "string", "allowed": versions},
                    "comments": {"type": "string"},
                },
            },
            "debug": {
                "type": "dict",
                "schema": {
                    "enabled": {"type": "boolean"},
                    "run_id": {"type": "integer"},
                    "year": {
                        "type": "integer",
                        "min": min_max_years[0],
                        "max": min_max_years[1],
                    },
                    "module": {
                        "type": "string",
                        "allowed": _MODULES + [""],
                    },
                },
            },
        }
        validator = cerberus.Validator(schema, require_all=True)
        if not validator.validate(self._config):
            raise ValueError(validator.errors)

        # Make sure our years are not travelling backwards in time
        if self._config["run"]["enabled"] and (
            self._config["run"]["start_year"] > self._config["run"]["end_year"]
        ):
            raise ValueError(
                f"Key 'start year' cannot be greater than key 'end year' in 'run' settings"
            )

        # Check that if we are in debug mode...
        if self._config["debug"]["enabled"]:
            # That the provided 'run_id' is valid
            self._check_run_id(self._config["debug"]["run_id"])

            # That a valid module was provided
            if self._config["debug"]["module"] not in _MODULES:
                raise ValueError(
                    f"Debug key 'module' must be one of {', '.join(_MODULES)}. "
                    f"Instead, \"{self._config['debug']['module']}\" was provided."
                )

            # That the 'year' value conforms with the [start_year] and [end_year]
            # already in [metadata].[run]
            with self._engine.connect() as con:
                check_year = con.execute(
                    sql.text(
                        """
                        SELECT
                            CASE
                                WHEN :year BETWEEN [start_year] AND [end_year] THEN 1
                                ELSE 0
                            END
                        FROM [metadata].[run]
                            WHERE [run_id] = :run_id
                        """
                    ),
                    {
                        "run_id": self._config["debug"]["run_id"],
                        "year": self._config["debug"]["year"],
                    },
                ).scalar()
            if check_year == 0:
                raise ValueError(
                    f"The provided debug 'year' of {self._config['debug']['year']} "
                    f"is not within the range of [metadata].[run] 'start_year' and "
                    f"'end_year' for 'run_id' {self._config['debug']['run_id']}"
                )
            else:
                self._start_year = self._config["debug"]["year"]
                self._end_year = self._config["debug"]["year"]

    def _parse_run_id(self) -> int:
        """Parse the run id from the configuration file.

        This function will create a new run id if standard run mode is enabled.
        The new run id is generated as the maximum run id in the database plus one.
        If debug mode is enabled, the supplied run id is validated against the
        database and returned.

        Returns:
            The 'run_id' value to use for this run

        Raises:
            ValueError: If any of the configuration values are invalid.
        """
        # Create a new run id if standard run mode is enabled
        if self._config["run"]["enabled"]:
            with self._engine.connect() as con:

                self._start_year = self._config["run"]["start_year"]
                self._end_year = self._config["run"]["end_year"]

                # Create run id from the most recent run id in the database
                run_id = con.execute(
                    sql.text("SELECT ISNULL(MAX(run_id),0)+1 FROM [metadata].[run]")
                ).scalar()

                # Insert new run id into the database
                con.execute(
                    sql.text(
                        """
                            INSERT INTO [metadata].[run] (
                                [run_id], 
                                [mgra], 
                                [start_year], 
                                [end_year],
                                [user], 
                                [start_date],
                                [end_date],
                                [version], 
                                [comments], 
                                [complete]
                            ) VALUES (
                                :run_id, 
                                :mgra, 
                                :start_year, 
                                :end_year, 
                                USER_NAME(),
                                GETDATE(), 
                                NULL,
                                :version, 
                                :comments, 
                                0
                            )
                        """
                    ),
                    {
                        "run_id": run_id,
                        "mgra": self._config["run"]["mgra"],
                        "start_year": self._start_year,
                        "end_year": self._end_year,
                        "version": self._config["run"]["version"],
                        "comments": self._config["run"]["comments"],
                    },
                )

                # Commit the transaction
                con.commit()

        # For debug mode, simply return the pre-selected [run_id]
        else:
            run_id = self._config["debug"]["run_id"]

        # Return the [run_id] this Estimates Program run is using
        return run_id

    def _parse_mgra_version(self) -> str:
        """Parse the MGRA version from the configuration file."""
        # Use the supplied mgra version if standard run mode is enabled
        if self._config["run"]["enabled"]:
            return self._config["run"]["mgra"]

        # Get mgra version from database if debug mode is enabled
        elif self._config["debug"]["enabled"]:
            # Ensure run id exists in the database
            self._check_run_id(run_id=self.run_id)

            with self._engine.connect() as con:
                query = sql.text(
                    "SELECT [mgra] FROM [metadata].[run] WHERE run_id = :run_id"
                )
                return con.execute(query, {"run_id": self.run_id}).scalar()
