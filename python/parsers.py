import sqlalchemy as sql
from click import command


class InputParser:
    """A class to parse and validate input configurations.

    Note that in addition to validating the configuration dictionary, this class also
    creates the run id and inserts it into the database if standard run mode is enabled.

    Attributes:
        _yaml_config (dict): The configuration dictionary to be parsed.
        _engine (sql.Engine): The SQL engine which corresponds to the Estimates database
        _debug_start_year (int): For a specific debug runtime config, used to store the
            start_year of the existing run
        _debug_end_year (int): For a specific debug runtime config, used to store the
            end_year of the existing run
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
        _check_if_list_of_ints(): Check if the input is a list of integers
        _parse_run_id(): Parses the run identifier from the configuration.
        _parse_mgra_version(): Parses the MGRA version from the run identifier.
    """

    def __init__(self, config: dict, engine: sql.Engine) -> None:
        """Initialize the InputParser with a configuration dictionary."""
        self._yaml_config = config
        self._engine = engine
        self._debug_start_year = None
        self._debug_end_year = None
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
        if self._yaml_config["run"]["enabled"]:
            self.run_instructions["years"] = list(
                range(
                    self._yaml_config["default"]["start_year"],
                    self._yaml_config["default"]["end_year"] + 1,
                )
            )
            for key in [
                "startup",
                "housing_and_households",
                "population",
                "population_by_ase",
                "population_by_ase",
                "staging",
            ]:
                self.run_instructions[key] = True
        elif self._yaml_config["debug"]["enabled"]:
            if self._yaml_config["debug"]["start_year"] is not None:
                self.run_instructions["years"] = list(
                    range(
                        self._yaml_config["debug"]["start_year"],
                        self._yaml_config["debug"]["end_year"] + 1,
                    )
                )
            else:
                self.run_instructions["years"] = list(
                    range(
                        self._yaml_config["default"]["start_year"],
                        self._yaml_config["default"]["end_year"] + 1,
                    )
                )
            for key in [
                "startup",
                "housing_and_households",
                "population",
                "population_by_ase",
                "population_by_ase",
                "staging",
            ]:
                self.run_instructions[key] = self._yaml_config["debug"][key]

    def _check_run_id(self, engine: sql.Engine, run_id: int) -> None:
        """Check if supplied run id exists in the database."""
        with engine.connect() as conn:
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
            raise ValueError("Cannot run in both debug and standard mode")
        if (
            not self._yaml_config["run"]["enabled"]
            and not self._yaml_config["debug"]["enabled"]
        ):
            raise ValueError("Must run in one of debug and standard mode")

        # Parse default arguments
        for key in ["mgra", "start_year", "end_year", "version"]:
            if key not in self._yaml_config["default"].keys():
                raise ValueError(f"Key '{key}' missing from default run settings")
        if self._yaml_config["default"]["mgra"] != "mgra15":
            raise ValueError("Only 'mgra15' supported")
        if not isinstance(self._yaml_config["default"]["start_year"], int):
            raise ValueError("Default key 'start year' must be an integer")
        if not isinstance(self._yaml_config["default"]["end_year"], int):
            raise ValueError("Default key 'end year' must be an integer")
        if (
            self._yaml_config["default"]["start_year"]
            > self._yaml_config["default"]["end_year"]
        ):
            raise ValueError(
                "Default key 'start year' cannot be greater than 'end year'"
            )

        # Parse arguments to run mode
        if self._yaml_config["run"]["comments"]:
            if not isinstance(self._yaml_config["run"]["comments"], str):
                print("Run key `comments' a string")

        # Parse arguments to debug mode
        if self._yaml_config["debug"]["enabled"]:

            # Check for None and typing
            if self._yaml_config["debug"]["comments"] is not None:
                if not isinstance(self._yaml_config["debug"]["comments"], str):
                    print("Debug key `comments` must be null or a string")
            for key in ["run_id", "start_year", "end_year"]:
                if self._yaml_config["debug"][key] is not None:
                    if not isinstance(self._yaml_config["debug"][key], int):
                        print(f"Debug key '{key}' must be null or an integer")
            for key in [
                "startup",
                "housing_and_households",
                "population",
                "population_by_ase",
                "household_characteristics",
                "staging",
            ]:
                if not isinstance(self._yaml_config["debug"][key], bool):
                    print(f"Debug key '{key}' must be True or False")

            # Check for contradictions in input arguments

            # If a run_id is provided, then we get the start_year and end_year from the
            # run metadata file, so they should be None
            if self._yaml_config["debug"]["run_id"] is not None:
                if (
                    self._yaml_config["debug"]["start_year"] is not None
                    or self._yaml_config["debug"]["end_year"] is not None
                ):
                    raise ValueError(
                        "If a debug 'run_id' is provided, then the debug keys of "
                        "'start_year' and 'end_year' must be null"
                    )
            # If no run_id is provided, then start_year and end_year must both be
            # provided
            else:
                if (
                    self._yaml_config["debug"]["start_year"] is None
                    or self._yaml_config["debug"]["end_year"] is None
                ):
                    raise ValueError(
                        "If a debug 'run_id' is not provided, then the debug keys of "
                        "'start_year' and 'end_year' must both be not null"
                    )

    def _parse_run_id(self) -> int:
        """Parse the run id from the configuration file.

        This function will create a new run id if standard run mode is enabled.
        The new run id is generated as the maximum run id in the database plus one.
        If debug mode is enabled, the supplied run id is validated against the
        database and returned.

        Args:
            engine (sql.Engine): The SQLAlchemy engine to connect to the database.

        Raises:
            ValueError: If any of the configuration values are invalid.
        """
        # Create a new run id if standard run mode is enabled, or if we are running a
        # subset of Estimates via debug mode
        if (
            self._yaml_config["run"]["enabled"]
            or self._yaml_config["debug"]["run_id"] is not None
        ):
            with self._engine.connect() as conn:

                # Override default arguments if debug mode is enabled
                if self._yaml_config["debug"]["enabled"]:
                    comments = (
                        f"Debug: {str(self._yaml_config['debug'])}"
                        if self._yaml_config["run"]["comments"] is None
                        else self._yaml_config["run"]["comments"]
                    )
                    start_year = (
                        self._yaml_config["default"]["start_year"]
                        if self._yaml_config["debug"]["start_year"] is None
                        else self._yaml_config["debug"]["start_year"]
                    )
                    end_year = (
                        self._yaml_config["default"]["end_year"]
                        if self._yaml_config["debug"]["end_year"] is None
                        else self._yaml_config["debug"]["end_year"]
                    )
                else:
                    comments = self._yaml_config["run"]["comments"]
                    start_year = self._yaml_config["default"]["start_year"]
                    end_year = self._yaml_config["default"]["end_year"]

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
                        "mgra": self._yaml_config["default"]["mgra"],
                        "start_year": start_year,
                        "end_year": end_year,
                        "version": self._yaml_config["default"]["version"],
                        "comments": comments,
                    },
                )

                # Commit the transaction
                conn.commit()

                # Store the run id in the class instance and return
                self.run_id = run_id
                return run_id

        # Use the supplied run id if debug mode is enabled
        elif self._yaml_config["debug"]["enabled"]:
            # Ensure supplied run id exists in the database
            self._check_run_id(
                engine=self._engine, run_id=self._yaml_config["debug"]["run_id"]
            )

            # Since the run_id exists, get the start and end year from the run metadata
            with self._engine.connect() as conn:
                self._debug_start_year = conn.execute(
                    sql.text(
                        "SELECT [start_year] "
                        "FROM [metadata].[run] "
                        "WHERE run_id = :run_id"
                    ),
                    {"run_id": self._yaml_config["debug"]["run_id"]},
                ).scalar()
                self._debug_end_year = conn.execute(
                    sql.text(
                        "SELECT [end_year] "
                        "FROM [metadata].[run] "
                        "WHERE run_id = :run_id"
                    ),
                    {"run_id": self._yaml_config["debug"]["run_id"]},
                ).scalar()

            # Store the run id in the class instance and return
            self.run_id = self._yaml_config["debug"]["run_id"]
            return self._yaml_config["debug"]["run_id"]

        else:
            raise ValueError("Either standard run mode or debug mode must be enabled")

    def _parse_mgra_version(self) -> str:
        """Parse the MGRA version from the configuration file."""
        # Use the supplied mgra version if standard run mode is enabled
        if self._yaml_config["run"]["enabled"]:
            return self._yaml_config["default"]["mgra"]

        # Get mgra version from database if debug mode is enabled
        elif self._yaml_config["debug"]["enabled"]:
            # Ensure run id exists in the database
            self._check_run_id(engine=self._engine, run_id=self.run_id)

            with self._engine.connect() as conn:
                query = sql.text(
                    "SELECT [mgra] FROM [metadata].[run] WHERE run_id = :run_id"
                )
                return conn.execute(query, {"run_id": self.run_id}).scalar()
