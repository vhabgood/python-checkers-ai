# engine/debug.py
import logging
import sys
import os
from datetime import datetime

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
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    
    # Let all messages flow up to the root logger
    root_logger.setLevel(logging.DEBUG)

    # Console Handler (displays INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # File Handler (writes DEBUG and above if any debug flag is set)
    has_debug_flags = any(getattr(args, f"debug_{name}", False) for name in LOGGERS)
    if has_debug_flags:
        if not os.path.exists('logs'):
            os.makedirs('logs')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/debug_{timestamp}.log"
        file_handler = logging.FileHandler(log_filename, mode='w')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)-10s - %(levelname)-8s - %(message)s'))
        file_handler.setLevel(logging.DEBUG)
        
        # This filter will control which logger's messages get written to the file
        class DebugFlagFilter(logging.Filter):
            def filter(self, record):
                for name in LOGGERS:
                    if record.name.startswith(name) and getattr(args, f"debug_{name}", False):
                        return True
                return False
        
        file_handler.addFilter(DebugFlagFilter())
        root_logger.addHandler(file_handler)
