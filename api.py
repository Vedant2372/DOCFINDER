import os
import pickle
from embedder import Embedder
from reader import read_file_content

from db import insert_documents
import faiss

# 🔍 Configuration
SCAN_DIRS = ["C:\\", "D:\\"]
VALID_EXTS = [
    ".txt", ".pdf", ".docx", ".xlsx", ".xls", ".db",
    ".js", ".py", ".java", ".cpp", ".c",
    ".jpg", ".jpeg", ".png", ".bmp", ".webp"
]
EXCLUDED_DIRS = [
    "windows", "program files", "programdata", ".git", ".venv",
    "appdata", "system volume information", "$recycle.bin",
    "node_modules", "__pycache__", ".idea", ".vscode",
    "site-packages", "lib", "dist", "build", ".mypy_cache"
]

INDEX_PATH = "Aaryan_store/index.faiss"
META_PATH = "Aaryan_store/meta.pkl"

embedder = Embedder()

# ✅ Check if a path should be excluded
def should_exclude(path):
    return any(excl.lower() in path.lower() for excl in EXCLUDED_DIRS)

# ✅ Get category based on folder name
def get_folder_category(path):
    parts = path.lower().split(os.sep)
    for folder in ["downloads", "documents", "desktop", "pictures", "videos", "music"]:
        if folder in parts:
            return folder.capitalize()
    return "Other"

# ✅ Scan files recursively from SCAN_DIRS
def scan_files():
    files = {}
    folder_counts = {}
    drive_counts = {}

    for root in SCAN_DIRS:
        drive_counts[root] = 0
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not should_exclude(os.path.join(dirpath, d))]
            for file in filenames:
                path = os.path.join(dirpath, file)
                ext = os.path.splitext(file)[1].lower()
                if ext in VALID_EXTS and os.path.exists(path):
                    try:
                        content = read_file_content(path)
                        files[path] = {
                            "filename": file,
                            "path": path,
                            "extension": ext,
                            "size": os.path.getsize(path),
                            "modified": os.path.getmtime(path),
                            "content": content
                        }

                        # Folder count
                        category = get_folder_category(path)
                        folder_counts[category] = folder_counts.get(category, 0) + 1

                        # Drive count
                        drive_counts[root] += 1
                    except:
                        continue

    return files

# ✅ Create and save FAISS index
def index_documents(documents: dict):
    texts = [v["content"] if v["content"] else v["filename"] for v in documents.values()]
    paths = list(documents.keys())

    vectors = embedder.embed_texts(texts)
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "wb") as f:
        pickle.dump(paths, f)
