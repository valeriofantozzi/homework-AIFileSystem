# Usage Guide

This guide provides comprehensive examples and patterns for using the AI File System Agent effectively. Whether you're a developer, data analyst, or power user, you'll find practical examples for common workflows.

## Getting Started

### Basic Setup

1. **Environment Configuration:**

   ```bash
   # Copy and edit configuration
   cp config/env/.env.example config/env/.env.local

   # Add your API keys
   vim config/env/.env.local
   ```

2. **Workspace Initialization:**

   ```bash
   # Initialize the sandbox workspace
   poetry run python -m tools.workspace_fs.workspace init

   # Verify setup
   poetry run python -m tools.workspace_fs.workspace status
   ```

3. **Start the Agent:**

   ```bash
   # Interactive mode
   poetry run python -m chat_interface.cli_chat.chat

   # Debug mode (see reasoning)
   poetry run python -m chat_interface.cli_chat.chat --debug
   ```

## Basic Operations

### File Listing and Exploration

**List all files:**

```
You: Show me all files in my workspace
Agent: I'll explore your workspace and show you all the files.

[Lists files with sizes, dates, and organization]
```

**Filtered listing:**

```
You: Find all Python files
Agent: I'll search for Python files in your workspace.

[Shows *.py files with details]
```

**Directory structure:**

```
You: Show me the directory structure
Agent: I'll map out your directory structure for you.

[Displays hierarchical tree view]
```

### File Reading

**Read specific file:**

```
You: Read the contents of config.json
Agent: I'll read the config.json file for you.

[Displays file contents with syntax highlighting]
```

**Read newest file:**

```
You: Show me the newest file
Agent: I'll find and display the most recently created file.

[Identifies newest file and shows contents]
```

**Partial file reading:**

```
You: Show me the first 10 lines of data.csv
Agent: I'll read the beginning of data.csv for you.

[Shows first 10 lines with proper formatting]
```

### File Creation

**Create simple file:**

```
You: Create a file called notes.txt with "Hello World"
Agent: I'll create notes.txt with your content.

[Creates file and confirms success]
```

**Create with complex content:**

```
You: Create a Python script that prints fibonacci numbers
Agent: I'll create a Python script for fibonacci sequence generation.

[Creates complete, functional Python script]
```

### File Modification

**Update existing file:**

```
You: Add a new line to notes.txt saying "Second line"
Agent: I'll append the new line to your notes.txt file.

[Updates file and shows changes]
```

**Bulk modifications:**

```
You: Replace all occurrences of "old_value" with "new_value" in config.json
Agent: I'll perform the text replacement in your config file.

[Makes replacements and shows summary]
```

## Advanced Use Cases

### Data Analysis Workflows

**CSV Analysis:**

```
You: Analyze the sales_data.csv file and tell me the top 5 customers by revenue
Agent: I'll analyze your sales data to identify top customers.

[Reads CSV, processes data, provides ranked results]
```

**Log File Analysis:**

```
You: Parse server.log and show me all error messages from today
Agent: I'll extract today's error messages from your server log.

[Filters log entries, extracts errors, formats results]
```

**JSON Data Processing:**

```
You: Read products.json and create a summary report of inventory levels
Agent: I'll analyze your product inventory and create a summary.

[Processes JSON, calculates statistics, generates report]
```

### Development Workflows

**Code Organization:**

```
You: List all Python files and organize them by purpose (tests, main code, utilities)
Agent: I'll categorize your Python files by their function.

[Analyzes file contents, categorizes by purpose]
```

**Documentation Generation:**

```
You: Create a README for the utils folder based on the Python files inside
Agent: I'll generate documentation based on your utility modules.

[Analyzes code, generates structured README]
```

**Project Structure Analysis:**

```
You: Analyze my project structure and suggest improvements
Agent: I'll examine your project layout and provide organization recommendations.

[Reviews structure, provides architectural suggestions]
```

### Content Management

**Duplicate Detection:**

```
You: Find any duplicate files in my workspace
Agent: I'll search for duplicate files by comparing content.

[Compares file contents, identifies duplicates]
```

**Content Search:**

```
You: Find all files that contain the word "database"
Agent: I'll search through all files for the term "database".

[Searches file contents, shows matches with context]
```

**Batch Operations:**

```
You: Rename all .txt files to have a .bak extension
Agent: I'll rename all text files to backup files.

[Performs bulk rename operation safely]
```

## Query Patterns and Best Practices

### Effective Query Formulation

**✅ Good Queries:**

- "Find the largest file and show me its first 20 lines"
- "Create a summary of all JSON files in the data folder"
- "List Python files modified in the last week"
- "Backup all configuration files to a backup folder"

**❌ Unclear Queries:**

- "Do something with files" (too vague)
- "Fix everything" (no specific action)
- "Show me stuff" (unclear intent)

### Multi-Step Operations

The agent excels at complex, multi-step operations:

**Example: Data Pipeline Creation**

```
You: Create a data processing pipeline that reads input.csv, filters rows where status is 'active', and saves the result to output.csv
Agent: I'll create a complete data processing pipeline for you.

Step 1: Reading input.csv to understand structure
Step 2: Filtering for active status records
Step 3: Creating output.csv with filtered data
Step 4: Providing summary of processed records
```

**Example: Project Setup**

```
You: Set up a new Python project with main.py, requirements.txt, and a README
Agent: I'll create a complete Python project structure for you.

Step 1: Creating main.py with basic structure
Step 2: Generating requirements.txt with common dependencies
Step 3: Creating comprehensive README with project info
Step 4: Adding .gitignore for Python projects
```

## Safety and Security

### Safe Operations

The agent automatically ensures safe operations:

**Boundary Protection:**

- Operations limited to designated workspace
- Path traversal attacks prevented
- System file access blocked

**Content Filtering:**

- Harmful content detection
- Inappropriate request rejection
- Graceful error messages

**Data Protection:**

- No unauthorized file access
- Backup creation for modifications
- Confirmation for destructive operations

### Working with Sensitive Data

**Best Practices:**

- Use the sandbox workspace for all operations
- Avoid sharing sensitive files in examples
- Review agent responses before acting on suggestions
- Use version control for important files

## Troubleshooting Common Issues

### Connection Problems

**API Key Issues:**

```
Error: Invalid API key
Solution: Check your .env.local file and ensure valid API keys
```

**Model Access Problems:**

```
Error: Model not available
Solution: Try switching to a different model in config/models.yaml
```

### File Operation Issues

**Permission Errors:**

```
Error: Permission denied
Solution: Ensure the workspace directory is writable
```

**File Not Found:**

```
Error: File not found
Solution: Use 'list files' to see available files, check spelling
```

### Performance Issues

**Slow Responses:**

```
Issue: Agent takes too long to respond
Solutions:
- Use smaller models for simple tasks
- Break complex queries into smaller parts
- Check network connectivity
```

**Memory Issues:**

```
Issue: Out of memory errors
Solutions:
- Restart the agent session
- Process large files in chunks
- Clear conversation history
```

## Advanced Configuration

### Model Selection

Edit `config/models.yaml` to optimize for your use case:

```yaml
# For speed (lower cost, faster responses)
roles:
  agent: "gpt-4o-mini"
  supervisor: "gpt-3.5-turbo"

# For quality (higher cost, better reasoning)
roles:
  agent: "gpt-4o"
  supervisor: "gpt-4o-mini"

# For specific providers
roles:
  agent: "claude-3-sonnet"
  supervisor: "claude-3-haiku"
```

### Debug Mode

Enable detailed logging to understand agent reasoning:

```bash
# Start with debug output
poetry run python -m chat_interface.cli_chat.chat --debug

# Or set environment variable
export AGENT_DEBUG=true
poetry run python -m chat_interface.cli_chat.chat
```

**Debug Output Example:**

```
[THINK] User wants to find the largest file
[ACT] Using list_workspace_files to get all files
[OBSERVE] Found 15 files, need to compare sizes
[THINK] file1.txt (1.2MB) is currently largest
[ACT] Reading largest file content
[OBSERVE] Successfully read file content
[RESPONSE] Here's the largest file...
```

### Custom Tool Configuration

Advanced users can configure tool behavior:

```python
# In your configuration
WORKSPACE_CONFIG = {
    "max_file_size": "10MB",
    "allowed_extensions": [".txt", ".py", ".json", ".csv"],
    "backup_enabled": True,
    "auto_confirm": False
}
```

## Integration Examples

### With Scripts

```python
# Direct integration example
from agent.core.secure_agent import SecureAgent
from config.model_config import AgentConfig

async def process_files():
    config = AgentConfig.from_env()
    agent = SecureAgent(config)

    response = await agent.process_query("List all Python files")
    print(response.content)
```

### With APIs

```python
# Flask web service example
from flask import Flask, request, jsonify
from agent.core.secure_agent import SecureAgent

app = Flask(__name__)
agent = SecureAgent.from_config()

@app.route('/query', methods=['POST'])
async def handle_query():
    query = request.json['query']
    response = await agent.process_query(query)
    return jsonify(response.dict())
```

## Performance Optimization

### Query Optimization

**Efficient Queries:**

- Be specific about what you need
- Use filters to narrow results
- Combine related operations in one query

**Example Optimizations:**

```
# Less efficient
"List all files" → "Show me their sizes" → "Which is largest?"

# More efficient
"Find the largest file in my workspace"
```

### Resource Management

**Memory Usage:**

- Long conversations may use more memory
- Restart sessions periodically for large workloads
- Process large files in chunks

**API Usage:**

- Simple operations use fewer API calls
- Complex reasoning requires more model interactions
- Use caching where possible

## Best Practices Summary

1. **Clear Communication:** Be specific in your requests
2. **Safety First:** Let the agent handle safety checks
3. **Incremental Work:** Break complex tasks into steps
4. **Verification:** Review results before acting on them
5. **Backup Important Data:** Use version control for critical files
6. **Monitor Performance:** Use debug mode to understand bottlenecks
7. **Stay Updated:** Keep dependencies and models current

## Getting Help

- **Documentation:** Comprehensive guides in `DOCS/`
- **Examples:** Sample conversations in `DOCS/examples/`
- **Troubleshooting:** Common issues in `DOCS/troubleshooting.md`
- **Architecture:** Technical details in `DOCS/agent-architecture.md`

---

This usage guide covers the most common patterns and workflows. For specific use cases or advanced customization, refer to the technical documentation or reach out for support.
