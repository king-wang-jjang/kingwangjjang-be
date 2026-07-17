import logging


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("gpt-service")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(levelname)s: [%(asctime)s] %(name)s %(filename)s:%(lineno)d - %(message)s"
        )
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def catch_exception(exc_type, exc_value, exc_traceback) -> None:
    setup_logger().exception(
        "Unexpected exception.",
        exc_info=(exc_type, exc_value, exc_traceback),
    )
