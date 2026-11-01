"""Standardized execution logging.

Use ``initialize(log_folder)`` once, then call ``debug``, ``info``,
``warning`` or ``error`` at module level.
"""

from .logger import (
    ExecutionLogger,
    debug,
    definir_id_execucao,
    error,
    info,
    initialize,
    warning,
)

__all__ = [
    "ExecutionLogger",
    "initialize",
    "definir_id_execucao",
    "debug",
    "info",
    "warning",
    "error",
]
