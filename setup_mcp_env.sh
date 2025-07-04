#!/bin/bash
# Setup script for MCP server environment variables.
# This script helps configure API keys for the MCP server integration with VSCode.
# Follows KISS principle - simple setup for immediate productivity.

set -e  # Exit on any error

echo "🔧 AI FileSystem MCP Server - Environment Setup"
echo "=============================================="

# Check if .env.local exists
ENV_FILE="config/.env.local"
if [ ! -f "$ENV_FILE" ]; then
    echo "📝 Creating environment file from template..."
    
    if [ -f "config/env/.env.local.template" ]; then
        cp "config/env/.env.local.template" "$ENV_FILE"
        echo "✅ Created $ENV_FILE from template"
    else
        # Create basic .env.local if template doesn't exist
        cat > "$ENV_FILE" << 'EOF'
# AI FileSystem Agent - Local Environment Configuration
# Add your API keys below (at least one is required)

# OpenAI API Key (recommended for development)
OPENAI_API_KEY=

# Google Gemini API Key (alternative)
GEMINI_API_KEY=

# Anthropic Claude API Key (optional)
ANTHROPIC_API_KEY=

# Groq API Key (optional)
GROQ_API_KEY=

# Environment setting
AI_ENVIRONMENT=development
EOF
        echo "✅ Created basic $ENV_FILE"
    fi
else
    echo "✅ Environment file already exists: $ENV_FILE"
fi

echo ""
echo "🔑 API Key Configuration:"
echo "1. Edit $ENV_FILE"
echo "2. Add at least one API key (OPENAI_API_KEY recommended)"
echo "3. Save the file"
echo ""
echo "📋 Get API keys from:"
echo "  • OpenAI: https://platform.openai.com/api-keys"
echo "  • Gemini: https://aistudio.google.com/app/apikey"
echo "  • Anthropic: https://console.anthropic.com/account/keys"
echo "  • Groq: https://console.groq.com/keys"
echo ""

# Check if API keys are configured
echo "🔍 Checking current API key status..."

check_env_var() {
    if [ -n "${!1}" ]; then
        echo "  ✅ $1: Configured"
    else
        echo "  ❌ $1: Not set"
    fi
}

# Source the .env file if it exists
if [ -f "$ENV_FILE" ]; then
    set -a  # Export all variables
    source "$ENV_FILE"
    set +a  # Stop exporting
fi

check_env_var "OPENAI_API_KEY"
check_env_var "GEMINI_API_KEY"
check_env_var "ANTHROPIC_API_KEY"
check_env_var "GROQ_API_KEY"

echo ""
echo "🚀 Next steps:"
echo "1. Configure your API keys in $ENV_FILE"
echo "2. Restart VSCode to reload MCP configuration"
echo "3. Test the MCP tools in VSCode"
echo ""
echo "💡 Tip: The MCP server will automatically use your configured API keys"
echo "    when running in the Docker container."
