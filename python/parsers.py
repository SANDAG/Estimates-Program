import cerberus
import sqlalchemy as sql


class InputParser:
    """A class to parse and validate input configurations.

    Note that in addition to validating the configuration dictionary, this class also
    creates the run id and inserts it into the database if standard run mode is enabled.

    Attributes:
        _yaml_config (dict): The configuration dictionary to be parsed.
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
        self._yaml_config = config
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
        self._parse_run_id()
        self.mgra_version = self._parse_mgra_version()

        # Depending on what run mode we are using, our run instructions are slightly
        # different
        if self._yaml_config["run"]["enabled"]:
            self.run_instructions["years"] = list(
                range(
                    self._yaml_config["run"]["start_year"],
                    self._yaml_config["run"]["end_year"] + 1,
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
        elif self._yaml_config["debug"]["enabled"]:
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
                self.run_instructions[key] = self._yaml_config["debug"][key]

    def _check_run_id(self, run_id: int) -> None:
        """Check if supplied run id exists in the database."""
        with self._engine.connect() as conn:
            # Ensure supplied run id exists in the database
            query = sql.text(
                """
                    SELECT CASE WHEN EXISTS (
                        SELECT [run_id] FROM [metadata].[run] WHERE run_id = :run_id
                    ) THEN 1 ELSE 0 END
                """
            )

            exists = conn.execute(query, {"run_id": run_id}).scalar()
            if exists == 0:
                raise ValueError("run_id does not exist in the database")

    def _validate_config(self) -> None:
        """Validate the contents of the configuration dictionary

        Raises:
            ValueError: If any of the configuration values are invalid.
        """
        # Check we are running in either standard or debug mode
        if (
            self._yaml_config["run"]["enabled"]
            and self._yaml_config["debug"]["enabled"]
        ):
            raise ValueError("Cannot run in both 'debug' and 'run' mode")
        if (
            not self._yaml_config["run"]["enabled"]
            and not self._yaml_config["debug"]["enabled"]
        ):
            raise ValueError("Must run in one of 'debug' and 'run' mode")

        # Check all keys are present and types using Cerberus. For help, see their
        # website here: https://docs.python-cerberus.org/usage.html
        schema = {
            "run": {
                "type": "dict",
                "schema": {
                    "enabled": {"type": "boolean"},
                    "mgra": {"type": "string", "allowed": ["mgra15"]},
                    "start_year": {"type": "integer", "min": 2010},
                    "end_year": {"type": "integer", "max": 2024},
                    "version": {"type": "string"},
                    "comments": {"type": "string", "nullable": True},
                },
            },
            "debug": {
                "type": "dict",
                "schema": {
                    "enabled": {"type": "boolean"},
                    "run_id": {"type": "integer", "nullable": True},
                    "start_year": {"type": "integer", "min": 2010, "nullable": True},
                    "end_year": {"type": "integer", "max": 2024, "nullable": True},
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
        if not validator.validate(self._yaml_config):
            raise ValueError(validator.errors)

        # Check for contradictions in arguments

        # Check the end year is after or equal to the start year. If the years are
        # equal, then only that year will be run
        if (
            self._yaml_config["run"]["start_year"]
            > self._yaml_config["run"]["end_year"]
        ):
            raise ValueError(
                "Key 'start year' cannot be greater than key 'end year' in 'run' settings"
            )

        # Check that in debug mode, if the 'run_id' is provided, that we do not also
        # provide 'start_year' or 'end_year'
        if (
            self._yaml_config["debug"]["enabled"]
            and self._yaml_config["debug"]["run_id"] is not None
        ):
            if (
                self._yaml_config["debug"]["start_year"] is not None
                or self._yaml_config["debug"]["end_year"] is not None
            ):
                raise ValueError(
                    "If a debug 'run_id' is provided, then the debug keys of "
                    "'start_year' and 'end_year' must be null"
                )

        # Check that in debug mode, if no 'run_id' is provided, that either:
        # 1. Both 'start_year' and 'end_year' are null, so we will use 'run' values or
        # 2. Both 'start_year' and 'end_year' are provided
        if (
            self._yaml_config["debug"]["enabled"]
            and self._yaml_config["debug"]["run_id"] is None
        ):
            if not (
                (
                    self._yaml_config["debug"]["start_year"] is None
                    and self._yaml_config["debug"]["end_year"] is None
                )
                or (
                    self._yaml_config["debug"]["start_year"] is not None
                    and self._yaml_config["debug"]["end_year"] is not None
                )
            ):
                raise ValueError(
                    "If a debug 'run_id' is not provided, then the debug keys of "
                    "'start_year' and 'end_year' must either both be null or both be "
                    "integers"
                )

        # If we are running in debug mode with a new run_id, then ensure that the
        # dependency chain of modules is correct. If we are in debug mode with an
        # already existing run_id, then it is assumed that the dependency chain
        # is already present
        if (
            self._yaml_config["debug"]["enabled"]
            and self._yaml_config["debug"]["run_id"] is None
        ):
            if self._yaml_config["debug"]["staging"]:
                for key in [
                    "startup",
                    "housing_and_households",
                    "population",
                    "population_by_ase",
                    "household_characteristics",
                ]:
                    if not self._yaml_config["debug"][key]:
                        raise ValueError(
                            f"Because debug key 'staging' is enabled, debug key "
                            f"'{key}' must also be enabled"
                        )
            if self._yaml_config["debug"]["household_characteristics"]:
                for key in [
                    "startup",
                    "housing_and_households",
                    "population",
                    "population_by_ase",
                ]:
                    if not self._yaml_config["debug"][key]:
                        raise ValueError(
                            f"Because debug key 'household_characteristics' is "
                            f"enabled, debug key '{key}' must also be enabled"
                        )
            if self._yaml_config["debug"]["population_by_ase"]:
                for key in ["startup", "housing_and_households", "population"]:
                    if not self._yaml_config["debug"][key]:
                        raise ValueError(
                            f"Because debug key 'population_by_ase' is enabled, "
                            f"debug key '{key}' must also be enabled"
                        )
            if self._yaml_config["debug"]["population"]:
                for key in ["startup", "housing_and_households"]:
                    if not self._yaml_config["debug"][key]:
                        raise ValueError(
                            f"Because debug key 'population' is enabled, debug key "
                            f"'{key}' must also be enabled"
                        )
            if self._yaml_config["debug"]["housing_and_households"]:
                if not self._yaml_config["debug"]["startup"]:
                    raise ValueError(
                        "Because debug key 'housing_and_households' is enabled, "
                        "debug key 'startup' must also be enabled"
                    )

    def _parse_run_id(self) -> None:
        """Parse the run id from the configuration file.

        This function will create a new run id if standard run mode is enabled.
        The new run id is generated as the maximum run id in the database plus one.
        If debug mode is enabled, the supplied run id is validated against the
        database and returned.

        Raises:
            ValueError: If any of the configuration values are invalid.
        """
        # Create a new run id if standard run mode is enabled, or if we are running a
        # subset of Estimates via debug mode
        if self._yaml_config["run"]["enabled"] or (
            self._yaml_config["debug"]["enabled"]
            and self._yaml_config["debug"]["run_id"] is None
        ):
            with self._engine.connect() as conn:

                # Override default arguments if debug mode is enabled
                if self._yaml_config["debug"]["enabled"]:
                    comments = (
                        self._yaml_config["run"]["comments"]
                        if self._yaml_config["debug"]["comments"] is None
                        else self._yaml_config["debug"]["comments"]
                    )
                    self._start_year = (
                        self._yaml_config["run"]["start_year"]
                        if self._yaml_config["debug"]["start_year"] is None
                        else self._yaml_config["debug"]["start_year"]
                    )
                    self._end_year = (
                        self._yaml_config["run"]["end_year"]
                        if self._yaml_config["debug"]["end_year"] is None
                        else self._yaml_config["debug"]["end_year"]
                    )
                else:
                    comments = self._yaml_config["run"]["comments"]
                    self._start_year = self._yaml_config["run"]["start_year"]
                    self._end_year = self._yaml_config["run"]["end_year"]

                # Create run id from the most recent run id in the database
                run_id = conn.execute(
                    sql.text("SELECT ISNULL(MAX(run_id),0)+1 FROM [metadata].[run]")
                ).scalar()

                # Insert new run id into the database
                conn.execute(
                    sql.text(
                        """
                            INSERT INTO [metadata].[run] (
                                [run_id], [mgra], [start_year], [end_year],
                                [user], [date], [version], [comments], [loaded]
                            ) VALUES (
                                :run_id, :mgra, :start_year, :end_year, USER_NAME(),
                                GETDATE(), :version, :comments, 0
                            )
                        """
                    ),
                    {
                        "run_id": run_id,
                        "mgra": self._yaml_config["run"]["mgra"],
                        "start_year": self._start_year,
                        "end_year": self._end_year,
                        "version": self._yaml_config["run"]["version"],
                        "comments": comments,
                    },
                )

                # Commit the transaction
                conn.commit()

                # Store the run id in the class instance and return
                self.run_id = run_id

        # Use the supplied run id if debug mode is enabled
        if (
            self._yaml_config["debug"]["enabled"]
            and self._yaml_config["debug"]["run_id"] is not None
        ):
            # Ensure supplied run id exists in the database
            self._check_run_id(self._yaml_config["debug"]["run_id"])

            # Since the run_id exists, get the start and end year from the run metadata
            with self._engine.connect() as conn:
                self._start_year = conn.execute(
                    sql.text(
                        "SELECT [start_year] "
                        "FROM [metadata].[run] "
                        "WHERE run_id = :run_id"
                    ),
                    {"run_id": self._yaml_config["debug"]["run_id"]},
                ).scalar()
                self._end_year = conn.execute(
                    sql.text(
                        "SELECT [end_year] "
                        "FROM [metadata].[run] "
                        "WHERE run_id = :run_id"
                    ),
                    {"run_id": self._yaml_config["debug"]["run_id"]},
                ).scalar()

            # Store the run id in the class instance and return
            self.run_id = self._yaml_config["debug"]["run_id"]

    def _parse_mgra_version(self) -> str:
        """Parse the MGRA version from the configuration file."""
        # Use the supplied mgra version if standard run mode is enabled
        if self._yaml_config["run"]["enabled"]:
            return self._yaml_config["run"]["mgra"]

        # Get mgra version from database if debug mode is enabled
        elif self._yaml_config["debug"]["enabled"]:
            # Ensure run id exists in the database
            self._check_run_id(run_id=self.run_id)

            with self._engine.connect() as conn:
                query = sql.text(
                    "SELECT [mgra] FROM [metadata].[run] WHERE run_id = :run_id"
                )
                return conn.execute(query, {"run_id": self.run_id}).scalar()
