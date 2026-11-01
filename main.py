from src.logger import logger
logger = logger.initialize(log_folder="logs", detailed=True)
logger.definir_id_execucao("123ABC")
logger.debug("This is a debug message.")
logger.info("This is an info message.")
logger.definir_id_execucao('teste123')
logger.warning("This is a warning message.")
logger.error("This is an error message.")