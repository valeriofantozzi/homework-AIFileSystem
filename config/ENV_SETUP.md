# Environment Configuration Files

This directory contains template files for different deployment environments.

## Quick Start

1. **Copy the appropriate template for your environment:**

   ```bash
   # For local development
   cp config/env/.env.local.template config/.env.local

   # For development environment
   cp config/env/.env.development.template config/.env.development

   # For testing
   cp config/env/.env.testing.template config/.env.testing

   # For production
   cp config/env/.env.production.template config/.env.production
   ```

2. **Edit the copied file and add your API keys:**

   ```bash
   # Edit your environment file
   nano config/.env.local  # or your preferred editor
   ```

3. **Get your API keys from:**
   - **OpenAI**: https://platform.openai.com/api-keys
   - **Gemini**: https://aistudio.google.com/app/apikey
   - **Anthropic**: https://console.anthropic.com/account/keys
   - **Groq**: https://console.groq.com/keys

## Environment Files Overview

| File                                   | Purpose                 | API Keys Required               |
| -------------------------------------- | ----------------------- | ------------------------------- |
| `config/env/.env.local.template`       | Quick local development | OpenAI (minimum)                |
| `config/env/.env.development.template` | Full development setup  | OpenAI, Gemini, Anthropic, Groq |
| `config/env/.env.testing.template`     | Automated testing       | None (uses local models)        |
| `config/env/.env.production.template`  | Production deployment   | All providers                   |

## Security Guidelines

- **Never commit** actual `.env` files to version control
- **Use different API keys** for development vs production
- **Rotate keys regularly** in production
- **Monitor usage** to detect unauthorized access
- **Use environment-specific quotas** on your API keys

## Architecture Benefits

### High Cohesion ✅

- Each environment file has a single responsibility
- Clear separation between development, testing, and production concerns
- Environment-specific optimizations (cost, performance, security)

### Low Coupling ✅

- Environment configuration is independent of application code
- No hardcoded API keys or environment-specific logic
- Easy to switch between environments without code changes

### Security ✅

- API keys are externalized from codebase
- Environment isolation prevents production keys from being used in development
- Template files provide secure defaults and guidance

## Usage Examples

### Switching Environments

```python
from config import set_environment

# Switch to development mode
set_environment('development')

# Switch to testing mode (uses local models)
set_environment('testing')

# Switch to production mode
set_environment('production')
```

### Checking Configuration

```python
from config.env_loader import get_env_loader

loader = get_env_loader()
print(f"Current environment: {loader.get_current_environment()}")
print(f"API key status: {loader.validate_api_keys()}")
```

## Troubleshooting

### Missing API Keys

If you get API key errors:

1. Check that your `.env` file exists and has the correct keys
2. Verify the key format (OpenAI keys start with `sk-`)
3. Test the key with a simple API call
4. Check quotas and rate limits

### Environment Not Loading

If environment variables aren't loading:

1. Install python-dotenv: `pip install python-dotenv`
2. Check that your `.env` file is in the project root
3. Verify file permissions are readable
4. Check for syntax errors in the `.env` file

### Local Models Not Working

If local models fail:

1. Install Ollama: https://ollama.ai/
2. Pull required models: `ollama pull llama3.2:3b`
3. Start Ollama service: `ollama serve`
4. Install Gemini CLI if needed

## Cost Optimization

### Development Environment

- Uses faster, cheaper models by default
- Enables request caching
- Limits token usage per request
- Prefers local models when available

### Testing Environment

- Uses local models by default
- Minimal API calls
- Mock responses for unit tests
- No cost for automated testing

### Production Environment

- Uses best models for quality
- Enables cost tracking and alerts
- Implements rate limiting
- Monitors usage and performance
