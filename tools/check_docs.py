"""Check authored Markdown links, fences, Python syntax, JSON and Compose wiring.

Run from any directory. This validates repository consistency, not a running server.
"""

import ast
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
markdown = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), ROOT / "examples/README.md"]
errors = []
for path in markdown:
    content = path.read_text(encoding="utf-8")
    fence = None
    prose = []
    for number, line in enumerate(content.splitlines(), start=1):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        elif fence is None:
            prose.append(line)
    if fence:
        errors.append(f"{path.relative_to(ROOT)}: unclosed code fence")
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", "\n".join(prose)):
        target = target.strip().split(' "', 1)[0].strip("<>")
        parts = urlsplit(target)
        if parts.scheme or target.startswith("#"):
            continue
        local = (path.parent / unquote(parts.path)).resolve()
        if not local.is_relative_to(ROOT) or not local.exists():
            errors.append(f"{path.relative_to(ROOT)}: broken local link {target}")

python_files = []
for folder in ("examples", "tests", "tools"):
    python_files.extend((ROOT / folder).rglob("*.py"))
for path in python_files:
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
for path in (ROOT / "examples/data").glob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))

compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
services = compose["services"]
assert services["standalone"]["image"] == "milvusdb/milvus:v3.0.1"
assert services["attu"]["environment"]["MILVUS_ADDRESS"] == "standalone:19530"
assert services["attu"]["profiles"] == ["ui"]
assert not services["etcd"].get("ports") and not services["minio"].get("ports")
for service in services.values():
    assert all(port.startswith("127.0.0.1:") for port in service.get("ports", []))
    for mount in service.get("volumes", []):
        assert mount.split(":", 1)[0] in compose["volumes"]

figures = sorted((ROOT / "assets/images").glob("*.png"))
assert len(figures) == 5
for path in figures:
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
if errors:
    raise SystemExit("\n".join(errors))
print(f"PASS: {len(markdown)} Markdown files, {len(figures)} figures, {len(python_files)} Python files, JSON and Compose wiring.")
print("This is a static check. Docker integration and model quality require separate runs.")
