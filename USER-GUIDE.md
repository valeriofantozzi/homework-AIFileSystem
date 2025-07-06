# 🧑‍💻 **AI File-System Agent – User Guide**

Welcome! This short guide shows you how to **install, run and interact** with the AI File-System Agent using **Poetry**.  
If you simply want to chat, skip to **Quick Start**. If you need MCP integration, see **MCP Clients**.

---

## 1. 🚀 Prerequisites

| Tool                    | Version    | Notes                                                 |
| ----------------------- | ---------- | ----------------------------------------------------- |
| **Python**              | 3.9 – 3.11 | Managed automatically by Poetry if `pyenv` is present |
| **Poetry**              | ≥ 1.7      | <https://python-poetry.org/docs/#installation>        |
| **Docker** _(optional)_ | 20.x+      | Only for container / compose usage                    |

---

## 2. 📦 Installation (Poetry)

```bash
# Clone the repo
git clone https://github.com/valeriofantozzi/homework-AIFileSystem
cd ai-filesystem-agent

# Install dependencies & create virtualenv
poetry install

# Activate the env
poetry shell
```

Poetry will:

1. Resolve versions from `pyproject.toml` / `poetry.lock`.
2. Create `.venv/` inside the project (or globally, per your config).
3. Install console entry-points (`chat-agent`, etc.).

---

### 2.5 🔧 Post-Install Environment Setup

```bash
# Generate a local env file from template (first time only)
poetry run python config/manage_env.py setup local

# Validate keys (will warn if OPENAI_API_KEY is missing)
poetry run python config/manage_env.py validate local

# List all env templates and existing files
poetry run python config/manage_env.py list
```

> **After installing dependencies, always create and validate your `.env` before running the agent.**

> **Tip:** run `poetry env info` to view / troubleshoot the venv path.

---

## 3. ⚡ Quick Start (CLI Chat)

```bash
poetry run python -m chat_interface.cli_chat.chat --workspace . --env development -debug
```

You’ll see a prompt similar to:

```
🤖  AI-FS ▸ How can I help?
```

Try:

```
list files
read tests/sandbox/docs/ml_project_overview.md
delete tests/sandbox/mixed/project_todos.txt
```

### CLI Shortcuts

| Command         | Effect             |
| --------------- | ------------------ |
| `help` / `?`    | Show built-in help |
| `clear`         | Clear screen       |
| `exit` / `quit` | End session        |

---

## 4. 🌐 Running the MCP Server

### Dev mode (local FastAPI)

```bash
poetry run python -m server.api_mcp.mcp_server
```

- Default port: **8000**
- Interactive OpenAPI docs: <http://localhost:8000/docs>

### Docker Compose

```bash
docker compose up --build
```

Containers:

| Name          | Purpose                      |
| ------------- | ---------------------------- |
| `mcp-agent`   | Agent + FastAPI              |
| `healthcheck` | Simple ping script for CI/CD |

---

## 5. 🖇️ Connecting MCP Clients

1. Copy `mcp_config.json` (root) **or** `server/config/claude_desktop_config.json`.
2. Follow the client’s “Add Context Provider” flow and select the file.
3. The client will reach `http://localhost:8000/mcp` (default).  
   Change `base_url` inside the JSON if you map a different port.

---

## 6. 🔧 Environment Variables

Create `.env` at project root **or** export vars in your shell.

| Var              | Default | Description                                  |
| ---------------- | ------- | -------------------------------------------- |
| `OPENAI_API_KEY` | —       | Key for GPT-4o (main model)                  |
| `GROQ_API_KEY`   | —       | Key for Llama-3 guard model                  |
| `AGENT_ROOT`     | `./`    | Base directory sandbox (should stay default) |
| `LOG_LEVEL`      | `INFO`  | Logging verbosity                            |

### 🛠️ Example `.env` setup

```bash
# Copy template or create a new .env file
cp config/ENV_SETUP.sample .env  # or touch .env

# Edit and add your keys
echo "OPENAI_API_KEY=sk-..." >> .env
echo "GROQ_API_KEY=groq-..." >> .env
```

The helper `config/manage_env.py` prints & validates required keys:

```bash
poetry run python -m config.manage_env
```

---

## 7. 🧪 Running Tests

```bash
pytest -q
```

Targets:

- CRUD operations
- Intelligent multi-tool queries
- CLI chat
- MCP integration

Coverage summary is printed on completion.

---

## 8. 🆘 Troubleshooting

| Issue                      | Fix                                                                        |
| -------------------------- | -------------------------------------------------------------------------- |
| **“No such tool”**         | Ensure you typed commands exactly; see `help`.                             |
| **Path outside workspace** | The agent blocks traversal – stay within repo.                             |
| **Port 8000 busy**         | Run `python -m server.api_mcp.mcp_server --port 8123` and update manifest. |
| **Docker build slow**      | Use `docker compose build --progress=plain` to watch caching.              |

Detailed logs are written to `logs/ai_fs_agent.log` with rotation.

---

## 9. 🛠️ Extending the Agent

1. Add a new package under `tools/your_new_tool/`.
2. Expose methods decorated with `@tool` (see `workspace_fs/fs_tools.py`).
3. Register metadata in `agent/core/advanced_tools_metadata.py`.
4. Write tests in `tools/your_new_tool/tests/`.
5. Run `pytest` and `bandit -r .` to verify.

---

## 10. 📜 License & Credits

MIT © 2025 <your-name>  
Built with ❤️, Clean Architecture, and **Poetry**.
