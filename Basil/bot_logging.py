import logging
import os
from logging.handlers import RotatingFileHandler

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging settings
LOG_FILE = os.path.join(LOG_DIR, "basil_bot.log")

# ✅ Configure main logger
logger = logging.getLogger("BasilLogger")
logger.setLevel(logging.INFO)

# ✅ File handler (rotating log file)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=2)
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)

# ✅ Console handler (for terminal output)
console_handler = logging.StreamHandler()
console_handler.setFormatter(file_formatter)

# ✅ Add handlers (if not already added)
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def log_event(event_type: str, message: str):
    """Logs an event with a specific type and message."""
    event_type = event_type.lower()
    log_func = {
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
        "debug": logger.debug
    }.get(event_type, logger.debug)

    log_func(message)

# ✅ Example usage (only runs if script is executed directly)
if __name__ == "__main__":
    log_event("info", "Basil Bot logging initialized.")