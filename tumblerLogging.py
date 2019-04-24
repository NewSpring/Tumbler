import logging
import logging.config

import yaml


def getLogger():
    """This will return a logger based on logging.yaml."""

    with open("logging.yaml") as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)
    return logging.getLogger("tumbler")
