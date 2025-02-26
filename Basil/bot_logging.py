import logging
import os

# Ensure logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configure logging settings
logging.basicConfig(
    filename="logs/basil_bot.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO
)

def log_event(event_type: str, message: str):
    """Logs an event with a specific type and message."""
    if event_type.lower() == "info":
        logging.info(message)
    elif event_type.lower() == "warning":
        logging.warning(message)
    elif event_type.lower() == "error":
        logging.error(message)
    elif event_type.lower() == "critical":
        logging.critical(message)
    else:
        logging.debug(message)

# Example usage
if __name__ == "__main__":
    log_event("info", "Basil Bot logging initialized.")
