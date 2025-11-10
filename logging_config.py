"""
Professional logging configuration with Rich console output and JSON file logging.

Features:
- Rich-based beautiful console output with icons and colors
- Full message content display (no truncation)
- Clean lines with visual hierarchy
- Shortened module names (webhook, openai, database, extractor)
- Dual output: pretty console + structured JSON file
- Minimal verbosity by default (INFO and above)
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text
from rich.theme import Theme

# Module name mappings for cleaner output
MODULE_NAME_MAP: Dict[str, str] = {
    '__main__': 'webhook',
    'webhook_openai': 'webhook',
    'openai_conversation_manager': 'openai',
    'data_extractor': 'extractor',
    'database': 'database',
    'webhook_notifier': 'notifier',
    'startup': 'startup'
}

# Custom theme for consistent colors
custom_theme = Theme({
    "logging.level.debug": "dim cyan",
    "logging.level.info": "green",
    "logging.level.warning": "yellow",
    "logging.level.error": "bold red",
    "logging.level.critical": "bold white on red",
})

# Create console instance
console = Console(theme=custom_theme)


class RichConsoleFormatter(logging.Formatter):
    """
    Custom formatter that works with RichHandler for beautiful output.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Get shortened module name
        module_name = MODULE_NAME_MAP.get(record.name, record.name)
        if len(module_name) > 10:
            module_name = module_name[:10]

        # Store shortened name for RichHandler
        record.name = module_name

        # Return just the message - RichHandler will add the rest
        return record.getMessage()


class JSONFileFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON file logging.

    Outputs one JSON object per line for easy parsing.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage(),
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add extra context if available
        if hasattr(record, 'phone'):
            log_entry['phone'] = record.phone
        if hasattr(record, 'conversation_id'):
            log_entry['conversation_id'] = record.conversation_id

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(log_level: int = logging.INFO, log_dir: str = 'logs') -> None:
    """
    Configure logging with Rich console output and JSON file logging.

    Args:
        log_level: Minimum log level to display (default: INFO)
        log_dir: Directory for log files (default: 'logs')
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything, filter at handler level

    # Remove any existing handlers
    root_logger.handlers.clear()

    # --- Rich Console Handler (Beautiful, Colorful) ---
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=False,  # Don't show file paths
        markup=True,  # Allow markup in messages
        rich_tracebacks=True,  # Beautiful tracebacks
        tracebacks_show_locals=False,  # Don't show local vars in tracebacks
        log_time_format="[%H:%M:%S]",  # Compact time format
    )
    console_handler.setLevel(log_level)  # Filter based on desired verbosity
    console_handler.setFormatter(RichConsoleFormatter())
    root_logger.addHandler(console_handler)

    # --- JSON File Handler (Everything) ---
    log_filename = os.path.join(log_dir, f'whatsapp_bot_{datetime.now().strftime("%Y%m%d")}.json')
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    file_handler.setFormatter(JSONFileFormatter())
    root_logger.addHandler(file_handler)

    # Suppress werkzeug (Flask) logs unless ERROR
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # Log successful initialization
    logger = logging.getLogger('startup')
    logger.info(f"✓ Logging initialized (console: {logging.getLevelName(log_level)}, file: DEBUG)")
    logger.debug(f"Log file: {log_filename}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Use this instead of logging.getLogger() for consistency.
    """
    return logging.getLogger(name)
