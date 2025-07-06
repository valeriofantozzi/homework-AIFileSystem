# 🧠 memory_tools — Conversation Memory for AI Agents 💾

Welcome to **memory_tools**!  
This package gives your AI agent a brain—persistent, context-aware memory for smarter, more natural conversations.  
If you want your agent to remember, reason, and adapt across sessions, you’re in the right place. 🦾🧠

---

## What’s Inside? 📦

- **src/memory_tools.py**: 🧩 Core logic for conversation memory, context, and memory management
- **\_\_init\_\_.py**: 📦 Exports the public API (ConversationMemory, MemoryManager, etc.)

---

## Key Features & Principles ✨

- **Session Memory**: Store and retrieve conversation history for each user/session
- **Context Management**: Maintain relevant context for multi-turn reasoning
- **High Cohesion, Low Coupling**: Each class/module has a single, clear responsibility
- **Extensible**: Add new memory strategies or storage backends easily
- **Error Handling**: Custom exceptions for robust, predictable behavior

---

## Usage Example 🧑‍💻

```python
from memory_tools import ConversationMemory, MemoryManager

# Create a memory manager
manager = MemoryManager()

# Start a new conversation
conv = manager.start_conversation(user_id="user-123")

# Add messages
conv.add_message(role="user", content="Hello, agent!")
conv.add_message(role="agent", content="Hi! How can I help?")

# Retrieve history
history = conv.get_history()
print(history)
```

---

## Integration & Extensibility 🔗

- **Plug & Play**: Designed for easy integration with any agent or chat system
- **Custom Storage**: Swap in-memory, file, or database backends as needed
- **Advanced Features**: Add summarization, context windowing, or long-term memory

---

## Best Practices 🏛️

- **No global state**: All memory is managed per session/conversation
- **No business logic in memory**: Pure context management, no agent reasoning
- **Testable**: Clear API boundaries for unit and integration testing

---

**Give your agent a memory—make every conversation smarter!** 🧠💬
