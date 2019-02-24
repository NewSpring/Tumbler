import logging
import logging.config

import yaml

#TODO: use dictConfig to pass dynamic script names with YML file, ex. logging.getLogger(name)


def getLogger(name=""):
    """This will return a logger based on logging.yaml."""

    with open("logging.yaml") as f:
        config = yaml.safe_load(f)

    logging.config.dictConfig(config)
    return logging.getLogger("tumbler")
