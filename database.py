import sqlite3
import os
import json
from pathlib import Path

# Create a data directory if it doesn't exist
DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)

# Database path
DB_PATH = DATA_DIR / 'anti_playlist.db'

def init_db():
    """Initialize database tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create history table
    c.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY,
        user_id TEXT NOT NULL,
        platform TEXT NOT NULL,
        song_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, platform, song_id)
    )
    ''')
    
    conn.commit()
    conn.close()

def save_history(user_id, platform, song_ids):
    """Save new song IDs to history"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Prepare data for batch insert
    data = [(user_id, platform, song_id) for song_id in song_ids]
    
    # Insert or ignore (to handle duplicates)
    c.executemany('''
    INSERT OR IGNORE INTO history (user_id, platform, song_id)
    VALUES (?, ?, ?)
    ''', data)
    
    conn.commit()
    conn.close()

def load_history(user_id, platform):
    """Load all song IDs for a user/platform from history"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
    SELECT song_id FROM history
    WHERE user_id = ? AND platform = ?
    ''', (user_id, platform))
    
    # Extract song IDs and return as a set
    results = c.fetchall()
    conn.close()
    
    return set(row[0] for row in results)
