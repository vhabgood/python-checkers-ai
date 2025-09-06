# create_sqlite_db_V2.py
import sqlite3
import pickle
import os
import glob
import logging
import re

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_database(db_name="checkers_endgame.db"):
    """Creates and populates a structured SQLite database from .pkl files."""
    
    if os.path.exists(db_name):
        logging.info(f"Database '{db_name}' already exists. Deleting old file.")
        os.remove(db_name)

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    logging.info(f"Successfully created and connected to '{db_name}'.")

    # --- 1. Load and Insert Data from Pickle Files ---
    resources_path = "resources"
    pkl_files = glob.glob(os.path.join(resources_path, 'db_*.pkl')) # Process only db files
    
    if not pkl_files:
        logging.warning(f"No endgame database .pkl files found in '{resources_path}'.")
        conn.close()
        return

    logging.info(f"Found {len(pkl_files)} endgame .pkl files to process.")

    for pkl_file in pkl_files:
        table_name = os.path.splitext(os.path.basename(pkl_file))[0]
        logging.info(f"Processing '{pkl_file}' into table '{table_name}'...")
        
        try:
            with open(pkl_file, 'rb') as f:
                data = pickle.load(f)

            if not isinstance(data, dict) or not data:
                logging.warning(f"Skipping '{pkl_file}': Not a valid, non-empty dictionary.")
                continue
            
            # --- Dynamically Create a Specific Table for Each Endgame DB ---
            # Infer schema from the first key
            sample_key = next(iter(data.keys()))
            num_pieces = len(sample_key) - 1
            
            # Create a more structured table
            # e.g., p1_pos, p2_pos, p3_pos, turn, result
            pos_cols = ', '.join([f'p{i+1}_pos INTEGER' for i in range(num_pieces)])
            
            create_table_sql = f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    {pos_cols},
                    turn TEXT(1),
                    result INTEGER NOT NULL,
                    PRIMARY KEY ({', '.join([f'p{i+1}_pos' for i in range(num_pieces)])}, turn)
                )
            '''
            cursor.execute(create_table_sql)

            # --- Prepare data for insertion ---
            to_insert = []
            for key, val in data.items():
                # Key is a tuple like (sq1, sq2, ..., turn)
                row_data = key[:-1] + (key[-1], val) # Unpack piece positions, add turn and result
                to_insert.append(row_data)
            
            # Build the INSERT statement dynamically
            q_marks = ', '.join(['?' for _ in range(len(sample_key) + 1)])
            insert_sql = f'INSERT INTO {table_name} VALUES ({q_marks})'
            
            cursor.executemany(insert_sql, to_insert)
            logging.info(f"Inserted {len(to_insert)} records into '{table_name}'.")

        except Exception as e:
            logging.error(f"Failed to process '{pkl_file}': {e}")

    # --- 3. Commit changes and close ---
    conn.commit()
    conn.close()
    logging.info("Database creation complete. All changes have been saved.")

if __name__ == '__main__':
    create_database()
