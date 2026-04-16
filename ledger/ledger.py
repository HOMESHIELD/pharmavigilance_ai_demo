import sqlite3
import json
import os
import datetime

# ── Database path ──
LEDGER_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.db")

def _get_connection():
    """
    Opens a SQLite connection with WAL mode enabled.
    WAL = Write-Ahead Logging — allows reads and writes 
    simultaneously without blocking, and survives crashes.
    """
    conn = sqlite3.connect(LEDGER_DB)
    conn.row_factory = sqlite3.Row  # returns dict-like rows
    
    # ── Enable WAL mode — the key enterprise feature ──
    conn.execute("PRAGMA journal_mode=WAL;")
    
    # ── Create table if it doesn't exist ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            post_id     TEXT NOT NULL,
            node        TEXT NOT NULL,
            data        TEXT NOT NULL  -- JSON string
        )
    """)
    
    # ── Index for fast lookups by post_id + node ──
    conn.execute("""
        CREATE INDEX IF NOT EXISTS 
        idx_post_node ON ledger(post_id, node)
    """)
    
    conn.commit()
    return conn

def write_entry(post_id, node_name, data):
    """
    Appends a new entry to the ledger.
    Append-only — entries are NEVER updated or deleted.
    This is the Immutable Ledger guarantee.
    """
    conn = _get_connection()
    try:
        conn.execute("""
            INSERT INTO ledger (timestamp, post_id, node, data)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.datetime.now().isoformat(),
            post_id,
            node_name,
            json.dumps(data, ensure_ascii=False)
        ))
        conn.commit()
        print(f"  [LEDGER] Saved → post: {post_id} | node: {node_name}")
    finally:
        conn.close()

def get_completed_node(post_id, node_name):
    """
    Checks if a specific node already completed for a post.
    This is how crash recovery works — skip already done work.
    """
    conn = _get_connection()
    try:
        cursor = conn.execute("""
            SELECT data FROM ledger
            WHERE post_id = ? AND node = ?
            LIMIT 1
        """, (post_id, node_name))
        row = cursor.fetchone()
        if row:
            return json.loads(row["data"])
        return None
    finally:
        conn.close()

def clear_ledger():
    """
    Wipes all entries for a fresh run.
    Only call this manually between demo runs.
    """
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM ledger")
        conn.commit()
        print("  [LEDGER] Cleared. (SQLite WAL mode)")
    finally:
        conn.close()

def print_ledger():
    """Prints the full ledger — useful for debugging."""
    conn = _get_connection()
    try:
        cursor = conn.execute("""
            SELECT timestamp, post_id, node, data 
            FROM ledger 
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()
        print("\n===== FULL LEDGER (SQLite WAL) =====")
        for row in rows:
            data = json.loads(row["data"])
            print(f"\n  [{row['timestamp']}]")
            print(f"  Post: {row['post_id']} | Node: {row['node']}")
            print(f"  Data: {json.dumps(data, indent=4, ensure_ascii=False)}")
        print("=====================================\n")
    finally:
        conn.close()

def read_ledger_as_list():
    """
    Returns all ledger entries as a list of dicts.
    Used by the Express server to read ledger data.
    """
    conn = _get_connection()
    try:
        cursor = conn.execute("""
            SELECT timestamp, post_id, node, data
            FROM ledger
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "timestamp": row["timestamp"],
                "post_id":   row["post_id"],
                "node":      row["node"],
                "data":      json.loads(row["data"])
            })
        return result
    finally:
        conn.close()