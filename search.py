import faiss
import pickle
import sqlite3
import numpy as np
import os
import datetime  # ✅ for date formatting

# ✅ Database & index paths
DB_PATH = "Aaryan_database.db"
INDEX_PATH = "Aaryan_store/index.faiss"
META_PATH = "Aaryan_store/meta.pkl"

def search_documents(query: str, embedder, top_k=5):
    query_lower = query.strip().lower()
    results = []

    # 1️⃣ Exact filename match from SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filename, path, modified, extension
            FROM documents
            WHERE lower(filename) LIKE ?
            ORDER BY modified DESC
            LIMIT ?
        """, (f"%{query_lower}%", top_k))
        exact_matches = cursor.fetchall()
        conn.close()

        for row in exact_matches:
            try:
                mod_readable = datetime.datetime.fromtimestamp(row[2]).strftime("%d-%b-%Y %H:%M")
            except Exception:
                mod_readable = ""
            extension = row[3] if row[3] else "unknown"

            results.append({
                "filename": row[0],
                "path": row[1],
                "modified": mod_readable,
                "extension": extension,
                "source": "filename match"
            })

        # 2️⃣ Return early if exact matches found
        if results:
            return results

    except Exception as e:
        print("❌ SQLite filename match failed:", str(e))

    # 3️⃣ Semantic match using FAISS
    try:
        query_embedding = embedder.embed_texts([query])
        faiss.normalize_L2(query_embedding)

        index = faiss.read_index(INDEX_PATH)
        with open(META_PATH, "rb") as f:
            all_paths = pickle.load(f)

        D, I = index.search(query_embedding, top_k)

        for idx in I[0]:
            if idx < len(all_paths):
                path = all_paths[idx]
                try:
                    mod_time = os.path.getmtime(path)
                    mod_readable = datetime.datetime.fromtimestamp(mod_time).strftime("%d-%b-%Y %H:%M")
                except Exception:
                    mod_readable = ""

                # ✅ Clean extension extraction
                ext = os.path.splitext(path)[1].lower()
                extension = ext if ext else "unknown"

                results.append({
                    "filename": os.path.basename(path),
                    "path": path,
                    "modified": mod_readable,
                    "extension": extension,
                    "source": "semantic match"
                })

        return results

    except Exception as e:
        print("❌ Semantic search failed:", str(e))
        return []
