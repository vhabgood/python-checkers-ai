# create_sqlite_db.py
import sqlite3
import pickle
import os
import glob
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_database(db_name="checkers_database.db"):
    """Creates and populates the SQLite database from .pkl files."""
    
    if os.path.exists(db_name):
        logging.info(f"Database '{db_name}' already exists. Deleting old file.")
        os.remove(db_name)

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    logging.info(f"Successfully created and connected to '{db_name}'.")

    # --- 1. Create Tables ---
    cursor.execute('''
        CREATE TABLE opening_book (
            board_hash INTEGER PRIMARY KEY,
            score REAL NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE endgame_tables (
            table_name TEXT NOT NULL,
            board_config TEXT NOT NULL,
            result TEXT NOT NULL,
            PRIMARY KEY (table_name, board_config)
        )
    ''')
    logging.info("Successfully created 'opening_book' and 'endgame_tables' tables.")

    # --- 2. Load and Insert Data ---
    resources_path = "resources"
    pkl_files = glob.glob(os.path.join(resources_path, '*.pkl'))
    
    if not pkl_files:
        logging.warning(f"No .pkl files found in '{resources_path}'. Database will be empty.")
        conn.close()
        return

    logging.info(f"Found {len(pkl_files)} .pkl files to process.")

    for pkl_file in pkl_files:
        filename = os.path.basename(pkl_file)
        
        if filename == 'game_resources.pkl':
            logging.info(f"Skipping '{filename}' as it is a bundled resource.")
            continue
            
        table_name = os.path.splitext(filename)[0]
        
        try:
            with open(pkl_file, 'rb') as f:
                data = pickle.load(f)

            if not isinstance(data, dict):
                logging.warning(f"Skipping '{filename}': Expected a dictionary, but found {type(data)}.")
                continue

            if 'book' in table_name:
                # --- FIX: Safely handle the opening book ---
                try:
                    # Attempt to process assuming integer keys, as the game engine expects.
                    to_insert = [(int(key), val) for key, val in data.items()]
                    cursor.executemany('INSERT INTO opening_book (board_hash, score) VALUES (?, ?)', to_insert)
                    logging.info(f"Inserted {len(to_insert)} records into 'opening_book' from '{filename}'.")
                except TypeError:
                    # If keys are not integers (e.g., tuples), log a warning and skip.
                    logging.warning(
                        f"Could not process '{filename}'. Its keys are not in the expected integer format. "
                        "This file should be regenerated with integer (Zobrist hash) keys."
                    )
            else:
                # This is an endgame table
                to_insert = []
                for key, val in data.items():
                    key_str = str(key)
                    to_insert.append((table_name, key_str, val))
                
                cursor.executemany('INSERT INTO endgame_tables (table_name, board_config, result) VALUES (?, ?, ?)', to_insert)
                logging.info(f"Inserted {len(to_insert)} records into 'endgame_tables' for '{table_name}'.")
        
        except Exception as e:
            logging.error(f"Failed to process '{filename}': {e}")

    # --- 3. Commit changes and close ---
    conn.commit()
    conn.close()
    logging.info("Database creation complete. All changes have been saved.")

if __name__ == '__main__':
    create_database()
