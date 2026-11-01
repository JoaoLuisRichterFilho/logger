"""Biblioteca para registro padronizado de mensagens de execução.

Chame ``initialize(pasta, detailed=False)`` antes de usar as funções
``debug``, ``info``, ``warning``, ``error`` ou ``definir_id_execucao``.
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
