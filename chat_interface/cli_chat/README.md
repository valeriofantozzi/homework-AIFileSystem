# 💬 cli_chat/ — Command-Line Chat for Your AI Agent 🖥️

Welcome to the **CLI Chat Interface**!  
This is where you can talk to your AI File System Agent right from your terminal—no browser required.  
Enjoy a rich, interactive, and developer-friendly chat experience. 🧑‍💻🤖

---

## What’s Inside? 📦

- **chat.py**: 💬 The main interactive chat loop (color, markdown, commands, debug mode)
- **demo_cli_features.py**: 🧪 Demo script showing off CLI features and session management
- **\_\_init\_\_.py**: 📦 Exports the CLIChat API

---

## Features & Highlights ✨

- **Rich Terminal UI**: Colorized output, markdown rendering, and panels via [rich]
- **Conversation History**: Persistent sessions—resume where you left off!
- **Debug Mode**: See the agent’s reasoning steps in real time
- **Command System**: `/help`, `/debug`, `/history`, `/clear`, `/workspace`, `/quit`
- **Safety First**: All requests are pre-screened by the supervisor before reaching the agent
- **Extensible**: Add new commands, UI features, or integrations easily

---

## Folder Structure 🗂️

| File                   | Purpose                                        |
| ---------------------- | ---------------------------------------------- |
| `chat.py`              | 💬 Main CLI chat interface implementation      |
| `demo_cli_features.py` | 🧪 Demo of CLI features and session management |
| `__init__.py`          | 📦 Exports the CLIChat API                     |

---

## Example Flow 🔗

1. User starts the chat: `poetry run python -m chat_interface.cli_chat.chat --workspace ./sandbox`
2. Greets with a rich welcome panel and available commands
3. User types a request (or a command like `/help`)
4. Supervisor checks for safety & intent
5. Agent responds, with reasoning steps shown in debug mode
6. Conversation is saved—resume anytime!

---

## Poetry Support 🐍

This project uses [Poetry](https://python-poetry.org/) for dependency management and running scripts.

- **Start the CLI chat:**  
  `poetry run python -m chat_interface.cli_chat.chat --workspace ./sandbox`

- **Run the demo:**  
  `poetry run python chat_interface/cli_chat/demo_cli_features.py`

Make sure to install dependencies with `poetry install` before running.

---

## Why Use This? 💡

- **Fast**: No browser, no lag—just instant terminal interaction
- **Transparent**: See exactly how your agent thinks and acts
- **Developer-Friendly**: Scriptable, hackable, and easy to extend
- **Safe**: Every request is moderated before execution

---

**Chat smart. Chat safe. Chat in style!** 😎🖥️
