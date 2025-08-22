import sqlite3
import os

DB_PATH = "Aaryan_database.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                path TEXT UNIQUE,
                extension TEXT,
                size INTEGER,
                modified REAL
            )
        ''')
        conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                filename, path, content
            )
        ''')

def insert_documents(docs: dict):
    with sqlite3.connect(DB_PATH) as conn:
        inserted = 0
        for path, meta in docs.items():
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO documents
                    (filename, path, extension, size, modified)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    meta["filename"], path,
                    meta["extension"], meta["size"], meta["modified"]
                ))
                conn.execute('''
                    INSERT INTO documents_fts (filename, path, content)
                    VALUES (?, ?, ?)
                ''', (
                    meta["filename"], path, meta.get("content", "")
                ))
                inserted += 1
            except Exception as e:
                print(f"[DB ERROR] {e}")
        conn.commit()
    return inserted

# ✅ Helper to get extension (filetype) from DB using path
def get_filetype_by_path(path):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT extension FROM documents WHERE path = ?", (path,))
            row = cursor.fetchone()
            return row[0] if row else "Unknown"
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch filetype for {path}: {e}")
        return "Unknown"

# ---------- NEW HELPERS FOR SMART RESCAN ----------

def get_all_doc_stats():
    """Return {path: (size, modified)} from the documents table."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT path, size, modified FROM documents")
        return {row[0]: (row[1], row[2]) for row in cur.fetchall()}

def upsert_document(path, filename, ext, size, modified, content=None):
    """Insert or update a single document row (+ FTS if content provided)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO documents (filename, path, extension, size, modified)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                filename=excluded.filename,
                extension=excluded.extension,
                size=excluded.size,
                modified=excluded.modified
        """, (filename, path, ext, size, modified))
        if content is not None:
            # Replace FTS content for this path (delete then insert)
            conn.execute("DELETE FROM documents_fts WHERE path = ?", (path,))
            conn.execute("""
                INSERT INTO documents_fts (filename, path, content)
                VALUES (?, ?, ?)
            """, (filename, path, content))
        conn.commit()

def delete_document(path):
    """Delete a document and its FTS row by exact path."""
    with sqlite3.connect(DB_PATH) as conn:
        # Delete FTS first (no ON DELETE CASCADE on virtual table)
        conn.execute("DELETE FROM documents_fts WHERE path = ?", (path,))
        conn.execute("DELETE FROM documents WHERE path = ?", (path,))
        conn.commit()