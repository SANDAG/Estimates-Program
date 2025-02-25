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
