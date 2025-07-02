# Agent Architecture Documentation

## Overview

The AI File System Agent implements a sophisticated, multi-layered architecture designed for secure, reliable, and intelligent file system operations. The system follows a modular design with clear separation of concerns, enabling maintainability, testability, and extensibility.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                     │
├─────────────────────────────────────────────────────────────┤
│  CLI Chat Interface  │  Demo Interfaces  │  Future: Web UI  │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                      Security Layer                         │
├─────────────────────────────────────────────────────────────┤
│          Supervisor (Lightweight Model Gatekeeper)         │
│  • Content Filtering    • Intent Extraction                │
│  • Jailbreak Detection  • Safety Validation               │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                       Agent Core                            │
├─────────────────────────────────────────────────────────────┤
│              SecureAgent (Main Reasoning Engine)           │
│  • ReAct Loop          • Conversation Management           │
│  • Tool Orchestration  • Context Tracking                 │
│  • Error Handling      • Response Generation               │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                      Tool Integration Layer                 │
├─────────────────────────────────────────────────────────────┤
│   File System Tools   │   CRUD Tools   │   Future: API Tools │
│  • Workspace Mgmt     │  • File Ops    │  • Web Services    │
│  • Safe Boundaries    │  • Data Manip  │  • External APIs   │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                     │
├─────────────────────────────────────────────────────────────┤
│  Config Management │  Logging System │  Error Handling     │
│  • Model Config    │  • Structured   │  • Exception        │
│  • Env Variables   │  • Diagnostics  │    Hierarchy        │
│  • Validation      │  • Audit Trail  │  • Recovery         │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Agent Core (`agent/core/`)

#### SecureAgent (`secure_agent.py`)

The main reasoning engine that orchestrates all agent operations.

**Key Responsibilities:**

- Primary conversation management
- Tool registration and execution
- Response generation and formatting
- Integration with security supervisor
- Error handling and recovery

**Architecture:**

```python
class SecureAgent:
    def __init__(self, config: AgentConfig):
        self.supervisor = SupervisorAgent(config.supervisor_model)
        self.model = config.main_model
        self.tools = self._register_tools()
        self.conversation_context = ConversationContext()

    async def process_query(self, query: str) -> AgentResponse:
        # 1. Security check via supervisor
        intent = await self.supervisor.analyze_intent(query)
        if not intent.is_safe:
            return self._create_rejection_response(intent.reason)

        # 2. Execute ReAct reasoning loop
        return await self.react_loop.execute(query, intent)
```

#### ReAct Loop (`react_loop.py`)

Implements the Reasoning-Action-Observation cycle for structured problem-solving.

**Phases:**

1. **THINK**: Analyze the query and plan approach
2. **ACT**: Execute tools or generate responses
3. **OBSERVE**: Process results and determine next steps

**Scratchpad Management:**

- Maintains conversation context across interactions
- Tracks reasoning steps for debugging and audit
- Enables complex multi-step operations

### 2. Security Supervisor (`agent/supervisor/`)

#### SupervisorAgent (`supervisor.py`)

Lightweight, fast security gatekeeper using efficient models.

**Two-Phase Processing:**

1. **Fast Rejection**: Quick safety assessment using small model
2. **Intent Extraction**: Detailed analysis for approved requests

**Security Features:**

- Content moderation with multiple filter layers
- Jailbreak pattern detection
- Intent classification (6 categories: read, write, delete, list, search, analyze)
- Structured safety reporting

**Models Used:**

- Primary: `gpt-4o-mini` for speed and cost efficiency
- Fallback: `gpt-3.5-turbo` for reliability

### 3. Tool Integration (`tools/`)

#### Workspace File System (`workspace_fs/`)

Manages sandboxed file operations with safety boundaries.

**Core Operations:**

- `list_workspace_files`: Directory traversal with filtering
- `read_file_content`: Safe file reading with encoding detection
- `create_new_file`: File creation with conflict resolution
- `update_file_content`: Content modification with backup
- `delete_file`: Secure deletion with confirmation

**Safety Features:**

- Path traversal prevention
- Workspace boundary enforcement
- File size and type validation
- Backup and recovery mechanisms

#### CRUD Tools (`crud_tools/`)

Advanced file manipulation and data processing utilities.

**Capabilities:**

- JSON/CSV data manipulation
- Batch file operations
- Content analysis and transformation
- Pattern matching and filtering

### 4. Configuration System (`config/`)

#### Environment Management (`env_loader.py`)

Handles environment variables, API keys, and configuration validation.

**Features:**

- Multi-environment support (dev, test, prod)
- Secure API key management
- Configuration validation with Pydantic
- Environment-specific overrides

#### Model Configuration (`model_config.py`)

Manages AI model selection and configuration.

**Support:**

- OpenAI (GPT-4o, GPT-4o-mini, GPT-3.5-turbo)
- Anthropic (Claude models)
- Google AI (Gemini models)
- Role-based model assignment

## Data Flow

### 1. Request Processing Flow

```
User Query → CLI Interface → Supervisor → Agent Core → Tools → Response
     ↓           ↓              ↓           ↓          ↓        ↓
   "Find      Parse &      Safety      ReAct     Execute   Format &
  largest    Format       Check       Loop      Tools     Return
   file"
```

### 2. Security Validation Flow

```
Input Query
    ↓
Content Filtering (Multi-layer)
    ↓
Jailbreak Detection
    ↓
Intent Classification
    ↓
Safety Assessment
    ↓
Allow/Deny Decision
```

### 3. Tool Execution Flow

```
Tool Request
    ↓
Parameter Validation
    ↓
Sandbox Boundary Check
    ↓
Operation Execution
    ↓
Result Processing
    ↓
Error Handling (if needed)
    ↓
Formatted Response
```

## Error Handling Architecture

### Exception Hierarchy

```python
# Base exceptions
class AgentError(Exception): pass
class SecurityError(AgentError): pass
class ToolError(AgentError): pass
class ConfigurationError(AgentError): pass

# Specific exceptions
class UnsafeRequestError(SecurityError): pass      # Harmful content
class JailbreakAttemptError(SecurityError): pass  # Prompt injection
class ToolExecutionError(ToolError): pass         # Tool failures
class WorkspaceBoundaryError(ToolError): pass     # Path violations
```

### Error Recovery Strategies

1. **Graceful Degradation**: Fallback to safer operations
2. **User Guidance**: Clear explanations and suggestions
3. **Retry Mechanisms**: Automatic retry for transient failures
4. **Alternative Approaches**: Suggest different ways to achieve goals

## Performance Characteristics

### Response Times

- **Simple operations** (list files): < 2s
- **Complex multi-step tasks**: < 10s
- **Security validation**: < 500ms

### Resource Usage

- **Memory**: ~200MB base, ~50MB per conversation
- **API calls**: Optimized with caching and batching
- **Storage**: Minimal, conversation logs only

### Scalability

- **Concurrent users**: Stateless design supports multiple sessions
- **Long conversations**: Context management with memory limits
- **Tool operations**: Async execution where possible

## Testing Strategy

### Unit Tests

- Individual component testing
- Mock dependencies for isolation
- Deterministic behavior validation

### Integration Tests

- End-to-end workflow testing
- Real tool execution in controlled environment
- Multi-step reasoning validation

### Security Tests

- Safety mechanism validation
- Jailbreak attempt simulation
- Boundary violation testing

### Performance Tests

- Response time measurement
- Memory usage profiling
- Concurrent load testing

## Deployment Architecture

### Development Environment

- Local development with Poetry
- Hot reloading for rapid iteration
- Debug mode for detailed logging

### Production Environment

- Containerized deployment (Docker)
- Environment-specific configuration
- Monitoring and alerting integration
- Graceful shutdown handling

## Monitoring and Observability

### Logging

- Structured JSON logging
- Multiple log levels (DEBUG, INFO, WARN, ERROR)
- Conversation tracking with unique IDs
- Performance metrics integration

### Metrics

- Request/response timing
- Tool usage statistics
- Error rates and categories
- Security event tracking

### Health Checks

- System component availability
- API connectivity validation
- Tool functionality verification
- Resource usage monitoring

## Security Considerations

### Data Protection

- No persistent storage of sensitive data
- Secure API key management
- Workspace sandboxing
- Audit trail maintenance

### Access Control

- Tool-level permission boundaries
- File system access restrictions
- API rate limiting
- User session isolation

### Threat Mitigation

- Prompt injection prevention
- Content filtering
- Resource exhaustion protection
- Malicious file detection

## Future Enhancements

### Planned Features

- Web-based user interface
- Plugin system for custom tools
- Advanced analytics dashboard
- Multi-user workspace support

### Architecture Evolution

- Microservice decomposition
- Event-driven architecture
- Distributed tool execution
- Advanced caching layer

---

This architecture provides a solid foundation for secure, scalable, and maintainable AI agent operations while maintaining clear separation of concerns and comprehensive error handling.
