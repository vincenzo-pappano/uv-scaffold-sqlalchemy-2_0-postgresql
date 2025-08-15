import logging
from logging.config import dictConfig

from pathlib import Path

# from colorama import init, Fore, Back

# init(autoreset=True)


# class ColorFormatter(logging.Formatter):
#     # Change this dictionary to suit your coloring needs!
#     COLORS = {
#         "WARNING": Fore.RED,
#         "ERROR": Fore.RED + Back.WHITE,
#         "DEBUG": Fore.BLUE,
#         "INFO": Fore.GREEN,
#         "CRITICAL": Fore.RED + Back.WHITE
#     }

#     def format(self, record):
#         color = self.COLORS.get(record.levelname, "")
#         if color:
#             record.name = color + record.name
#             record.levelname = color + record.levelname
#             record.msg = color + record.msg
#         return logging.Formatter.format(self, record)


import yaml
class Logger:
    """
    A logger class that is initialized through a configuration object.
    """

    def __init__(self):
        import os
        # Load settings        
        logger_path = Path(__file__).resolve()
        print(f"{logger_path}")
        logger_path = Path(__file__).resolve().parent / "logger.yaml" # 'utils/logger.yaml'
        print(f"{logger_path}")
        try:
            with open(logger_path, 'r') as fp:
                self.config = yaml.safe_load(fp)  #  Config(logger_path)
            self.setup_logger()
        except FileNotFoundError as e:
            print(e)
            return

    def setup_logger(self):
        if self.config.get('logger') is not None:
            logging_config = self.config.get('logger')
            with open(logging_config['handlers']['file']['filename'], 'w') as f:
                f.write("\n\n\t\t START OF LOG\n\n")
                pass
            dictConfig(logging_config)
        else:
            # Default configuration with console and file handlers

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            # console_handler.setFormatter(ColorFormatter(
            #     '%(name)s - %(levelname)s - %(message)s'))
            console_handler.setFormatter(
                '%(name)s - %(levelname)s - %(message)s')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler = logging.FileHandler('app.log')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)

            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG)
            root_logger.addHandler(console_handler)
            root_logger.addHandler(file_handler)

            logging.warning(
                "Logging configuration not found in settings.yaml. Using default configuration.")

    def get_logger(self, name):
        return logging.getLogger(name)

logger_base = Logger()
