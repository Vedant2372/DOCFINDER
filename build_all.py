import subprocess
import shutil
import os

# Paths
flask_dir = r"C:\Users\Admin\Desktop\doc_finder\connection"
frontend_dir = r"C:\Users\Admin\Desktop\doc_finder\frontend"
exe_name = "backend_server.exe"

# Step 1: Build backend
subprocess.run("pyinstaller --noconfirm --onefile --name backend_server app.py", shell=True, cwd=flask_dir)

# Step 2: Copy to Electron folder
shutil.copy(os.path.join(flask_dir, "dist", exe_name), os.path.join(frontend_dir, "backend", exe_name))

# Step 3: Package Electron app
subprocess.run("electron-packager . doc-finder --platform=win32 --arch=x64", shell=True, cwd=frontend_dir)
