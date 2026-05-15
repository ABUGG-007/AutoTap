"""
日志系统模块

提供统一的日志记录功能，支持控制台输出和文件输出，
按日期自动分割日志文件。
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    """日志记录器类

    提供统一的日志记录功能，支持控制台和文件双输出，
    按日期自动分割日志文件。

    Attributes:
        _instance: 单例实例
        _logger: logging.Logger 实例
        _log_dir: 日志文件目录路径
    """

    _instance: Optional["Logger"] = None
    _logger: Optional[logging.Logger] = None
    _log_dir: Path = Path("logs")
    _initialized: bool = False

    def __new__(cls) -> "Logger":
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialized = False
        return cls._instance

    def __init__(
        self,
        name: str = "autotap",
        log_dir: Optional[str] = None,
        level: int = logging.DEBUG,
    ) -> None:
        """初始化日志记录器

        Args:
            name: 日志记录器名称，默认为 "autoclicker"
            log_dir: 日志文件目录路径，默认为 "logs"
            level: 日志级别，默认为 DEBUG
        """
        if Logger._initialized:
            return

        if log_dir is not None:
            Logger._log_dir = Path(log_dir)

        Logger._logger = logging.getLogger(name)
        Logger._logger.setLevel(level)
        Logger._logger.handlers.clear()

        self._setup_formatters()
        self._setup_handlers(level)
        Logger._initialized = True

    def _setup_formatters(self) -> None:
        """配置日志格式"""
        Logger._formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _setup_handlers(self, level: int) -> None:
        """配置日志处理器"""
        Logger._log_dir.mkdir(parents=True, exist_ok=True)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(Logger._formatter)
        Logger._logger.addHandler(console_handler)

        log_file = self._get_log_file_path()
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(Logger._formatter)
        Logger._logger.addHandler(file_handler)

    def _get_log_file_path(self) -> Path:
        """获取当前日期的日志文件路径

        Returns:
            日志文件路径，格式：autoclicker_YYYY-MM-DD.log
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self._log_dir / f"autotap_{date_str}.log"

    def _log(self, level: int, message: str, module: str = "app") -> None:
        """内部日志记录方法

        Args:
            level: 日志级别
            message: 日志消息
            module: 模块名称
        """
        if Logger._logger is None:
            return

        log_message = f"[{module}] {message}"
        Logger._logger.log(level, log_message)

    def debug(self, message: str, module: str = "app") -> None:
        """记录 DEBUG 级别日志

        Args:
            message: 日志消息
            module: 模块名称，默认为 "app"
        """
        self._log(logging.DEBUG, message, module)

    def info(self, message: str, module: str = "app") -> None:
        """记录 INFO 级别日志

        Args:
            message: 日志消息
            module: 模块名称，默认为 "app"
        """
        self._log(logging.INFO, message, module)

    def warning(self, message: str, module: str = "app") -> None:
        """记录 WARNING 级别日志

        Args:
            message: 日志消息
            module: 模块名称，默认为 "app"
        """
        self._log(logging.WARNING, message, module)

    def error(self, message: str, module: str = "app") -> None:
        """记录 ERROR 级别日志

        Args:
            message: 日志消息
            module: 模块名称，默认为 "app"
        """
        self._log(logging.ERROR, message, module)

    def set_level(self, level: int) -> None:
        """设置日志级别

        Args:
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        """
        if Logger._logger is not None:
            Logger._logger.setLevel(level)
            for handler in Logger._logger.handlers:
                handler.setLevel(level)


_logger_instance: Optional[Logger] = None


def init_logger(
    name: str = "autotap",
    log_dir: str = "logs",
    level: int = logging.DEBUG,
) -> Logger:
    """初始化全局日志记录器

    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录
        level: 日志级别

    Returns:
        Logger 实例
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger()
        _logger_instance.__init__(name, log_dir, level)
    return _logger_instance


def log_debug(message: str, module: str = "app") -> None:
    """便捷函数：记录 DEBUG 日志

    Args:
        message: 日志消息
        module: 模块名称
    """
    global _logger_instance
    if _logger_instance is None:
        init_logger()
    _logger_instance.debug(message, module)


def log_info(message: str, module: str = "app") -> None:
    """便捷函数：记录 INFO 日志

    Args:
        message: 日志消息
        module: 模块名称
    """
    global _logger_instance
    if _logger_instance is None:
        init_logger()
    _logger_instance.info(message, module)


def log_warning(message: str, module: str = "app") -> None:
    """便捷函数：记录 WARNING 日志

    Args:
        message: 日志消息
        module: 模块名称
    """
    global _logger_instance
    if _logger_instance is None:
        init_logger()
    _logger_instance.warning(message, module)


def log_error(message: str, module: str = "app") -> None:
    """便捷函数：记录 ERROR 日志

    Args:
        message: 日志消息
        module: 模块名称
    """
    global _logger_instance
    if _logger_instance is None:
        init_logger()
    _logger_instance.error(message, module)


def get_logger() -> Logger:
    """获取全局日志记录器实例

    Returns:
        Logger 实例，如果未初始化则先初始化
    """
    global _logger_instance
    if _logger_instance is None:
        init_logger()
    return _logger_instance
