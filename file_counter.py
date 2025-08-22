from flask import Flask, jsonify
import os

app = Flask(__name__)

# 📁 Define key folders to scan
FOLDER_PATHS = {
    "Documents": os.path.join(os.path.expanduser("~"), "Documents"),
    "Downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
    "Desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
    "C Drive": "C:\\",
    "D Drive": "D:\\",
    "Pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
    "Others": os.path.join(os.path.expanduser("~"), "AppData\\Local\\Temp")
}

# 🔢 Count files in a folder (including all subfolders)
def count_files_in_folder(path):
    count = 0
    try:
        for root, dirs, files in os.walk(path):  # <-- recursive scan
            count += len(files)
    except Exception as e:
        print(f"⚠ Error accessing {path}: {e}")
    return count

# 🌐 API endpoint to return file counts
@app.route("/count_files", methods=["POST"])
def count_files():
    results = {}
    for folder, path in FOLDER_PATHS.items():
        if os.path.exists(path):
            results[folder] = count_files_in_folder(path)
        else:
            results[folder] = 0
    return jsonify(results)

if __name__ == "__main__":
    app.run(port=5005, debug=True)
