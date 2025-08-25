import logging


def test_litellm_loggers_set_to_warning_by_default():
    # Importing logger module triggers its configuration
    import openhands.core.logger as logger_mod  # noqa: F401

    lite_logger = logging.getLogger("LiteLLM")
    litellm_logger = logging.getLogger("litellm")

    # Ensure the library loggers are not noisier than WARNING by default
    assert lite_logger.level == logging.WARNING
    assert litellm_logger.level == logging.WARNING
