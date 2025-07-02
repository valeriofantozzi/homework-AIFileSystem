# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the AI File System Agent. Issues are organized by category with step-by-step solutions.

## 🚨 Quick Diagnostics

### System Health Check

Run this command to verify your setup:

```bash
poetry run python -c "
from config.env_loader import EnvLoader
from config.model_config import AgentConfig
try:
    env = EnvLoader.load()
    config = AgentConfig.from_env()
    print('✅ Configuration loaded successfully')
    print(f'✅ Main model: {config.main_model}')
    print(f'✅ Supervisor model: {config.supervisor_model}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"
```

### Agent Status Check

```bash
# Verify workspace
poetry run python -m tools.workspace_fs.workspace status

# Test basic functionality
poetry run python -c "
import asyncio
from agent.core.secure_agent import SecureAgent
from config.model_config import AgentConfig

async def test():
    try:
        config = AgentConfig.from_env()
        agent = SecureAgent(config)
        response = await agent.process_query('Hello, can you help me?')
        print('✅ Agent responding normally')
    except Exception as e:
        print(f'❌ Agent error: {e}')

asyncio.run(test())
"
```

## 🔧 Installation Issues

### Poetry Installation Problems

**Problem:** `poetry: command not found`

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH (add to your ~/.zshrc or ~/.bashrc)
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.zshrc
```

**Problem:** `poetry install` fails with dependency conflicts

```bash
# Clear poetry cache
poetry cache clear pypi --all

# Update poetry
poetry self update

# Fresh install
rm poetry.lock
poetry install
```

**Problem:** Python version compatibility

```bash
# Check Python version
python3 --version

# Should be 3.11+, if not:
# On macOS with Homebrew
brew install python@3.11

# Update pyproject.toml if needed
poetry env use python3.11
poetry install
```

### Package Installation Issues

**Problem:** Missing system dependencies

```bash
# macOS
brew install pkg-config libffi

# Ubuntu/Debian
sudo apt-get install build-essential libffi-dev python3-dev

# Then retry installation
poetry install
```

## 🔑 Configuration Issues

### API Key Problems

**Problem:** `Invalid API key` or `Authentication failed`

**Diagnosis:**

```bash
# Check if .env.local exists
ls -la config/env/.env.local

# Verify content (without exposing keys)
grep -c "API_KEY" config/env/.env.local
```

**Solutions:**

1. **Missing configuration file:**

   ```bash
   cp config/env/.env.example config/env/.env.local
   # Edit with your API keys
   ```

2. **Invalid key format:**

   ```bash
   # OpenAI keys start with 'sk-'
   # Anthropic keys start with 'sk-ant-'
   # Google AI keys are 39 characters
   ```

3. **Key verification:**

   ```bash
   # Test OpenAI key
   curl -H "Authorization: Bearer YOUR_OPENAI_KEY" \
        https://api.openai.com/v1/models

   # Test Anthropic key
   curl -H "x-api-key: YOUR_ANTHROPIC_KEY" \
        https://api.anthropic.com/v1/messages
   ```

### Model Configuration Issues

**Problem:** `Model 'gpt-4o' not available`

**Solutions:**

1. **Check model availability:**

   ```bash
   # Edit config/models.yaml
   roles:
     agent: "gpt-4o-mini"  # More widely available
     supervisor: "gpt-3.5-turbo"
   ```

2. **Use alternative models:**

   ```yaml
   # Budget-friendly configuration
   roles:
     agent: "gpt-3.5-turbo"
     supervisor: "gpt-3.5-turbo"

   # Anthropic alternative
   roles:
     agent: "claude-3-sonnet"
     supervisor: "claude-3-haiku"
   ```

### Environment Loading Issues

**Problem:** `Environment file not found` or variables not loading

```bash
# Check environment loading
poetry run python -c "
from config.env_loader import EnvLoader
env = EnvLoader.load()
print(f'Environment: {env.environment}')
print(f'Config path: {env.config_path}')
"
```

**Solutions:**

1. **File location:** Ensure `.env.local` is in `config/env/`
2. **File format:** Use `KEY=value` format (no spaces around =)
3. **Permissions:** Ensure file is readable (`chmod 644`)

## 🤖 Agent Runtime Issues

### Slow Response Times

**Problem:** Agent takes >30 seconds to respond

**Diagnosis:**

```bash
# Enable debug mode to see timing
poetry run python -m chat_interface.cli_chat.chat --debug
```

**Solutions:**

1. **Model optimization:**

   ```yaml
   # Use faster models
   roles:
     agent: "gpt-4o-mini"
     supervisor: "gpt-3.5-turbo"
   ```

2. **Network issues:**

   ```bash
   # Test API connectivity
   curl -w "@curl-format.txt" -s -o /dev/null https://api.openai.com/v1/models
   ```

3. **Query optimization:**
   ```
   # Instead of: "Tell me everything about all my files"
   # Use: "List my Python files with their sizes"
   ```

### Memory Issues

**Problem:** `MemoryError` or system becomes unresponsive

**Solutions:**

1. **Restart session:**

   ```bash
   # Exit and restart the chat interface
   Ctrl+C
   poetry run python -m chat_interface.cli_chat.chat
   ```

2. **Process large files in chunks:**

   ```
   You: Show me the first 100 lines of large_file.txt
   # Instead of reading entire file
   ```

3. **Monitor memory usage:**
   ```bash
   # In another terminal
   top -p $(pgrep -f "python.*chat")
   ```

### Conversation Context Issues

**Problem:** Agent "forgets" earlier conversation

**Causes:**

- Context window limits exceeded
- Session restart
- Model limitations

**Solutions:**

1. **Summarize important context:**

   ```
   You: Based on our earlier discussion about the sales data, now show me...
   ```

2. **Break long conversations:**
   ```bash
   # Start fresh session for new topics
   Ctrl+C
   poetry run python -m chat_interface.cli_chat.chat
   ```

## 🛡️ Security & Safety Issues

### Safety Blocking Issues

**Problem:** Agent rejects legitimate requests

**Example:**

```
You: Delete old backup files
Agent: I cannot help with file deletion as it may be unsafe.
```

**Solutions:**

1. **Rephrase requests:**

   ```
   # Instead of: "Delete all backup files"
   # Try: "Help me clean up .bak files that are older than 30 days"
   ```

2. **Be specific:**

   ```
   # Instead of: "Remove everything"
   # Try: "Remove the file named temp_data.txt"
   ```

3. **Check debug output:**
   ```bash
   poetry run python -m chat_interface.cli_chat.chat --debug
   # See why request was flagged
   ```

### Workspace Boundary Issues

**Problem:** `WorkspaceBoundaryError: Path outside workspace`

**Cause:** Trying to access files outside the sandbox

**Solutions:**

1. **Check workspace location:**

   ```bash
   poetry run python -m tools.workspace_fs.workspace status
   ```

2. **Copy files to workspace:**

   ```bash
   # Copy external files to workspace
   cp /path/to/external/file ./workspace/
   ```

3. **Reinitialize workspace:**
   ```bash
   poetry run python -m tools.workspace_fs.workspace init --force
   ```

## 🔧 Tool Integration Issues

### File System Tool Errors

**Problem:** `ToolExecutionError` during file operations

**Common Causes:**

1. **Permission issues:**

   ```bash
   # Check workspace permissions
   ls -la workspace/
   chmod -R 755 workspace/
   ```

2. **File locks:**

   ```bash
   # Close files in other applications
   # Or restart if files are locked
   ```

3. **Disk space:**
   ```bash
   df -h .
   # Ensure sufficient space
   ```

### Encoding Issues

**Problem:** `UnicodeDecodeError` when reading files

**Solutions:**

1. **File encoding detection:**

   ```bash
   file -I filename.txt
   # Shows encoding information
   ```

2. **Convert file encoding:**

   ```bash
   iconv -f ISO-8859-1 -t UTF-8 input.txt > output.txt
   ```

3. **Agent handles common encodings automatically**

## 🚀 Performance Issues

### Optimization Strategies

**Slow File Operations:**

1. **Large file handling:**

   ```
   # Instead of: "Read entire 100MB file"
   # Use: "Show first 50 lines of large_file.txt"
   ```

2. **Batch operations:**
   ```
   # Instead of: Multiple individual requests
   # Use: "Process all .csv files and create summaries"
   ```

**API Rate Limiting:**

```bash
# If you hit rate limits, wait or switch models
# Configure retries in models.yaml:
models:
  gpt-4o:
    max_retries: 3
    retry_delay: 5
```

## 🔍 Debugging Techniques

### Debug Mode

**Enable comprehensive logging:**

```bash
export AGENT_DEBUG=true
export LOG_LEVEL=DEBUG
poetry run python -m chat_interface.cli_chat.chat --debug
```

**Debug output interpretation:**

```
[SUPERVISOR] Analyzing query: "list files"
[SUPERVISOR] Intent: list, Safety: SAFE
[AGENT] Executing tool: list_workspace_files
[TOOL] Found 15 files in workspace
[AGENT] Formatting response
```

### Log Analysis

**Check logs for errors:**

```bash
# Recent logs
tail -n 50 logs/agent.log

# Error filtering
grep -i error logs/agent.log

# Performance analysis
grep -i "took\|time" logs/agent.log
```

### Manual Testing

**Test individual components:**

```bash
# Test supervisor
poetry run python -c "
import asyncio
from agent.supervisor.supervisor import SupervisorAgent
async def test():
    supervisor = SupervisorAgent('gpt-4o-mini')
    result = await supervisor.analyze_intent('list my files')
    print(result)
asyncio.run(test())
"

# Test tools
poetry run python -c "
from tools.workspace_fs.fs_tools import list_workspace_files
result = list_workspace_files()
print(result)
"
```

## 📋 Error Reference

### Common Error Codes

| Error Type               | Code   | Description            | Solution                  |
| ------------------------ | ------ | ---------------------- | ------------------------- |
| `ConfigurationError`     | CFG001 | Missing API key        | Add key to .env.local     |
| `SecurityError`          | SEC001 | Unsafe request         | Rephrase query            |
| `ToolError`              | TL001  | File not found         | Check file path           |
| `ToolError`              | TL002  | Permission denied      | Check file permissions    |
| `WorkspaceBoundaryError` | WS001  | Path outside workspace | Use workspace files only  |
| `ModelError`             | MDL001 | Model unavailable      | Switch to available model |

### Error Message Patterns

**Configuration Errors:**

```
❌ "Environment file not found"
→ Create config/env/.env.local

❌ "Invalid model configuration"
→ Check config/models.yaml format

❌ "API key missing or invalid"
→ Verify API keys in .env.local
```

**Runtime Errors:**

```
❌ "Request rejected by supervisor"
→ Rephrase request more specifically

❌ "Tool execution failed"
→ Check file permissions and paths

❌ "Context window exceeded"
→ Start new conversation
```

## 🆘 Emergency Recovery

### Complete Reset

If nothing works, perform a complete reset:

```bash
# 1. Backup important files
cp -r workspace/ workspace_backup/

# 2. Clean installation
rm -rf .venv poetry.lock
poetry install

# 3. Reset configuration
rm config/env/.env.local
cp config/env/.env.example config/env/.env.local
# Re-add your API keys

# 4. Reinitialize workspace
poetry run python -m tools.workspace_fs.workspace init --force

# 5. Test basic functionality
poetry run python -m chat_interface.cli_chat.chat
```

### Data Recovery

**If workspace is corrupted:**

```bash
# Check backup location
ls -la workspace_backup/

# Restore from backup
rm -rf workspace/
cp -r workspace_backup/ workspace/

# Or initialize fresh workspace
poetry run python -m tools.workspace_fs.workspace init
```

## 📞 Getting Help

### Self-Service Resources

1. **Documentation:** Check `DOCS/` directory
2. **Examples:** Review `DOCS/examples/`
3. **Tests:** See `tests/` for expected behavior
4. **Logs:** Analyze `logs/` for error patterns

### Reporting Issues

When reporting issues, include:

```bash
# System information
uname -a
python3 --version
poetry --version

# Configuration (sanitized)
poetry run python -c "
from config.env_loader import EnvLoader
env = EnvLoader.load()
print(f'Environment: {env.environment}')
print(f'Python version: {env.python_version}')
"

# Error logs (last 20 lines)
tail -n 20 logs/agent.log

# Reproduction steps
# 1. Started agent with: poetry run python -m chat_interface.cli_chat.chat
# 2. Asked: "list my files"
# 3. Got error: [paste error message]
```

### Community Support

- **GitHub Issues:** Report bugs and feature requests
- **Discussions:** Ask questions and share solutions
- **Documentation:** Contribute improvements

---

This troubleshooting guide covers the most common issues. For complex problems, enable debug mode and analyze the detailed logs to understand the root cause.
