"""ログ出力共通処理
"""
import logging
import sys

# get_logger実行時のデフォルトログレベル
default_loglevel = logging.DEBUG


def get_logger(name: str | None = None, loglevel: str | int | None = None) -> logging.Logger:
    """ログ出力用にLoggerを取得する。

    :param name: ログ出力時の部品名称
    :param loglevel: ログレベル(logging.INFOなど), 省略可能

    :return logging.Logger: Loggerインスタンス
    """
    # ログ書式を設定する。
    _log_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # 標準出力ハンドラを設定する。
    _log_handler_stdout = logging.StreamHandler(sys.stdout)
    _log_handler_stdout.setFormatter(_log_formatter)
    # Loggerを取得する。
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_log_handler_stdout)
    if loglevel is None:
        loglevel = default_loglevel
    logger.setLevel(loglevel)
    return logger
