import os
import zipfile

# Корень проекта
project_root = os.path.abspath(".")
output_zip = os.path.join(project_root, "userbssapi_cleaned.zip")

# Исключаемые папки и расширения
exclude_dirs = {'.venv', '__pycache__', '.secrets', '.vscode', 'venv'}
exclude_extensions = {'.pyc', '.log'}

with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for foldername, subfolders, filenames in os.walk(project_root):
        # Исключить директории
        subfolders[:] = [d for d in subfolders if d not in exclude_dirs]

        for filename in filenames:
            if any(filename.endswith(ext) for ext in exclude_extensions):
                continue

            file_path = os.path.join(foldername, filename)
            arcname = os.path.relpath(file_path, project_root)
            zipf.write(file_path, arcname)

print(f"\n✅ Архив успешно создан: {output_zip}")
