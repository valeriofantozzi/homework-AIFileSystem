# 📦 Client-Delivery Checklist

Run through this list **before** zipping / pushing the repository to the customer.

| ✔️  | Category               | Action                                                               | Path / Command                                                                      |
| --- | ---------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| ☐   | **Secrets**            | Delete every real `.env.*` file (keep only templates)                | `rm -f config/.env.*`                                                               |
| ☐   |                        | Search for hard-coded API keys or tokens                             | `grep -R --line-number "sk-" .`                                                     |
| ☐   | **Logs & Diagnostics** | Purge runtime logs and diagnostics exports                           | `rm -rf logs/`                                                                      |
| ☐   | **Sandbox Data**       | Remove test datasets and example files                               | `rm -rf tests/sandbox/`                                                             |
| ☐   | **Internal Docs**      | Remove planning / troubleshooting drafts                             | `rm -rf DOCS/planning DOCS/troubleshooting.md DOCS/clear-command-implementation.md` |
| ☐   | **Lock Files**         | Delete poetry.lock inside example sub-packages                       | `find tools -name "poetry.lock" -delete`                                            |
| ☐   | **Caches**             | Remove pycache, pytest cache, coverage artefacts                     | `find . -name "__pycache__" -or -name ".pytest_cache" -exec rm -rf {} +`            |
| ☐   | **Docker Dev Stuff**   | Review/strip local volume mounts or credentials                      | Edit `server/docker/docker-compose.yml`                                             |
| ☐   | **.gitignore**         | Ensure the above patterns are ignored going forward                  | Update `.gitignore` if needed                                                       |
| ☐   | **Tests (Optional)**   | Keep unit tests or remove if not shipping QA                         | `rm -rf tests/` **or** keep if agreed                                               |
| ☐   | **Verify Build**       | Fresh clone → `poetry install && poetry run pytest` passes           |
| ☐   | **Tag Release**        | `git tag v1.0-client-release && git push origin v1.0-client-release` |

---

### Quick One-liner (UNIX)

```bash
poetry run python - <<'PY'
import os, shutil, subprocess, pathlib as p
trash = [
    "logs", "tests/sandbox", "DOCS/planning", "DOCS/troubleshooting.md",
    "DOCS/clear-command-implementation.md"
]
for t in trash:
    path = p.Path(t)
    if path.exists():
        shutil.rmtree(path) if path.is_dir() else path.unlink()
# delete env files
for f in p.Path("config").glob(".env.*"):
    f.unlink()
# delete sub-package lock files
for f in p.Path("tools").rglob("poetry.lock"):
    f.unlink()
print("Cleanup done")
PY
```

> ⚠️ **Review before running**: adapt paths to match customer expectations.

---

Deliver only:

- `agent/`, `tools/`, `server/`, `chat_interface/`
- `README.md`, `USER-GUIDE.md`, `agent/ARCHITECTURE.md`
- `pyproject.toml`, `poetry.lock`, `mcp_config.json`
- `config/` **without** real .env files
- (Optional) `tests/` if the client wants automated QA.

Everything else should stay internal. ✔️
