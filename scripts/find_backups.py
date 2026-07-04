import os

gemini_dir = r"C:\Users\Imhussnain\.gemini"
workspace_dir = r"d:\2026-15MAY\ML-project"

print("Searching for files containing Topbar...")

# Search in workspace
for root, dirs, files in os.walk(workspace_dir):
    for file in files:
        if "topbar" in file.lower():
            path = os.path.join(root, file)
            print(f"Workspace: {path} ({os.path.getsize(path)} bytes)")

# Search in gemini dir
for root, dirs, files in os.walk(gemini_dir):
    for file in files:
        if "topbar" in file.lower() or "backup" in file.lower():
            path = os.path.join(root, file)
            print(f"Gemini: {path} ({os.path.getsize(path)} bytes)")
