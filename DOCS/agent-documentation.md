# AI File System Agent Documentation

## Overview

The AI File System Agent is an intelligent autonomous agent that provides safe and efficient file system operations through natural language interaction. It uses advanced reasoning patterns, security controls, and comprehensive monitoring to help users manage files and directories within a secured workspace.

## Architecture

### Core Components

#### 1. SecureAgent (`agent/core/secure_agent.py`)
The main agent orchestrator that:
- Processes user queries using ReAct reasoning
- Maintains conversation context and security boundaries
- Coordinates between supervisor and tool execution
- Provides structured responses with error handling

**Key Features:**
- Autonomous reasoning with the ReAct pattern
- Comprehensive error handling with user-friendly messages
- Performance tracking and usage statistics
- Debug mode for detailed reasoning traces

#### 2. ReAct Loop (`agent/core/react_loop.py`)
Implements the Reasoning-Action-Observation pattern:
- **Think**: Analyzes the problem and plans next steps
- **Act**: Executes tools based on reasoning
- **Observe**: Processes results and continues reasoning
- **Complete**: Provides final response

**Multi-step Capabilities:**
- Complex file operations (find largest file, read newest, etc.)
- Intelligent tool chaining
- Context-aware decision making
- Graceful failure recovery

#### 3. Supervisor (`agent/supervisor/supervisor.py`)
Provides safety moderation and intent extraction:
- **Two-phase moderation**: Fast content filtering + AI analysis
- **Safety risk detection**: Path traversal, malicious code, system access, etc.
- **Intent extraction**: Understands user goals for better tool routing
- **Enhanced rejection explanations** with suggested alternatives

#### 4. File System Tools (`tools/workspace_fs/`)
Secure file system operations:
- `list_files()`: List files with sorting options
- `read_file(filename)`: Read file contents safely
- `write_file(filename, content)`: Write files with validation
- `create_directory(path)`: Create directory structures
- `delete_file(filename)`: Remove files safely
- Advanced operations: `find_largest_file()`, `read_newest_file()`

#### 5. Diagnostics System (`agent/diagnostics.py`)
Comprehensive monitoring and analytics:
- **Performance tracking**: Operation timing and memory usage
- **Usage statistics**: Tool usage, conversation metrics, error rates
- **Security monitoring**: Safety events and risk assessments
- **Health checks**: System status and resource monitoring
- **Export capabilities**: JSON diagnostics reports

### Data Flow

```
User Query → Supervisor (Safety Check) → SecureAgent → ReAct Loop → Tools → Response
                ↓                           ↓              ↓         ↓
            Security Events         Operation Tracking  Tool Usage  Results
                ↓                           ↓              ↓         ↓
            Diagnostics System ←──────────────────────────────────────┘
```

## Usage Examples

### Basic File Operations

#### List Files
```python
# User: "What files are in my workspace?"
# Agent uses list_files() and formats results
response = await agent.process_query("What files are in my workspace?")
```

#### Read File Content
```python
# User: "Show me the content of README.md"
# Agent uses read_file("README.md")
response = await agent.process_query("Show me the content of README.md")
```

#### Write New File
```python
# User: "Create a new file called hello.py with a simple hello world script"
# Agent uses write_file() with generated content
response = await agent.process_query("Create a new file called hello.py with a simple hello world script")
```

### Advanced Multi-Step Operations

#### Find and Read Largest File
```python
# User: "What's in the largest file?"
# Agent chains: list_files() → find_largest_file() → read_file()
response = await agent.process_query("What's in the largest file?")
```

#### Analyze Recent Activity
```python
# User: "Show me the newest file and summarize its content"
# Agent chains: list_files() → read_newest_file() → content analysis
response = await agent.process_query("Show me the newest file and summarize its content")
```

### Security Examples

#### Safe Rejections
```python
# User: "Delete all my files"
# Supervisor detects malicious intent and provides helpful alternatives
response = await agent.process_query("Delete all my files")
# Response includes explanation and safer alternatives
```

#### Path Traversal Prevention
```python
# User: "Read ../../../etc/passwd"
# Supervisor detects path traversal attempt
response = await agent.process_query("Read ../../../etc/passwd")
# Response explains security concern and workspace boundaries
```

## Configuration

### Environment Setup

1. **Model Configuration** (`config/models.yaml`)
```yaml
models:
  primary:
    provider: "gemini"
    model: "gemini-1.5-flash"
    temperature: 0.1
  supervisor:
    provider: "gemini"  
    model: "gemini-1.5-flash-8b"
    temperature: 0.0
```

2. **Environment Variables**
```bash
# Required
GEMINI_API_KEY=your_api_key_here

# Optional
DEBUG=true                    # Enable debug mode
WORKSPACE_PATH=/path/to/workspace  # Custom workspace path
LOG_LEVEL=INFO               # Logging level
```

3. **Workspace Setup**
```python
from agent.core.secure_agent import SecureAgent
from pathlib import Path

# Initialize agent with workspace
agent = SecureAgent(
    workspace_path=Path("./my_workspace"),
    debug_mode=True
)
```

### Logging Configuration

The agent uses structured logging with multiple output streams:

- **Agent Activity** (`logs/agent_activity.log`): Detailed operation logs
- **Performance** (`logs/performance.jsonl`): JSON performance metrics  
- **Usage Statistics** (`logs/usage.jsonl`): JSON usage data
- **Errors** (`logs/errors.log`): Error tracking and debugging
- **Console Output**: Debug mode real-time logging

## API Reference

### SecureAgent Class

```python
class SecureAgent:
    def __init__(
        self, 
        workspace_path: Path, 
        debug_mode: bool = False,
        model_config: Optional[ModelConfig] = None
    ):
        """Initialize the secure agent."""
        
    async def process_query(self, user_query: str) -> AgentResponse:
        """Process a user query and return structured response."""
```

### AgentResponse Structure

```python
@dataclass
class AgentResponse:
    conversation_id: str
    response: str
    tools_used: List[str]
    reasoning_steps: Optional[List[str]]
    success: bool
    error_message: Optional[str] = None
```

### Diagnostics API

```python
# Performance monitoring
from agent.diagnostics import get_performance_summary, get_usage_statistics

performance = get_performance_summary(hours=24)
usage = get_usage_statistics()

# Health monitoring
health = health_check()
diagnostics_file = export_diagnostics()
```

## Troubleshooting Guide

### Common Issues

#### 1. Model Configuration Errors
**Problem**: `ModelConfigurationError: Could not load model configuration`

**Solutions:**
- Verify `config/models.yaml` exists and is valid YAML
- Check API keys are set in environment variables
- Ensure model names are correct for your provider

#### 2. Workspace Permission Issues
**Problem**: `ToolExecutionError: Permission denied accessing file`

**Solutions:**
- Check workspace directory permissions
- Verify files exist and are readable
- Ensure workspace path is correctly set

#### 3. Tool Execution Failures
**Problem**: Tools fail with unexpected errors

**Solutions:**
- Enable debug mode: `debug_mode=True`
- Check logs in `logs/` directory
- Verify tool arguments and file paths
- Use diagnostics to check system health

#### 4. Security Rejections
**Problem**: Valid requests being rejected by supervisor

**Solutions:**
- Check content filtering sensitivity
- Review security event logs
- Rephrase requests to be more specific
- Use suggested alternatives in rejection messages

### Debug Mode

Enable comprehensive debugging:

```python
agent = SecureAgent(workspace_path=Path("./workspace"), debug_mode=True)
```

Debug mode provides:
- Detailed reasoning step traces
- Tool execution logging
- Enhanced error messages
- Performance timing information

### Log Analysis

#### Check Agent Activity
```bash
tail -f logs/agent_activity.log
```

#### Monitor Performance
```bash
cat logs/performance.jsonl | jq '.duration' | sort -n
```

#### Review Security Events
```bash
grep "SECURITY_EVENT" logs/agent_activity.log
```

#### Export Diagnostics
```python
from agent.diagnostics import export_diagnostics
diagnostic_file = export_diagnostics()
print(f"Diagnostics exported to: {diagnostic_file}")
```

### Performance Optimization

#### Monitoring Performance
- Use `get_performance_summary()` to track operation times
- Monitor memory usage in diagnostics reports
- Check success rates and error patterns

#### Optimizing Queries
- Be specific about file names and operations
- Use workspace-relative paths
- Avoid overly complex multi-step requests

#### Resource Management
- Monitor disk space in workspace
- Check memory usage during large file operations
- Use health checks to monitor system resources

## Best Practices

### For Users

1. **Be Specific**: Clear, specific requests get better results
   - Good: "Read the config.json file"
   - Avoid: "Show me some config"

2. **Use Workspace Paths**: Stick to files in your workspace
   - Good: "Create a new folder called 'docs'"
   - Avoid: "Access system configuration files"

3. **Handle Errors Gracefully**: Read error messages for guidance
   - Error messages include recovery suggestions
   - Use debug mode for complex issues

### For Developers

1. **Error Handling**: Always handle `AgentError` exceptions
2. **Resource Cleanup**: Properly close file handles and resources
3. **Security**: Validate all user inputs through the supervisor
4. **Monitoring**: Use diagnostics for production monitoring
5. **Testing**: Use `FakeChatModel` for deterministic testing

## Security Model

### Safety Boundaries

The agent operates within strict security boundaries:

1. **Workspace Isolation**: All operations confined to designated workspace
2. **Path Validation**: Prevents directory traversal attacks
3. **Content Filtering**: Blocks malicious code and harmful requests
4. **Intent Analysis**: Understands and validates user intentions
5. **Rate Limiting**: Prevents abuse through operation tracking

### Risk Assessment

The supervisor evaluates requests for:
- **Path Traversal**: Attempts to access files outside workspace
- **Malicious Code**: Potentially harmful commands or scripts
- **System Access**: Requests for system-level operations
- **Data Exfiltration**: Attempts to extract or transmit sensitive data
- **Prompt Injection**: Attempts to manipulate agent behavior

### Security Monitoring

All security events are logged and can be monitored:
- Request approvals and rejections
- Risk factor detection
- Confidence levels in security decisions
- User behavior patterns

## Testing

### Unit Testing
```bash
python -m pytest tests/unit/ -v
```

### Integration Testing
```bash
python -m pytest tests/integration/ -v
```

### Coverage Report
```bash
python -m pytest --cov=agent --cov-report=html
```

## Monitoring and Maintenance

### Health Checks
```python
from agent.diagnostics import health_check
health = health_check()
print(f"System status: {health['overall_status']}")
```

### Performance Monitoring
```python
from agent.diagnostics import get_performance_summary
perf = get_performance_summary(hours=24)
print(f"Success rate: {perf['success_rate']:.2%}")
```

### Log Rotation
Configure log rotation to prevent disk space issues:
```bash
# Add to logrotate configuration
/path/to/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

This documentation provides comprehensive guidance for using, configuring, and maintaining the AI File System Agent. For additional support, check the logs directory and use the built-in diagnostics tools.
