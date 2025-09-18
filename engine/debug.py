# engine/debug.py
import logging
import sys
from datetime import datetime

# Define the loggers we'll use throughout the application
LOGGERS = {
    'gameflow': logging.getLogger('gameflow'),
    'search': logging.getLogger('search'),
    'eval': logging.getLogger('eval'),
    'board': logging.getLogger('board')
}

def setup_logging(args):
    """
    Configures all loggers. INFO goes to console, DEBUG (if flagged) goes to file.
    """
    # --- Configure Root Logger (for Console INFO) ---
    root_logger = logging.getLogger()
    # Clear any existing handlers to prevent duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(message)s')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # --- Configure File Handler (for DEBUG) ---
    has_debug_flags = any(getattr(args, f"debug_{name}", False) for name in LOGGERS)

    if has_debug_flags:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/debug_{timestamp}.log"
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)-10s - %(levelname)-8s - %(message)s'
        )
        file_handler = logging.FileHandler(log_filename, mode='w')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)

        for name, logger in LOGGERS.items():
            # Clear any previous handlers from this specific logger
            if logger.hasHandlers():
                logger.handlers.clear()
            
            if getattr(args, f"debug_{name}", False):
                logger.setLevel(logging.DEBUG)
                logger.addHandler(file_handler)
                # This is the key: stop the logger from passing messages to the root
                logger.propagate = False
            else:
                # Ensure loggers not activated are disabled
                logger.propagate = False
                logger.disabled = True
