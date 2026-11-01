
"""Registro de mensagens no console e em arquivos diários.

O módulo oferece funções de conveniência e a classe :class:`ExecutionLogger`.
É necessário chamar :func:`initialize` antes de usar as funções do módulo.
Mensagens de depuração são exibidas somente no console; mensagens INFO,
WARNING e ERROR também são gravadas em um arquivo por dia. O identificador
de execução, quando definido, é incluído nas mensagens seguintes.
"""

import copy
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union


_LOG_FORMAT = "%(asctime)s %(levelname)s%(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LEVEL_COLUMN_WIDTH = len("[WARNING]") + 1
_LEVEL_COLORS = {
    logging.INFO: "\033[34m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
}


class _AlignedFormatter(logging.Formatter):
    """Formata mensagens com níveis alinhados e detalhes opcionais da chamada."""

    def __init__(
        self,
        fmt: str,
        datefmt: str,
        *,
        use_colors: bool = False,
        detailed: bool = False,
    ) -> None:
        """Configura o formato, as cores do console e o modo detalhado.

        Args:
            fmt: Modelo de formatação da biblioteca ``logging``.
            datefmt: Formato usado para a data e hora.
            use_colors: Se verdadeiro, aplica cores ANSI ao nível da mensagem.
            detailed: Se verdadeiro, inclui módulo e função de origem.
        """
        super().__init__(fmt, datefmt=datefmt)
        self._use_colors = use_colors
        self._detailed = detailed

    def format(self, record: logging.LogRecord) -> str:
        """Produz uma linha formatada sem modificar o registro original."""
        formatted_record = copy.copy(record)
        if self._detailed:
            caller = (
                f"{record.module};{record.funcName}"
                if record.funcName != "<module>"
                else record.module
            )
            formatted_record.msg = f"{caller}; {record.getMessage()}"
            formatted_record.args = ()

        level_label = f"[{record.levelname}]"
        color = _LEVEL_COLORS.get(record.levelno) if self._use_colors else None
        color_entire_line = color is not None and record.levelno in (
            logging.WARNING,
            logging.ERROR,
        )
        if color is not None and not color_entire_line:
            level_label = f"{color}{level_label}\033[0m"

        label_width = len(f"[{record.levelname}]")
        padding = " " * max(1, _LEVEL_COLUMN_WIDTH - label_width)
        execution_id = getattr(record, "execution_id", None)
        id_label = f"[{execution_id}] " if execution_id is not None else ""
        formatted_record.levelname = f"{level_label}{padding}{id_label}"
        formatted_message = super().format(formatted_record)
        if color_entire_line:
            return f"{color}{formatted_message}\033[0m"
        return formatted_message


class _ExecutionIdFilter(logging.Filter):
    """Acrescenta aos registros o identificador atual da execução."""

    def __init__(self, logger_instance: "ExecutionLogger") -> None:
        """Associa o filtro à instância que fornece o identificador."""
        super().__init__()
        self._logger_instance = logger_instance

    def filter(self, record: logging.LogRecord) -> bool:
        """Define ``execution_id`` no registro e permite seu processamento."""
        record.execution_id = self._logger_instance._execution_id
        return True


class ExecutionLogger:
    """Registra mensagens no console e em um arquivo datado por dia.

    A primeira inicialização define a pasta de saída durante todo o processo.
    Uma nova inicialização com outra pasta gera ``RuntimeError``. O modo
    detalhado pode ser alterado em inicializações posteriores para a mesma
    pasta. As operações de escrita são sincronizadas entre threads.
    """

    _instance: Optional["ExecutionLogger"] = None
    _instance_lock = threading.Lock()
    _initialization_lock = threading.Lock()
    _lock: threading.RLock
    _initialized: bool

    def __new__(
        cls,
        log_folder: Union[str, Path],
        detailed: bool = False,
    ) -> "ExecutionLogger":
        """Obtém a instância singleton de :class:`ExecutionLogger`.

        Args:
            log_folder: Pasta de destino dos arquivos de log.
            detailed: Indica se os registros devem incluir módulo e função.

        Returns:
            A única instância de :class:`ExecutionLogger` no processo.
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._lock = threading.RLock()
            return cls._instance

    def __init__(self, log_folder: Union[str, Path], detailed: bool = False) -> None:
        """Inicializa os destinos de log na pasta indicada.

        Args:
            log_folder: Pasta onde serão criados os arquivos diários.
            detailed: Inclui módulo e função de origem nas mensagens.

        Raises:
            TypeError: Se ``detailed`` não for booleano.
            RuntimeError: Se a instância já estiver vinculada a outra pasta.
        """
        if not isinstance(detailed, bool):
            raise TypeError("detailed must be a bool.")

        with self._initialization_lock:
            folder = Path(log_folder).expanduser().resolve()
            if self._initialized:
                if folder != self._log_folder:
                    raise RuntimeError(
                        "ExecutionLogger is already initialized with a different folder."
                    )
                self._set_detailed(detailed)
                return

            folder.mkdir(parents=True, exist_ok=True)
            self._log_folder = folder
            self._logger = logging.getLogger("logger")
            self._logger.setLevel(logging.DEBUG)
            self._logger.propagate = False
            self._execution_id: Optional[str] = None
            self._execution_id_filter = _ExecutionIdFilter(self)
            self._logger.addFilter(self._execution_id_filter)

            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(logging.DEBUG)
            self._console_handler.setFormatter(
                _AlignedFormatter(
                    _LOG_FORMAT,
                    datefmt=_DATE_FORMAT,
                    use_colors=True,
                    detailed=detailed,
                )
            )
            self._logger.addHandler(self._console_handler)

            self._file_handler: Optional[logging.FileHandler] = None
            self._log_date = None
            self._detailed = detailed
            self._initialized = True

    def _set_detailed(self, detailed: bool) -> None:
        """Atualiza o modo detalhado nos formatadores ativos.

        Args:
            detailed: Se verdadeiro, inclui módulo e função de origem.
        """
        with self._lock:
            self._detailed = detailed
            self._console_handler.setFormatter(
                _AlignedFormatter(
                    _LOG_FORMAT,
                    datefmt=_DATE_FORMAT,
                    use_colors=True,
                    detailed=detailed,
                )
            )
            if self._file_handler is not None:
                self._file_handler.setFormatter(
                    _AlignedFormatter(_LOG_FORMAT, datefmt=_DATE_FORMAT, detailed=detailed)
                )

    def debug(self, message: object, *args: Any, **kwargs: Any) -> None:
        """Registra uma mensagem de depuração somente no console.

        Args:
            message: Texto da mensagem, que pode usar formatação do ``logging``.
            *args: Valores posicionais usados na formatação da mensagem.
            **kwargs: Opções adicionais aceitas por ``logging.Logger.log``.
        """
        self._write(logging.DEBUG, message, args, kwargs, stacklevel=3)

    def info(self, message: object, *args: Any, **kwargs: Any) -> None:
        """Registra uma informação no console e no arquivo diário.

        Args:
            message: Texto da mensagem, que pode usar formatação do ``logging``.
            *args: Valores posicionais usados na formatação da mensagem.
            **kwargs: Opções adicionais aceitas por ``logging.Logger.log``.
        """
        self._write(logging.INFO, message, args, kwargs, stacklevel=3)

    def warning(self, message: object, *args: Any, **kwargs: Any) -> None:
        """Registra um aviso no console e no arquivo diário.

        A linha do aviso é exibida em amarelo no console.

        Args:
            message: Texto da mensagem, que pode usar formatação do ``logging``.
            *args: Valores posicionais usados na formatação da mensagem.
            **kwargs: Opções adicionais aceitas por ``logging.Logger.log``.
        """
        self._write(logging.WARNING, message, args, kwargs, stacklevel=3)

    def error(self, message: object, *args: Any, **kwargs: Any) -> None:
        """Registra um erro no console e no arquivo diário.

        A linha do erro é exibida em vermelho no console.

        Args:
            message: Texto da mensagem, que pode usar formatação do ``logging``.
            *args: Valores posicionais usados na formatação da mensagem.
            **kwargs: Opções adicionais aceitas por ``logging.Logger.log``.
        """
        self._write(logging.ERROR, message, args, kwargs, stacklevel=3)

    def definir_id_execucao(self, execution_id: Optional[str]) -> None:
        """Define ou limpa o ID de execução dos próximos registros.

        O ID definido aparece entre colchetes após o nível do log e permanece
        ativo até esta função ser chamada novamente com ``None``.

        Args:
            execution_id: ID textual da execução ou ``None`` para removê-lo.

        Raises:
            TypeError: Se o valor não for uma string nem ``None``.
        """
        if execution_id is not None and not isinstance(execution_id, str):
            raise TypeError("execution_id must be a string or None.")
        with self._lock:
            self._execution_id = execution_id

    def _write(
        self,
        level: int,
        message: object,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        stacklevel: int,
    ) -> None:
        """Envia uma mensagem ao logger e prepara o arquivo diário se necessário.

        Args:
            level: Nível de severidade definido pelo módulo ``logging``.
            message: Texto ou objeto que será registrado.
            args: Valores posicionais para formatar a mensagem.
            kwargs: Opções adicionais para a chamada do logger.
            stacklevel: Quantidade de quadros ignorados para localizar a origem.
        """
        with self._lock:
            if level != logging.DEBUG:
                self._ensure_daily_file(datetime.now())
            self._logger.log(level, message, *args, stacklevel=stacklevel, **kwargs)

    def _ensure_daily_file(self, timestamp: datetime) -> None:
        """Abre ou troca o arquivo de log correspondente à data informada.

        Args:
            timestamp: Data e hora usadas para determinar o nome do arquivo.
        """
        log_date = timestamp.date()
        if self._file_handler is not None and log_date == self._log_date:
            return

        if self._file_handler is not None:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()

        filename = timestamp.strftime("%Y-%m-%d_%H-%M-%S.log")
        handler = logging.FileHandler(
            self._log_folder / filename,
            mode="a",
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            _AlignedFormatter(
                _LOG_FORMAT,
                datefmt=_DATE_FORMAT,
                detailed=self._detailed,
            )
        )
        self._logger.addHandler(handler)
        self._file_handler = handler
        self._log_date = log_date


_instance: Optional[ExecutionLogger] = None


def initialize(
    log_folder: Union[str, Path],
    detailed: bool = False,
) -> ExecutionLogger:
    """Inicializa e retorna o logger compartilhado.

    Args:
        log_folder: Pasta de destino dos arquivos de log.
        detailed: Se verdadeiro, inclui módulo e função de origem antes da
            mensagem. O padrão é ``False``.

    Returns:
        A instância compartilhada de :class:`ExecutionLogger`.

    Raises:
        TypeError: Se ``detailed`` não for booleano.
        RuntimeError: Se o singleton já estiver associado a outra pasta.
    """
    global _instance
    instance = ExecutionLogger(log_folder, detailed=detailed)
    _instance = instance
    return instance


def _get_instance() -> ExecutionLogger:
    """Retorna o logger inicializado ou informa como inicializá-lo."""
    if _instance is None:
        raise RuntimeError("Call logger.initialize(log_folder) before logging.")
    return _instance


def debug(message: object, *args: Any, **kwargs: Any) -> None:
    """Registra uma mensagem de depuração somente no console.

    Args:
        message: Texto da mensagem, que pode usar formatação do ``logging``.
        *args: Valores posicionais usados na formatação da mensagem.
        **kwargs: Opções adicionais aceitas por ``logging.Logger.log``.

    Raises:
        RuntimeError: Se ``initialize`` ainda não tiver sido chamado.
    """
    _module_log(logging.DEBUG, message, args, kwargs)


def info(message: object, *args: Any, **kwargs: Any) -> None:
    """Registra uma informação no console e no arquivo diário.

    Args:
        message: Texto da mensagem, que pode usar formatação do ``logging``.
        *args: Valores posicionais usados na formatação da mensagem.
        **kwargs: Opções adicionais aceitas por ``logging.Logger.log``.

    Raises:
        RuntimeError: Se ``initialize`` ainda não tiver sido chamado.
    """
    _module_log(logging.INFO, message, args, kwargs)


def warning(message: object, *args: Any, **kwargs: Any) -> None:
    """Registra um aviso no console e no arquivo diário.

    A linha do aviso é exibida em amarelo no console.

    Args:
        message: Texto da mensagem, que pode usar formatação do ``logging``.
        *args: Valores posicionais usados na formatação da mensagem.
        **kwargs: Opções adicionais aceitas por ``logging.Logger.log``.

    Raises:
        RuntimeError: Se ``initialize`` ainda não tiver sido chamado.
    """
    _module_log(logging.WARNING, message, args, kwargs)


def error(message: object, *args: Any, **kwargs: Any) -> None:
    """Registra um erro no console e no arquivo diário.

    A linha do erro é exibida em vermelho no console.

    Args:
        message: Texto da mensagem, que pode usar formatação do ``logging``.
        *args: Valores posicionais usados na formatação da mensagem.
        **kwargs: Opções adicionais aceitas por ``logging.Logger.log``.

    Raises:
        RuntimeError: Se ``initialize`` ainda não tiver sido chamado.
    """
    _module_log(logging.ERROR, message, args, kwargs)


def _module_log(
    level: int,
    message: object,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """Encaminha a mensagem à instância compartilhada com nível indicado."""
    _get_instance()._write(level, message, args, kwargs, stacklevel=4)


def definir_id_execucao(execution_id: Optional[str]) -> None:
    """Define ou limpa o ID de execução das próximas mensagens.

    O ID aparece entre colchetes após o nível e permanece ativo até ser limpo
    com ``None``.

    Args:
        execution_id: ID textual da execução ou ``None`` para removê-lo.

    Raises:
        RuntimeError: Se ``initialize`` ainda não tiver sido chamado.
        TypeError: Se o valor não for uma string nem ``None``.
    """
    _get_instance().definir_id_execucao(execution_id)
