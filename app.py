from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, pickle, threading, logging, platform, subprocess, sys
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from embedder import Embedder
from search import search_documents
from db import init_db, insert_documents, get_all_doc_stats, upsert_document, delete_document
from api import index_documents, scan_files
from reader import read_file_content

sys.stdout.reconfigure(encoding='utf-8')

if getattr(sys, 'frozen', False):
    APP_ROOT = sys._MEIPASS
else:
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))

INDEX_PATH = os.path.join(APP_ROOT, "Aaryan_store", "index.faiss")
META_PATH = os.path.join(APP_ROOT, "Aaryan_store", "meta.pkl")
STATE_FILE = os.path.join(APP_ROOT, "config_state.json")
LOG_FILE = os.path.join(APP_ROOT, "document_finder.log")

AARYAN_DIR = os.path.join(APP_ROOT, "Aaryan_store")
os.makedirs(AARYAN_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app = Flask(__name__)
CORS(app)

WATCH_ROOTS = ["C:\\", "D:\\"]
VALID_EXTS = {".txt", ".pdf", ".docx", ".xlsx", ".xls", ".db", ".js", ".py", ".java", ".cpp", ".c", ".jpg", ".jpeg", ".png", ".bmp", ".webp"}
EXCLUDED_DIRS = {"windows", "program files", "programdata", ".git", ".venv", "appdata", "system volume information", "$recycle.bin", "node_modules", "_pycache_", ".idea", ".vscode", "site-packages", "lib", "dist", "build", ".mypy_cache"}

embedder = Embedder()
STATE_LOCK = threading.Lock()
STATE = {"termsAccepted": False, "firstTime": True, "job": {"status": "idle", "step": "", "startedAt": None, "endedAt": None, "error": None, "indexed": 0}}

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                STATE.update(json.load(f))
        except Exception as e:
            logging.exception("Error loading state")

def save_state():
    with STATE_LOCK:
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({"termsAccepted": STATE["termsAccepted"], "firstTime": STATE["firstTime"]}, f, indent=2)
        except Exception as e:
            logging.exception("Error saving state")

load_state()

def set_job(status, step="", error=None, indexed=0):
    with STATE_LOCK:
        STATE["job"].update({"status": status, "step": step, "error": error, "indexed": indexed})
        now = datetime.now().isoformat(timespec="seconds")
        if status == "running":
            STATE["job"]["startedAt"] = now
            STATE["job"]["endedAt"] = None
        elif status in ("done", "error"):
            STATE["job"]["endedAt"] = now
    logging.info(f"Job {status}: {step} (indexed={indexed}) error={error}")

def _allowed_file(path):
    path_lower = path.lower()
    if not any(path_lower.endswith(ext) for ext in VALID_EXTS): return False
    parts = path_lower.split(os.sep)
    return not any(ex in parts for ex in EXCLUDED_DIRS)

def _stat_walk(roots):
    out = {}
    for root in roots:
        if not os.path.exists(root): continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not any(ex in os.path.join(dirpath, d).lower() for ex in EXCLUDED_DIRS)]
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if not _allowed_file(file_path): continue
                try:
                    stat = os.stat(file_path)
                    out[file_path] = (stat.st_size, stat.st_mtime)
                except (FileNotFoundError, PermissionError): continue
    return out

def _build_docs_for_paths(paths):
    docs = {}
    for path in paths:
        if not os.path.exists(path) or not _allowed_file(path):
            continue
        try:
            logging.info(f"🔍 Processing: {path}")
            stat = os.stat(path)
            content = read_file_content(path) or os.path.basename(path)
            docs[path] = {
                "filename": os.path.basename(path),
                "path": path,
                "extension": os.path.splitext(path)[1].lower(),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "content": content
            }
        except Exception as e:
            logging.warning(f"⚠️ Skipped file due to error: {e} at path: {path}")
    return docs

def run_full_scan_bg():
    try:
        set_job("running", "init-db")
        init_db()
        set_job("running", "scan-files")
        docs = scan_files()
        if not docs:
            set_job("done", "scan-files", indexed=0)
            return
        set_job("running", "insert-db")
        inserted = insert_documents(docs)
        set_job("running", "index-faiss")
        index_documents(docs)
        STATE["firstTime"] = False
        save_state()
        set_job("done", "complete", indexed=inserted)
        threading.Thread(target=start_file_watcher, daemon=True).start()
    except Exception as e:
        logging.exception("🔴 Full scan crashed")
        set_job("error", "full-scan", error=str(e))

def run_smart_rescan_bg():
    try:
        set_job("running", "compute-changes")
        db_stats = get_all_doc_stats()
        fs_stats = _stat_walk(WATCH_ROOTS)

        new_paths = [p for p in fs_stats if p not in db_stats]
        modified_paths = [p for p, (size, mtime) in fs_stats.items() if p in db_stats and db_stats[p] != (size, mtime)]
        deleted_paths = [p for p in db_stats if p not in fs_stats]

        set_job("running", f"apply-deletes({len(deleted_paths)})")
        for path in deleted_paths:
            delete_document(path)

        current_paths = ((set(db_stats) - set(deleted_paths)) | set(new_paths) | set(modified_paths))

        set_job("running", f"build-docs({len(current_paths)})")
        docs = _build_docs_for_paths(current_paths)

        set_job("running", "update-db")
        for path, meta in docs.items():
            upsert_document(path, meta["filename"], meta["extension"], meta["size"], meta["modified"], content=meta.get("content", ""))

        set_job("running", f"index-faiss({len(docs)})")
        index_documents(docs)
        set_job("done", "smart-rescan", indexed=len(docs))
    except Exception as e:
        logging.exception("🔴 Smart rescan failed")
        set_job("error", "smart-rescan", error=str(e))

def start_file_watcher():
    try:
        from file_watcher import start_file_watch
        logging.info("🔁 Starting background file watcher...")
        threading.Thread(target=start_file_watch, daemon=True).start()
    except Exception as e:
        logging.exception("File watcher failed")

def start_initial_file_watcher_if_needed():
    if STATE["termsAccepted"] and os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
        start_file_watcher()

@app.route("/task", methods=["POST", "OPTIONS"])
def task():
    if request.method == "OPTIONS": return ("", 204)
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip().lower()
    logging.info(f"📩 Task: {action}")

    if action == "accept":
        STATE["termsAccepted"] = True
        save_state()
        if STATE["firstTime"] or not (os.path.exists(INDEX_PATH) and os.path.exists(META_PATH)):
            threading.Thread(target=run_full_scan_bg, daemon=True).start()
            return jsonify({"ok": True, "message": "Full scan started"})
        start_file_watcher()
        return jsonify({"ok": True, "message": "Index already exists"})

    elif action == "search":
        if not STATE["termsAccepted"]:
            return jsonify({"ok": False, "error": "Terms not accepted"}), 403
        query = (data.get("q") or "").strip()
        if not query:
            return jsonify({"ok": False, "error": "No query provided"}), 400
        try:
            results = search_documents(query, embedder)
            return jsonify({"ok": True, "results": results})
        except Exception as e:
            logging.exception("Search failed")
            return jsonify({"ok": False, "error": str(e)}), 500

    elif action == "smart-rescan":
        if not STATE["termsAccepted"]:
            return jsonify({"ok": False, "error": "Terms not accepted"}), 403
        if STATE["job"]["status"] == "running":
            return jsonify({"ok": False, "message": "Another job running"}), 409
        threading.Thread(target=run_smart_rescan_bg, daemon=True).start()
        return jsonify({"ok": True, "message": "Smart rescan started"})

    elif action == "status":
        return jsonify({"ok": True, **STATE, "indexExists": os.path.exists(INDEX_PATH) and os.path.exists(META_PATH)})

    return jsonify({"ok": False, "error": f"Unknown action: {action}"}), 400


# ————— NEW API —————
@app.route("/count_files", methods=["POST"])
def count_files():
    folder_paths = {
        "Documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "Downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "Desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
        "C Drive": "C:\\",
        "D Drive": "D:\\",
        "Pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
        "Others": os.path.join(os.path.expanduser("~"), "AppData\\Local\\Temp")
    }

    def count_files_in_folder(path):
        count = 0
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not any(ex in os.path.join(root, d).lower() for ex in EXCLUDED_DIRS)]
                for f in files:
                    full_path = os.path.join(root, f)
                    if _allowed_file(full_path):
                        count += 1
        except Exception as e:
            logging.warning(f"⚠ Error walking {path}: {e}")
        return count

    results = {name: count_files_in_folder(path) for name, path in folder_paths.items()}
    return jsonify(results)


@app.route("/openfile", methods=["POST"])
def open_file():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    if not path or not os.path.exists(path):
        return jsonify({"ok": False, "error": "Invalid or missing file path"}), 400

    # Optional: Validate file is indexed
    stats = get_all_doc_stats()
    if path not in stats:
        return jsonify({"ok": False, "error": "File not indexed"}), 400

    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", path])
        else:  # Linux and others
            subprocess.Popen(["xdg-open", path])
        return jsonify({"ok": True, "message": f"Opening {path}"})
    except Exception as e:
        logging.exception("Failed to open file")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/", methods=["GET"])
def root():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == "__main__":
    print(f"\n🚀 Starting Document Finder at {datetime.now().isoformat(timespec='seconds')}")
    print("🚀 Listening on http://127.0.0.1:5005")
    logging.info("Application started")

    db_path = os.path.join(APP_ROOT, "doc_index.db")
    if not os.path.exists(db_path):
        logging.info("🔧 Creating missing database at startup...")
        init_db()

    if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
        logging.info("⚠ FAISS index or meta missing. Rebuilding...")
        threading.Thread(target=run_full_scan_bg, daemon=True).start()

    start_initial_file_watcher_if_needed()
    app.run(port=5005)
