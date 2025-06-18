import cerberus
import sqlalchemy as sql


class InputParser:
    """A class to parse and validate input configurations.

    The final result of creating a class instance and running the 'parse_config()'
    function is:
    * (Class variable 'run_instructions') Explicit instructions on which modules to run
        on which years
    * (Class variable 'run_id') The value of 'run_id' to use. If standard run mode is
        enabled or if no 'run_id' was provided in 'debug' mode, then a new 'run_id' was
        created and inserted into '[run].[metadata]'
    * (Class variable 'mgra_version') The MGRA version to run on

    Attributes:
        _config (dict): The configuration dictionary to be parsed.
        _engine (sql.Engine): The SQL engine which corresponds to the Estimates database
        _start_year (int): Used to store the start_year, whether of a new run or an
            existing run
        _end_year (int): Used to store the end_year, whether of a new run or an
            existing run
        run_instructions (dict): Explicit instructions on which modules/years to run.
            The YAML config file is parsed and this dictionary is filled no matter if
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
            for key in [
                "startup",
                "housing_and_households",
                "population",
                "population_by_ase",
                "household_characteristics",
                "staging",
            ]:
                self.run_instructions[key] = True
        elif self._config["debug"]["enabled"]:
            self.run_instructions["years"] = list(
                range(
                    self._start_year,
                    self._end_year + 1,
                )
            )
            for key in [
                "startup",
                "housing_and_households",
                "population",
                "population_by_ase",
                "household_characteristics",
                "staging",
            ]:
                self.run_instructions[key] = self._config["debug"][key]

    def _check_run_id(self, run_id: int) -> None:
        """Check if supplied run id exists in the database."""
        with self._engine.connect() as con:
            # Ensure supplied run id exists in the database
            query = sql.text(
                """
                    SELECT CASE WHEN EXISTS (
                        SELECT [run_id] FROM [metadata].[run] WHERE run_id = :run_id
                    ) THEN 1 ELSE 0 END
                """
            )

            exists = con.execute(query, {"run_id": run_id}).scalar()
            if exists == 0:
                raise ValueError("run_id does not exist in the database")

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
        versions = ["0.0.0-dev", "1.0.0"]
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
                    "run_id": {"type": "integer", "nullable": True},
                    "start_year": {"type": "integer", "min": min_max_years[0]},
                    "end_year": {"type": "integer", "max": min_max_years[1]},
                    "version": {
                        "type": "string",
                        "allowed": versions,
                        "nullable": True,
                    },
                    "comments": {"type": "string", "nullable": True},
                    "startup": {"type": "boolean"},
                    "housing_and_households": {"type": "boolean"},
                    "population": {"type": "boolean"},
                    "population_by_ase": {"type": "boolean"},
                    "household_characteristics": {"type": "boolean"},
                    "staging": {"type": "boolean"},
                },
            },
        }
        validator = cerberus.Validator(schema, require_all=True)
        if not validator.validate(self._config):
            raise ValueError(validator.errors)

        # Make sure our years are not travelling backwards in time
        for run_type in ["run", "debug"]:
            if self._config[run_type]["enabled"] and (
                self._config[run_type]["start_year"]
                > self._config[run_type]["end_year"]
            ):
                raise ValueError(
                    f"Key 'start year' cannot be greater than key 'end year' in '{run_type}' settings"
                )

        # Check that if we are in debug mode and trying to re-use a 'run_id'...
        if (
            self._config["debug"]["enabled"]
            and self._config["debug"]["run_id"] is not None
        ):
            # That the provided 'run_id' is valid
            self._check_run_id(self._config["debug"]["run_id"])

            # That 'version', and 'comments' are null
            for key in ["version", "comments"]:
                if self._config["debug"][key] is not None:
                    raise ValueError(
                        f"If a debug 'run_id' is provided, then the debug key of "
                        f"'{key}' must be null"
                    )

            # That the 'start_year' and 'end_year' values, conform with those already
            # in [metadata].[run]
            with self._engine.connect() as con:
                existing_start_year = con.execute(
                    sql.text(
                        "SELECT [start_year] FROM [metadata].[run] WHERE run_id = :run_id"
                    ),
                    {"run_id": self._config["debug"]["run_id"]},
                ).scalar()
            if self._config["debug"]["start_year"] < existing_start_year:
                raise ValueError(
                    f"The provided debug 'start_year' of {self._config['debug']['start_year']} "
                    f"is less than the [metadata].[run] 'start_year' of "
                    f"{existing_start_year} for 'run_id' {self._config["debug"]["run_id"]}"
                )
            else:
                self._start_year = self._config["debug"]["start_year"]

            with self._engine.connect() as con:
                existing_end_year = con.execute(
                    sql.text(
                        "SELECT [end_year] FROM [metadata].[run] WHERE run_id = :run_id"
                    ),
                    {"run_id": self._config["debug"]["run_id"]},
                ).scalar()
            if self._config["debug"]["end_year"] > existing_end_year:
                raise ValueError(
                    f"The provided debug 'end_year' of {self._config['debug']['end_year']} "
                    f"is greater than the [metadata].[run] 'end_year' of "
                    f"{existing_end_year} for 'run_id' {self._config["debug"]["run_id"]}"
                )
            else:
                self._end_year = self._config["debug"]["end_year"]

        # Check that in debug mode, if no 'run_id' is provided...
        if self._config["debug"]["enabled"] and self._config["debug"]["run_id"] is None:
            # That all of 'start_year', 'end_year', and 'version' are provided. Note
            # that 'comments' can still be null
            for key in ["start_year", "end_year", "version"]:
                if self._config["debug"][key] is None:
                    raise ValueError(
                        f"If a debug 'run_id' is not provided, then the debug key of "
                        f"'{key}' must be provided"
                    )

            # That the dependency chain of modules is correct
            if self._config["debug"]["staging"]:
                for key in [
                    "startup",
                    "housing_and_households",
                    "population",
                    "population_by_ase",
                    "household_characteristics",
                ]:
                    if not self._config["debug"][key]:
                        raise ValueError(
                            f"Because debug key 'staging' is enabled, debug key "
                            f"'{key}' must also be enabled"
                        )
            if self._config["debug"]["household_characteristics"]:
                for key in [
                    "startup",
                    "housing_and_households",
                    "population",
                    "population_by_ase",
                ]:
                    if not self._config["debug"][key]:
                        raise ValueError(
                            f"Because debug key 'household_characteristics' is "
                            f"enabled, debug key '{key}' must also be enabled"
                        )
            if self._config["debug"]["population_by_ase"]:
                for key in ["startup", "housing_and_households", "population"]:
                    if not self._config["debug"][key]:
                        raise ValueError(
                            f"Because debug key 'population_by_ase' is enabled, "
                            f"debug key '{key}' must also be enabled"
                        )
            if self._config["debug"]["population"]:
                for key in ["startup", "housing_and_households"]:
                    if not self._config["debug"][key]:
                        raise ValueError(
                            f"Because debug key 'population' is enabled, debug key "
                            f"'{key}' must also be enabled"
                        )
            if self._config["debug"]["housing_and_households"]:
                if not self._config["debug"]["startup"]:
                    raise ValueError(
                        "Because debug key 'housing_and_households' is enabled, "
                        "debug key 'startup' must also be enabled"
                    )

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
        # Create a new run id if standard run mode is enabled, or if we are running a
        # subset of Estimates via debug mode
        if self._config["run"]["enabled"] or (
            self._config["debug"]["enabled"] and self._config["debug"]["run_id"] is None
        ):
            with self._engine.connect() as con:

                # Override default arguments if debug mode is enabled
                if self._config["debug"]["enabled"]:
                    comments = self._config["debug"]["comments"]
                    self._start_year = self._config["debug"]["start_year"]
                    self._end_year = self._config["debug"]["end_year"]
                else:
                    comments = self._config["run"]["comments"]
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
                                [date], 
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
                        "comments": comments,
                    },
                )

                # Commit the transaction
                con.commit()

                # Return the valid 'run_id'
                return run_id

        # Use the supplied 'run_id' if debug mode is enabled. Note the existence of the
        # 'run_id' has already been checked
        if (
            self._config["debug"]["enabled"]
            and self._config["debug"]["run_id"] is not None
        ):
            return self._config["debug"]["run_id"]

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
