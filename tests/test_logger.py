import io
import re
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import logger as logger_module


@pytest.fixture
def logger_instance(tmp_path: Path):
    instance = logger_module.initialize(tmp_path)
    console = instance._console_handler.stream
    output = io.StringIO()
    instance._console_handler.setStream(output)

    yield instance, tmp_path, output

    instance._console_handler.setStream(console)
    if instance._file_handler is not None:
        instance._logger.removeHandler(instance._file_handler)
        instance._file_handler.close()
        instance._file_handler = None
    instance._logger.removeHandler(instance._console_handler)
    instance._logger.removeFilter(instance._execution_id_filter)
    instance._execution_id = None
    instance._initialized = False
    instance.__class__._instance = None
    logger_module.logger._instance = None


def test_is_singleton_and_rejects_a_different_folder(logger_instance) -> None:
    logger, log_folder, _ = logger_instance

    assert logger.__class__(log_folder) is logger
    with pytest.raises(RuntimeError):
        logger.__class__(log_folder / "different")


def test_execution_id_is_added_until_cleared(logger_instance) -> None:
    _, log_folder, output = logger_instance

    logger_module.definir_id_execucao("123ABC")
    logger_module.warning("Minha msg aqui")
    logger_module.info("Mensagem com o mesmo ID")
    logger_module.definir_id_execucao(None)
    logger_module.warning("Mensagem sem ID")

    console = re.sub(r"\033\[[0-9;]*m", "", output.getvalue())
    assert "[WARNING]       [123ABC] Minha msg aqui" in console
    assert "[INFO]          [123ABC] Mensagem com o mesmo ID" in console
    assert "[WARNING]       Mensagem sem ID" in console

    content = next(log_folder.glob("*.log")).read_text(encoding="utf-8")
    assert "[WARNING]       [123ABC] Minha msg aqui" in content
    assert "[INFO]          [123ABC] Mensagem com o mesmo ID" in content
    assert "[WARNING]       Mensagem sem ID" in content


def test_execution_id_must_be_a_string_or_none(logger_instance) -> None:
    with pytest.raises(TypeError):
        logger_module.definir_id_execucao(123)  # type: ignore[arg-type]


def test_console_colors_and_debug_is_not_written_to_file(logger_instance) -> None:
    logger, log_folder, output = logger_instance

    logger_module.debug("debug-only")
    logger_module.info("info-message")
    logger_module.warning("warning-message")
    logger_module.error("error-message")

    console = output.getvalue()
    assert "debug-only" in console
    debug_line = next(line for line in console.splitlines() if "debug-only" in line)
    assert "[DEBUG]" in debug_line
    assert "\033[" not in debug_line
    assert "\033[34m[INFO]\033[0m          info-message" in console
    assert "\033[33m[WARNING]\033[0m       warning-message" in console
    assert "\033[31m[ERROR]\033[0m         error-message" in console

    files = list(log_folder.glob("*.log"))
    assert len(files) == 1
    assert files[0].name == datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
    content = files[0].read_text(encoding="utf-8")
    assert "debug-only" not in content
    assert "info-message" in content
    assert "warning-message" in content
    assert "error-message" in content
    assert "[INFO]          info-message" in content
    assert "[WARNING]       warning-message" in content
    assert "\033[" not in content


def test_creates_a_new_timestamped_file_after_midnight(logger_instance) -> None:
    logger, log_folder, _ = logger_instance

    with patch("logger.logger.datetime") as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2027, 4, 5, 6, 7, 8)
        logger.info("first-day")
        mocked_datetime.now.return_value = datetime(2027, 4, 6, 0, 0, 1)
        logger.info("next-day")

    first_day = log_folder / "2027-04-05_06-07-08.log"
    next_day = log_folder / "2027-04-06_00-00-01.log"
    assert "first-day" in first_day.read_text(encoding="utf-8")
    assert "next-day" in next_day.read_text(encoding="utf-8")
