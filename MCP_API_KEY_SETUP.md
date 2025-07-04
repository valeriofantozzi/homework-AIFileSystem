# MCP Server Configuration Guide

This guide explains how to configure API keys for the MCP (Model Context Protocol) server integration with VSCode.

## Architecture Overview

The MCP server uses **high-cohesion configuration management**:

- **Environment isolation**: Development, testing, and production configs
- **Secure API key injection**: Keys passed via Docker environment variables
- **Low coupling**: No hardcoded credentials in source code

## Quick Setup

1. **Run the setup script:**

   ```bash
   ./setup_mcp_env.sh
   ```

2. **Edit the environment file:**

   ```bash
   # Add your API keys to config/.env.local
   OPENAI_API_KEY=sk-your-openai-key-here
   GEMINI_API_KEY=your-gemini-key-here
   ```

3. **Restart VSCode** to reload the MCP configuration

## Configuration Details

### Environment Variables Passed to Docker

The `mcp.json` configuration passes these environment variables:

```json
{
  "servers": {
    "ai-filesystem": {
      "command": "sh",
      "args": [
        "-c",
        "docker run ...
         -e OPENAI_API_KEY=\"${OPENAI_API_KEY:-}\"
         -e GEMINI_API_KEY=\"${GEMINI_API_KEY:-}\"
         -e ANTHROPIC_API_KEY=\"${ANTHROPIC_API_KEY:-}\"
         -e GROQ_API_KEY=\"${GROQ_API_KEY:-}\"
         -e AI_ENVIRONMENT=\"${AI_ENVIRONMENT:-development}\"
         ..."
      ]
    }
  }
}
```

### How API Keys Are Loaded

1. **Host Environment**: VSCode reads from your shell environment
2. **Docker Container**: Environment variables are passed via `-e` flags
3. **MCP Server**: Uses the centralized config system to access keys

```python
# In stdio_mcp_server.py
from config import load_env_for_context
environment = os.getenv('AI_ENVIRONMENT', 'development')
load_env_for_context(environment)
```

## Security Features ✅

- **No hardcoded keys**: All API keys externalized via environment variables
- **Environment isolation**: Separate configs for dev/test/prod
- **Template-based setup**: Secure defaults with user-provided keys
- **Docker isolation**: Keys passed securely to container runtime

## Troubleshooting

### "API key not found" Error

1. **Check environment file exists:**

   ```bash
   ls -la config/.env.local
   ```

2. **Verify keys are set:**

   ```bash
   source config/.env.local
   echo $OPENAI_API_KEY  # Should show your key
   ```

3. **Restart VSCode** after changing environment variables

### Docker Container Issues

1. **Check container logs:**

   ```bash
   docker logs ai-filesystem-mcp-vscode
   ```

2. **Verify environment variables in container:**
   ```bash
   docker exec ai-filesystem-mcp-vscode env | grep API_KEY
   ```

## API Key Sources

- **OpenAI**: https://platform.openai.com/api-keys
- **Gemini**: https://aistudio.google.com/app/apikey
- **Anthropic**: https://console.anthropic.com/account/keys
- **Groq**: https://console.groq.com/keys

## Architecture Benefits

This approach maintains **Clean Architecture principles**:

- **High Cohesion**: Configuration management has single responsibility
- **Low Coupling**: MCP server depends on abstractions, not concrete API clients
- **Dependency Injection**: API keys injected via environment, not hardcoded
- **Security**: Keys externalized and never committed to source control
