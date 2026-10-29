"""Create a source download without environments, secrets, generated archives or Git."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent.parent
excluded = {".git", ".venv", ".runtime", "__pycache__", ".pytest_cache", "artifacts"}
output = root / "web/starter.zip"
with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    for file in sorted(root.rglob("*")):
        rel = file.relative_to(root)
        if not file.is_file() or excluded.intersection(rel.parts) or file == output:
            continue
        if file.name == ".env" or file.name.startswith(".env.") and file.name != ".env.example":
            continue
        if file.suffix in {".pyc", ".zip"} or file.name == ".DS_Store":
            continue
        archive.write(file, Path("rag-field-guide") / rel)
print(f"Created {output} ({output.stat().st_size:,} bytes)")
