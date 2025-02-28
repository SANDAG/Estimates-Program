import sqlalchemy as sql


def parse_config(config: dict) -> None:
    """Parse the configuration YAML file and validate its contents.

    Args:
        config (dict): The loaded configuration dictionary.

    Raises:
        ValueError: If any of the configuration values are invalid.
    """
    # Check if both standard run and debug modes are enabled
    if config["run"]["enabled"] & config["debug"]["enabled"]:
        raise ValueError("debug mode cannot be enabled along with standard run mode")

    # Parse arguments to standard run mode
    elif config["run"]["enabled"]:
        if config["run"]["mgra"] != "mgra15":
            raise ValueError("only 'mgra15' supported")
        if not isinstance(config["run"]["start_year"], int):
            raise ValueError("start year must be an integer")
        elif not isinstance(config["run"]["end_year"], int):
            raise ValueError("end year must be an integer")
        elif config["run"]["start_year"] > config["run"]["end_year"]:
            raise ValueError("start year cannot be greater than end year")

    # Parse arguments to debug mode
    elif config["debug"]["enabled"]:
        if not isinstance(config["debug"]["run_id"], int):
            raise ValueError("run_id must be an integer")
        if not isinstance(config["debug"]["year"], int):
            raise ValueError("year must be an integer")

    else:
        raise ValueError("Either standard run mode or debug mode must be enabled")


def parse_run_id(config: dict) -> int:
    """Parse the run id from the configuration file.

    This function will create a new run id if standard run mode is enabled.
    The new run id is generated as the maximum run id in the database plus one.
    If debug mode is enabled, the supplied run id is validated against the
    database and returned.

    Args:
        config (dict): The loaded configuration dictionary.

    Raises:
        ValueError: If any of the configuration values are invalid.
    """

    from python.utils import ESTIMATES_ENGINE  # avoid circular import

    # Create a new run id if standard run mode is enabled
    if config["run"]["enabled"]:
        with ESTIMATES_ENGINE.connect() as conn:
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
                    "mgra": config["run"]["mgra"],
                    "start_year": config["run"]["start_year"],
                    "end_year": config["run"]["end_year"],
                    "version": config["run"]["version"],
                    "comments": config["run"]["comments"],
                },
            )

            # Commit the transaction
            conn.commit()

            return run_id

    # Use the supplied run id if debug mode is enabled
    elif config["debug"]["enabled"]:
        with ESTIMATES_ENGINE.connect() as conn:
            # Ensure supplied run id exists in the database
            query = sql.text(
                """
                    SELECT CASE WHEN EXISTS (
                        SELECT [run_id] FROM [metadata].[run] WHERE run_id = :run_id
                    ) THEN 1 ELSE 0 END
                """
            )

            exists = conn.execute(query, {"run_id": config["debug"]["run_id"]}).scalar()

            if exists == 0:
                raise ValueError("run_id does not exist in the database")

        return config["debug"]["run_id"]

    else:
        raise ValueError("Either standard run mode or debug mode must be enabled")


def parse_mgra_version(run_id: int) -> str:
    """Parse the MGRA version from the run identifier."""

    from python.utils import ESTIMATES_ENGINE  # avoid circular import

    with ESTIMATES_ENGINE.connect() as conn:
        query = sql.text("SELECT [mgra] FROM [metadata].[run] WHERE run_id = :run_id")
        return conn.execute(query, {"run_id": run_id}).scalar()
