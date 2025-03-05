import sqlalchemy as sql


class InputParser:
    """A class to parse and validate input configurations.

    Note that in addition to validating the configuration dictionary, this
    class also creates the run id and inserts it into the database if
    standard run mode is enabled.

    Attributes:
        config (dict): The configuration dictionary to be parsed.
        run_id (int): The run identifier parsed from the configuration.

    Methods:
        _check_run_id(): Checks if a run id exists in the database.
        parse_config(): Parses and validates the configuration dictionary.
        parse_run_id(): Parses the run identifier from the configuration.
        parse_mgra_version(): Parses the MGRA version from the run identifier.
    """

    def __init__(self, config: dict) -> None:
        """Initialize the InputParser with a configuration dictionary."""
        self.config = config
        self.run_id = None

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

    def parse_config(self) -> None:
        """Parse the configuration dictionary and validate its contents.

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
            if not isinstance(self.config["debug"]["year"], int):
                raise ValueError("year must be an integer")

        else:
            raise ValueError("Either standard run mode or debug mode must be enabled")

    def parse_run_id(self, engine: sql.Engine) -> int:
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
            with engine.connect() as conn:
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
            self._check_run_id(engine=engine, run_id=self.config["debug"]["run_id"])

            # Store the run id in the class instance and return
            self.run_id = self.config["debug"]["run_id"]
            return self.config["debug"]["run_id"]

        else:
            raise ValueError("Either standard run mode or debug mode must be enabled")

    def parse_mgra_version(self, engine: sql.Engine = None) -> str:
        """Parse the MGRA version from the configuration file."""
        # Use the supplied mgra version if standard run mode is enabled
        if self.config["run"]["enabled"]:
            return self.config["run"]["mgra"]

        # Get mgra version from database if debug mode is enabled
        elif self.config["debug"]["enabled"]:
            # Ensure run id exists in the database
            self._check_run_id(engine=engine, run_id=self.run_id)

            with engine.connect() as conn:
                query = sql.text(
                    "SELECT [mgra] FROM [metadata].[run] WHERE run_id = :run_id"
                )
                return conn.execute(query, {"run_id": self.run_id}).scalar()
