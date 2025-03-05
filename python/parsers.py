import sqlalchemy as sql


class InputParser:
    """A class to parse and validate input configurations.

    Note that in addition to validating the configuration dictionary, this
    class also creates the run id and inserts it into the database if
    standard run mode is enabled.

    The way standard run mode works is by overriding debug mode parameters.
    Specifically, debug mode is enabled, run_id is set to a specific value,
    module years are set to specific year ranges, and a new row is added to the
    run metadata table.

    Attributes:
        config (dict): The configuration dictionary to be parsed.
        run_id (int): The run identifier parsed from the configuration.

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
        self.config = config
        self.engine = engine
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

        # As stated in the class signature, we need to override config debug
        # values if we are trying to run everything
        if self.config["run"]["enabled"]:
            for key in [
                "startup",
                "housing_and_households",
                "population",
                "population_by_ase",
                "population_by_ase",
                "staging",
            ]:
                self.config["debug"][key] = list(
                    range(
                        self.config["run"]["start_year"],
                        self.config["run"]["end_year"] + 1,
                    )
                )

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
        # Check if both standard run and debug modes are enabled
        if self.config["run"]["enabled"] & self.config["debug"]["enabled"]:
            raise ValueError(
                "debug mode cannot be enabled along with standard run mode"
            )

        # Parse arguments to standard run mode
        elif self.config["run"]["enabled"]:
            if self.config["run"]["mgra"] != "mgra15":
                raise ValueError("only 'mgra15' supported")
            if not isinstance(self.config["run"]["start_year"], int):
                raise ValueError("start year must be an integer")
            elif not isinstance(self.config["run"]["end_year"], int):
                raise ValueError("end year must be an integer")
            elif self.config["run"]["start_year"] > self.config["run"]["end_year"]:
                raise ValueError("start year cannot be greater than end year")

        # Parse arguments to debug mode
        elif self.config["debug"]["enabled"]:
            if not isinstance(self.config["debug"]["run_id"], int):
                raise ValueError("run_id must be an integer")
            for key in [
                "startup",
                "housing_and_households",
                "population",
                "population_by_ase",
                "household_characteristics",
                "staging",
            ]:
                self._check_if_list_of_ints(self.config["debug"][key], key)

        else:
            raise ValueError("Either standard run mode or debug mode must be enabled")

    def _check_if_list_of_ints(self, to_check: list[int], variable_name: str):
        """Check if the provided input is a list of integers

        Args:
            to_check: The list to check. Technically Python type hinting should
                kind of check, but best to be explicit about it
            variable_name: Only used in case of error to display the proper name

        Returns:
            None

        Raises:
            ValueError: If the input is not a list
            TypeError: If the input list contains non-integers (can be empty)
        """
        if not isinstance(to_check, list):
            raise ValueError(f"{variable_name} must be an list")
        if not all([isinstance(item, int) for item in to_check]):
            raise TypeError(f"{variable_name} can only contain integers")

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
        # Create a new run id if standard run mode is enabled
        if self.config["run"]["enabled"]:
            with self.engine.connect() as conn:
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
                        "mgra": self.config["run"]["mgra"],
                        "start_year": self.config["run"]["start_year"],
                        "end_year": self.config["run"]["end_year"],
                        "version": self.config["run"]["version"],
                        "comments": self.config["run"]["comments"],
                    },
                )

                # Commit the transaction
                conn.commit()

                # Store the run id in the class instance and return
                self.run_id = run_id
                return run_id

        # Use the supplied run id if debug mode is enabled
        elif self.config["debug"]["enabled"]:
            # Ensure supplied run id exists in the database
            self._check_run_id(
                engine=self.engine, run_id=self.config["debug"]["run_id"]
            )

            # Store the run id in the class instance and return
            self.run_id = self.config["debug"]["run_id"]
            return self.config["debug"]["run_id"]

        else:
            raise ValueError("Either standard run mode or debug mode must be enabled")

    def _parse_mgra_version(self) -> str:
        """Parse the MGRA version from the configuration file."""
        # Use the supplied mgra version if standard run mode is enabled
        if self.config["run"]["enabled"]:
            return self.config["run"]["mgra"]

        # Get mgra version from database if debug mode is enabled
        elif self.config["debug"]["enabled"]:
            # Ensure run id exists in the database
            self._check_run_id(engine=self.engine, run_id=self.run_id)

            with self.engine.connect() as conn:
                query = sql.text(
                    "SELECT [mgra] FROM [metadata].[run] WHERE run_id = :run_id"
                )
                return conn.execute(query, {"run_id": self.run_id}).scalar()
