"""
EasyPay Payment Gateway - Logging Infrastructure
"""
import logging
import os
import sys
from typing import Optional

import structlog

from .logging_config import setup_enhanced_logging, get_audit_logger, get_log_aggregator


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


def setup_logging() -> logging.Logger:
    """
    Set up enhanced structured logging.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    return setup_enhanced_logging()


# Global instances
audit_logger = get_audit_logger()
log_aggregator = get_log_aggregator()
