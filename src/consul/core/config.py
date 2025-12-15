from importlib import resources

import yaml
from loguru import logger
from pydantic_core import ValidationError

from consul.db.handler import get_db_handler
from consul.db.tables import AppConfigTable


def store_defaults(*, force_refresh: bool = False) -> None:
    """Checks if database contains configurations defined in defaults.yaml and stores them in db if not."""
    # Check if database table with configuration is empty
    handler = get_db_handler()
    configs = handler.load(AppConfigTable)
    if configs and not force_refresh:
        return

    # Loads all yaml files from consul.configs directory and validates, that they can be store in the database
    config_dir = resources.files("consul.configs")
    data = []
    for config_path in config_dir.iterdir():
        try:
            if config_path.suffix.lower() == ".yaml":
                with config_path.open("r", encoding="utf-8") as file:
                    file_data = yaml.safe_load(file)
                data.extend([AppConfigTable.model_validate(row) for row in file_data])
        except (TypeError, ValidationError) as e:
            msg = f"YAML file {config_path.name} wan't loaded due to: {e!s}."
            logger.warning(msg)

    if not data:
        msg = "No default configuration data were retrieved, application cannot be started!"
        logger.error(msg)
        raise RuntimeError(msg)

    # Clears table and stores new values
    handler.clear_table(AppConfigTable)
    handler.store(data)
    logger.success(f"Stored default Consul configuration into {len(data)} rows.")
