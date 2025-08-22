# scanner_fast.py
import os
from db import get_all_doc_stats

EXCLUDE_DIRS = {"windows","program files","programdata","appdata",
                ".git",".venv","__pycache__","node_modules","system volume information"}
VALID_EXTS = {".txt",".pdf",".docx",".xlsx",".xls",".py",".java",".c",".cpp",".jpg",".jpeg",".png",".db"}

def allowed(path):
    p = path.lower()
    if not any(ext in p for ext in VALID_EXTS):
        return False
    return not any(ex in p for ex in EXCLUDE_DIRS)

def stat_walk(roots):
    result = {}
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            # prune excluded dirs
            dirnames[:] = [d for d in dirnames if all(ex not in d.lower() for ex in EXCLUDE_DIRS)]
            for f in filenames:
                path = os.path.join(dirpath, f)
                if not allowed(path): 
                    continue
                try:
                    st = os.stat(path)
                    result[path] = (st.st_size, st.st_mtime)
                except FileNotFoundError:
                    continue
    return result

def compute_changes(roots):
    db_stats = get_all_doc_stats()    # {path: (size, mtime)}
    fs_stats = stat_walk(roots)

    new_files = [p for p in fs_stats if p not in db_stats]
    modified_files = [p for p,stat in fs_stats.items() if p in db_stats and db_stats[p] != stat]
    deleted_files = [p for p in db_stats if p not in fs_stats]

    return new_files, modified_files, deleted_files, fs_stats