'''
Objectives
- Keep the logs in files and standard out
Usage Examples
    import logging_setup as Logger
    logging = Logger.configure_logging(Path("./"))
    logging.info(f"This is the logger module imported.")
To do
- 

v. 0.1 : authored by HYP (Some functions and portions of codes are taken from various websites.)
2025.02.20
Changes
- Tested on Ubuntu 22.04
'''
import logging as Logging
from datetime import datetime

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

if __name__ == "__main__":
    from pathlib import Path
    Logger = configure_logging(Path("./"))
    Logger.info(f"This is the logger module working example.")
