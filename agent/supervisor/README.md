# 🛡️ agent/supervisor — The Guardian of Your AI Agent ⚡

Welcome to the **supervisor** layer!  
This is where every user request is checked, filtered, and understood—before it ever reaches the core agent.  
Think of it as your agent’s **security guard and intent detective**. 🕵️‍♂️🛡️

---

## What’s Inside? 📦

This package implements a **lightweight LLM supervisor** that:

- **MODERATES**: Screens every request for safety, security, and compliance
- **EXTRACTS INTENT**: Figures out what the user really wants (even in multiple languages!)
- **DEFENDS**: Blocks dangerous, ambiguous, or off-topic actions before they can do harm

All with **high cohesion**, **low coupling**, and a focus on **single responsibility**.

---

## Folder Structure 🗂️

| File            | Purpose                                                                |
| --------------- | ---------------------------------------------------------------------- |
| `supervisor.py` | 🛡️ Main supervisor logic: moderation, intent extraction, safety checks |
| `__init__.py`   | 📦 Exports the public API for the supervisor module                    |

---

## Key Concepts & Design Principles 🏛️

- **Single Responsibility**: Only moderates and extracts intent—nothing else.
- **LLM-Driven**: Uses a fast, specialized model for pre-screening and intent analysis.
- **Security First**: Detects path traversal, prompt injection, and other risks.
- **Context-Aware**: Handles ambiguous or contextual user replies with conversation history.
- **Extensible**: Add new moderation rules or intent types with minimal changes.

---

## How It Works 🔗

1. **User sends a request**
2. `RequestSupervisor` runs **fast safety checks** and **intent extraction**
3. If safe and clear, the request is passed to the main agent
4. If risky or ambiguous, it’s blocked or flagged for review
5. All decisions are **transparent** and **explainable** (with reasons & risk factors)

---

## Why This Matters 💡

- **Safety**: No unsafe or malicious requests reach your agent.
- **Clarity**: Every request is understood—no more “what did the user mean?”.
- **Auditability**: Every moderation decision is logged and explainable.
- **Plug & Play**: Drop in new moderation logic or intent types as your project grows.

---

## Want to Extend? 🛠️

- Add new intent types or risk factors in `supervisor.py`
- Enhance moderation logic for new threat models
- Integrate with external logging or alerting systems

---

**Let your agent work smarter and safer—supervise every step!** 🦾🕵️‍♀️
