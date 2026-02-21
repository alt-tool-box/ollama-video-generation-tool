import logging
import sys
from pathlib import Path

# Try to load config for log level, fallback to INFO
try:
    from config import config
    LOG_LEVEL = getattr(config, 'LOG_LEVEL', 'INFO')
except ImportError:
    LOG_LEVEL = 'INFO'


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Setup and return a logger with consistent formatting.
    
    Args:
        name: Logger name (usually __name__ or app name)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Set level
    log_level = getattr(logging, (level or LOG_LEVEL).upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Format: timestamp - name - level - message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    return logger


# Pre-configured loggers for common use
def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name."""
    return setup_logger(name)
