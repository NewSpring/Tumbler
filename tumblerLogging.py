import logging
import logging.config

#TODO: use dictConfig to pass dynamic script names with YML file, ex. logging.getLogger(name)

# logging configuration for all handlers
logging.config.fileConfig("logging.conf")
logger = logging.getLogger("tumblerLogger")
