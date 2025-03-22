'''
Objectives
- Overall: keep all the utility functions
- Keep the logs in files and standard out

Usage Examples
    import proj_util as util
    logging = util.configure_logging(Path("./"))
    logging.info(f"This is the logger module imported.")
Reference
- https://stackoverflow.com/questions/15746675/how-to-write-a-python-module-package

Version History
v. 0.0.1 : authored by HYP (Some functions and portions of codes are taken from various websites.)
2025.02.20
- Tested on Ubuntu 22.04
'''
import logging as Logging
from datetime import datetime
from pathlib import Path

def setup_logger(name, log_file=None, file_level=Logging.DEBUG, console_level=Logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', date_format='%Y-%m-%d %H:%M:%S', console=True):
    """
    Set up a logger with different logging levels for file and console outputs.
    
    :param name: Logger name
    :param log_file: File path for the log file (optional)
    :param file_level: Logging level for the file handler (default: DEBUG)
    :param console_level: Logging level for the console handler (default: INFO)
    :param format: Logging format (default: basic format)
    :param date_format: date & time format
    :param console: Whether to enable console logging (default: True)
    :return: Configured logger
    """
    logging = Logging.getLogger(name)
    logging.setLevel(Logging.DEBUG)  # Set the overall logger level to the most verbose option

    formatter = Logging.Formatter(format, datefmt=date_format)
    
    # Remove existing handlers (to avoid duplicate logs)
    if logging.hasHandlers():
        logging.handlers.clear()

    # File handler
    if log_file:
        file_handler = Logging.FileHandler(log_file)
        file_handler.setLevel(file_level)  # Set file-specific logging level
        file_handler.setFormatter(formatter)
        logging.addHandler(file_handler)

    # Console handler
    if console:
        console_handler = Logging.StreamHandler()
        console_handler.setLevel(console_level)  # Set console-specific logging level
        console_handler.setFormatter(formatter)
        logging.addHandler(console_handler)

    return logging

def configure_logging(output_path, log_file_prefix='log', log_extension='txt', file_level=Logging.DEBUG, console_level=Logging.INFO):
    """Set up logging to a file."""
    # Configure logging
    log_format = '%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s'
    log_file = output_path / f"{log_file_prefix}_{datetime.today().strftime('%Y%m%d_%H%M')}.{log_extension}"
    
    # Create a logger with separate levels for file and console
    logger = setup_logger(
        name="CombinedLogger",
        log_file=log_file,
        file_level=file_level,      # File will log DEBUG and above
        console_level=console_level,  # Console will log WARNING and above
        format=log_format,
        console=True
    )
    logger.info(f"{datetime.today().strftime('%a %b %d %T %Y')}")
    return logger

def initialize_paths(parent_dir_name="./", in_dir_name="log", out_dir_prefix="out_"):
    """Initialize input and output paths."""
    directory = Path(parent_dir_name)
    input_folder = directory / in_dir_name
    today = datetime.today().strftime("%Y%m%d_%H%M")
    report_folder = Path(f"{parent_dir_name}{out_dir_name}{today}")

    # Ensure unique folder name
    idx = 0
    while report_folder.exists():
        idx += 1
        report_folder = Path(f"{parent_dir_name}{out_dir_name}{today}_{idx}")

    report_folder.mkdir(parents=True, exist_ok=True)
    return input_folder, report_folder

if __name__ == "__main__":
    Logger = configure_logging(Path("./"))
    Logger.info(f"This is the logger module working example.")
