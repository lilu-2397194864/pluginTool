import logging
from logging.handlers import RotatingFileHandler
import os
import inspect

class Logger:
    def __init__(self, name, log_level=logging.DEBUG, log_file="./ielts.log"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # 创建一个handler，用于写入日志
        handler = logging.StreamHandler()
        handler.setFormatter(self.create_formatter())
        self.logger.addHandler(handler)

        # 创建一个handler，用于写入日志文件
        handler = logging.FileHandler(log_file)
        handler.setFormatter(self.create_formatter())
        self.logger.addHandler(handler)

        self.INFO = logging.INFO
        self.DEBUG = logging.DEBUG
        self.WARN = logging.WARN
        self.ERROR = logging.ERROR
        self.CRITICAL = logging.CRITICAL

    def create_formatter(self):
        # 创建一个formatter，并设置其格式
        formatter = logging.Formatter(
            '<[%(asctime)s %(levelname)s %(message)s'
        )
        return formatter

    def log_info(self, message):
        self.logger.info(message)

    def log_debug(self, message):
        self.logger.debug(message)

    def log_warning(self, message):
        self.logger.warning(message)

    def log_error(self, message):
        self.logger.error(message)

    def log_critical(self, message):
        self.logger.critical(message)

    def context(self, level, message):
        # 获取调用处的信息
        caller_frame = inspect.currentframe().f_back
        caller_filename = os.path.relpath(caller_frame.f_code.co_filename)
        caller_lineno = caller_frame.f_lineno
        caller_name = caller_frame.f_code.co_name

        # 格式化并输出日志
        log_message = f'{caller_filename}:{caller_lineno}:{caller_name}]> {message}'
        self.logger.log(level, log_message)


# 使用示例
if __name__ == "__main__":

    logger = Logger('IELTS_LOG')
    logger.context(logging.INFO, 'This is a test log message')
    logger.context(logging.DEBUG, 'This is a test log message')
