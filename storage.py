import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the SQLite schema if it doesn't already exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table for storing main execution metrics (QoS, errors, dates)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        passed INTEGER NOT NULL,
        failed INTEGER NOT NULL,
        error_rate REAL NOT NULL,
        latency_avg REAL NOT NULL,
        latency_p95 REAL NOT NULL,
        availability REAL NOT NULL
    )
    """)
    
    # Table for storing detailed logs of individual test cases
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        latency_ms REAL NOT NULL,
        details TEXT,
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
    )
    """)
    
    # Table for storing structural metadata of artworks verified in the run (WOW factor component)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tested_artworks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL,
        artwork_id INTEGER NOT NULL,
        title TEXT,
        artist TEXT,
        image_url TEXT,
        is_public INTEGER,
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

def save_run(run_data):
    """
    Saves a complete execution payload in a strict atomic transaction.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert run overview
        cursor.execute("""
        INSERT INTO runs (timestamp, passed, failed, error_rate, latency_avg, latency_p95, availability)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            run_data["timestamp"],
            run_data["summary"]["passed"],
            run_data["summary"]["failed"],
            run_data["summary"]["error_rate"],
            run_data["summary"]["latency_ms_avg"],
            run_data["summary"]["latency_ms_p95"],
            run_data["summary"]["availability"]
        ))
        
        run_id = cursor.lastrowid
        
        # Insert test assertions results
        for test in run_data["tests"]:
            cursor.execute("""
            INSERT INTO test_details (run_id, name, status, latency_ms, details)
            VALUES (?, ?, ?, ?, ?)
            """, (
                run_id,
                test["name"],
                test["status"],
                test["latency_ms"],
                test["details"]
            ))
            
        # Insert artworks captured during functional list check
        for art in run_data.get("artworks", []):
            cursor.execute("""
            INSERT INTO tested_artworks (run_id, artwork_id, title, artist, image_url, is_public)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                art["artwork_id"],
                art["title"],
                art["artist"],
                art["image_url"],
                art["is_public"]
            ))
            
        conn.commit()
        return run_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def list_runs(limit=10):
    """
    Queries historical runs summaries.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM runs ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_latest_run():
    """
    Fetches the last run completed along with its assertions and featured gallery artworks.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1")
    run_row = cursor.fetchone()
    
    if not run_row:
        conn.close()
        return None
        
    run = dict(run_row)
    run_id = run["id"]
    
    cursor.execute("SELECT * FROM test_details WHERE run_id = ? ORDER BY id ASC", (run_id,))
    test_rows = cursor.fetchall()
    run["tests"] = [dict(row) for row in test_rows]
    
    cursor.execute("SELECT * FROM tested_artworks WHERE run_id = ? ORDER BY id ASC", (run_id,))
    art_rows = cursor.fetchall()
    run["artworks"] = [dict(row) for row in art_rows]
    
    conn.close()
    return run

def get_run_by_id(run_id):
    """
    Retrieves details of any specific past run by its unique identifier.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    run_row = cursor.fetchone()
    
    if not run_row:
        conn.close()
        return None
        
    run = dict(run_row)
    
    cursor.execute("SELECT * FROM test_details WHERE run_id = ? ORDER BY id ASC", (run_id,))
    test_rows = cursor.fetchall()
    run["tests"] = [dict(row) for row in test_rows]
    
    cursor.execute("SELECT * FROM tested_artworks WHERE run_id = ? ORDER BY id ASC", (run_id,))
    art_rows = cursor.fetchall()
    run["artworks"] = [dict(row) for row in art_rows]
    
    conn.close()
    return run
