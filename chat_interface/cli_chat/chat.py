"""
Command-line chat interface for the AI File System Agent.

This module provides an interactive terminal-based chat interface that allows
users to converse with the AI agent. It features colorized output, conversation
history, debug mode, and session persistence.
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from rich.console import Console
from rich.live import Live  
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.core.secure_agent import SecureAgent
from agent.supervisor.supervisor import RequestSupervisor, ModerationRequest
from config.model_config import ModelConfig


class ConversationHistory:
    """Manages conversation history with persistence."""
    
    def __init__(self, session_file: Optional[Path] = None):
        """
        Initialize conversation history.
        
        Args:
            session_file: Optional file path for session persistence
        """
        self.messages: List[Dict[str, Any]] = []
        self.session_file = session_file
        self.console = Console()
        
        if session_file and session_file.exists():
            self._load_session()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        
        if self.session_file:
            self._save_session()
    
    def _load_session(self):
        """Load conversation history from file."""
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.messages = data.get('messages', [])
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.console.print(f"[yellow]Warning: Could not load session file: {e}[/yellow]")
    
    def _save_session(self):
        """Save conversation history to file."""
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "messages": self.messages,
                    "created": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            self.console.print(f"[red]Error saving session: {e}[/red]")
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent messages."""
        return self.messages[-limit:] if self.messages else []
    
    def clear(self):
        """Clear conversation history."""
        self.messages.clear()
        if self.session_file and self.session_file.exists():
            self.session_file.unlink()


class CLIChat:
    """
    Command-line chat interface for AI File System Agent.
    
    Provides an interactive terminal interface with features like colorized output,
    conversation history, debug mode, and session persistence. Follows Clean
    Architecture principles with high cohesion and proper separation of concerns.
    """
    
    def __init__(
        self,
        workspace_path: str,
        debug_mode: bool = False,
        session_name: Optional[str] = None,
        model_config: Optional[ModelConfig] = None
    ):
        """
        Initialize CLI chat interface.
        
        Args:
            workspace_path: Path to the agent's workspace directory
            debug_mode: Enable debug output showing reasoning steps
            session_name: Name for session persistence file
            model_config: Model configuration instance
        """
        self.workspace_path = Path(workspace_path)
        self.debug_mode = debug_mode  
        self.console = Console()
        self.logger = structlog.get_logger(__name__)
        
        # Initialize conversation history
        session_file = None
        if session_name:
            sessions_dir = Path.home() / ".ai-fs-chat" / "sessions"
            session_file = sessions_dir / f"{session_name}.json"
        
        self.history = ConversationHistory(session_file)
        
        # Initialize model configuration and agent components
        self.model_config = model_config or ModelConfig()
        
        # Initialize supervisor for request validation
        self.supervisor = RequestSupervisor(logger=self.logger)
        
        # Initialize main agent
        self.agent = SecureAgent(
            workspace_path=str(self.workspace_path),
            model_config=self.model_config,
            debug_mode=debug_mode
        )
        
        self.logger.info(
            "CLI Chat initialized",
            workspace_path=str(self.workspace_path),
            debug_mode=debug_mode,
            session_name=session_name
        )
    
    def _print_welcome(self):
        """Print welcome message and agent information."""
        workspace_info = self.agent.get_workspace_info()
        
        # Create welcome panel
        welcome_text = Text()
        welcome_text.append("🤖 AI File System Agent\n", style="bold blue")
        welcome_text.append("Interactive chat interface for secure file operations\n\n", style="dim")
        welcome_text.append(f"Workspace: {workspace_info['workspace_path']}\n", style="green")
        welcome_text.append(f"Model: {workspace_info['model']}\n", style="cyan")
        welcome_text.append(f"Debug Mode: {'ON' if self.debug_mode else 'OFF'}\n", style="yellow" if self.debug_mode else "dim")
        
        welcome_panel = Panel(
            welcome_text,
            title="Welcome",
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(welcome_panel)
        
        # Print available commands
        commands_table = Table(title="Available Commands", border_style="dim")
        commands_table.add_column("Command", style="cyan", width=15)
        commands_table.add_column("Description", style="white")
        
        commands_table.add_row("/help", "Show this help message")
        commands_table.add_row("/debug", "Toggle debug mode")
        commands_table.add_row("/history", "Show conversation history")
        commands_table.add_row("/clear", "Clear conversation history")
        commands_table.add_row("/workspace", "Show workspace information")
        commands_table.add_row("/quit", "Exit the chat")
        
        self.console.print(commands_table)
        self.console.print()
    
    def _handle_command(self, command: str) -> bool:
        """
        Handle special commands.
        
        Args:
            command: The command to handle
            
        Returns:
            True if should continue, False to exit
        """
        command = command.lower().strip()
        
        if command == "/quit" or command == "/exit":
            self.console.print("[yellow]Goodbye! 👋[/yellow]")
            return False
        
        elif command == "/help":
            self._print_welcome()
        
        elif command == "/debug":
            self.debug_mode = not self.debug_mode
            self.agent.debug_mode = self.debug_mode
            status = "ON" if self.debug_mode else "OFF"
            self.console.print(f"[yellow]Debug mode: {status}[/yellow]")
        
        elif command == "/history":
            self._show_history()
        
        elif command == "/clear":
            self.history.clear()
            self.console.print("[green]Conversation history cleared[/green]")
        
        elif command == "/workspace":
            self._show_workspace_info()
        
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self.console.print("[dim]Type /help for available commands[/dim]")
        
        return True
    
    def _show_history(self):
        """Display conversation history."""
        recent_messages = self.history.get_recent_messages(20)
        
        if not recent_messages:
            self.console.print("[dim]No conversation history[/dim]")
            return
        
        history_panel = Panel(
            "Recent conversation history",
            title="History", 
            border_style="dim"
        )
        self.console.print(history_panel)
        
        for msg in recent_messages:
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
            role_color = "blue" if msg['role'] == 'user' else "green"
            
            self.console.print(f"[{role_color}]{msg['role'].capitalize()}[/{role_color}] [dim]({timestamp}):[/dim]")
            self.console.print(msg['content'])
            self.console.print()
    
    def _show_workspace_info(self):
        """Display workspace information."""
        workspace_info = self.agent.get_workspace_info()
        
        info_table = Table(title="Workspace Information", border_style="blue")
        info_table.add_column("Property", style="cyan", width=20)
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Workspace Path", workspace_info['workspace_path'])
        info_table.add_row("Model", workspace_info['model'])
        info_table.add_row("Debug Mode", str(workspace_info['debug_mode']))
        info_table.add_row("Available Tools", ", ".join(workspace_info['available_tools']))
        
        self.console.print(info_table)
    
    def _display_user_message(self, message: str):
        """Display user message with formatting."""
        user_panel = Panel(
            message,
            title="You",
            border_style="blue",
            title_align="left"
        )
        self.console.print(user_panel)
    
    def _display_agent_response(self, response: Any):
        """Display agent response with rich formatting."""
        if not response.success:
            # Display error response
            error_panel = Panel(
                f"❌ {response.response}",
                title="Agent Error",
                border_style="red",
                title_align="left"
            )
            self.console.print(error_panel)
            return
        
        # Display successful response
        response_panel = Panel(
            Markdown(response.response),
            title="🤖 Agent",
            border_style="green",
            title_align="left"
        )
        self.console.print(response_panel)
        
        # Display tools used if any
        if response.tools_used:
            tools_text = ", ".join(response.tools_used)
            self.console.print(f"[dim]🔧 Tools used: {tools_text}[/dim]")
        
        # Display reasoning steps in debug mode
        if self.debug_mode and response.reasoning_steps:
            self._display_reasoning_steps(response.reasoning_steps)
    
    def _display_reasoning_steps(self, reasoning_steps: List[Dict[str, Any]]):
        """Display reasoning steps in debug mode."""
        debug_panel = Panel(
            "Agent Reasoning Process",
            title="🧠 Debug: Reasoning Steps",
            border_style="yellow"
        )
        self.console.print(debug_panel)
        
        for i, step in enumerate(reasoning_steps, 1):
            # Use 'phase' field from ReAct loop instead of 'type'
            step_type = step.get('phase', step.get('type', 'unknown')).lower()
            content = step.get('content', '')
            
            # Color code different step types
            if step_type == 'think':
                style = "cyan"
                icon = "💭"
            elif step_type == 'act':
                style = "yellow"
                icon = "⚡"
            elif step_type == 'observe':
                style = "green" 
                icon = "👀"
            else:
                style = "white"
                icon = "❓"
            
            self.console.print(f"[{style}]{icon} Step {i} ({step_type.upper()}):[/{style}]")
            
            if step_type == 'act' and ('tool_name' in step or 'tool' in step):
                # Display tool call details - check both field names for compatibility
                tool_name = step.get('tool_name', step.get('tool', 'unknown'))
                tool_args = step.get('tool_args', step.get('args', {}))
                self.console.print(f"  Tool: [bold]{tool_name}[/bold]")
                if tool_args:
                    args_json = json.dumps(tool_args, indent=2)
                    syntax = Syntax(args_json, "json", theme="monokai", line_numbers=False)
                    self.console.print(syntax)
            else:
                self.console.print(f"  {content}")
            
            self.console.print()
    
    async def _process_user_input(self, user_input: str) -> bool:
        """
        Process user input through supervisor and agent.
        
        Args:
            user_input: The user's input message
            
        Returns:
            True to continue chat, False to exit
        """
        try:
            # First check with supervisor for safety and intent extraction
            self.console.print("[dim]🔍 Validating request...[/dim]")
            
            # Get or create conversation ID for memory tracking
            conversation_id = getattr(self, '_current_conversation_id', None)
            if conversation_id is None:
                import uuid
                conversation_id = str(uuid.uuid4())
                self._current_conversation_id = conversation_id
            
            # Get conversation context for ambiguous response detection
            conversation_context = None
            if hasattr(self.agent, 'file_tools') and 'get_conversation_context' in self.agent.file_tools:
                try:
                    conversation_context = self.agent.file_tools['get_conversation_context'](conversation_id)
                except Exception as e:
                    self.logger.warning("Failed to get conversation context", error=str(e))
            
            # Create moderation request with context
            moderation_request = ModerationRequest(
                user_query=user_input,
                conversation_id=conversation_id,
                conversation_context=conversation_context
            )
            
            moderation_response = await self.supervisor.moderate_request(moderation_request)
            
            if not moderation_response.allowed:
                # Request was rejected by supervisor
                rejection_panel = Panel(
                    f"❌ {moderation_response.reason}",
                    title="Request Rejected",
                    border_style="red"
                )
                self.console.print(rejection_panel)
                
                # Log rejection
                self.history.add_message(
                    "user", user_input, 
                    {"moderation": "rejected", "reason": moderation_response.reason}
                )
                return True
            
            # Request approved, process with agent
            self.console.print("[dim]✅ Request approved, processing...[/dim]")
            
            # Store user message
            self.history.add_message("user", user_input)
            
            # Process with agent using conversation context
            if hasattr(self.agent, 'process_query_with_conversation'):
                response = await self.agent.process_query_with_conversation(user_input, conversation_id)
            else:
                # Fallback for agents without memory support
                response = await self.agent.process_query(user_input)
            
            # Display response
            self._display_agent_response(response)
            
            # Store agent response
            self.history.add_message(
                "agent", 
                response.response,
                {
                    "conversation_id": response.conversation_id,
                    "tools_used": response.tools_used,
                    "success": response.success
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Error processing user input", error=str(e))
            error_panel = Panel(
                f"An unexpected error occurred: {str(e)}",
                title="System Error",
                border_style="red"
            )
            self.console.print(error_panel)
            return True
    
    async def run(self):
        """Run the interactive chat loop."""
        self._print_welcome()
        
        self.console.print("[dim]Type your message and press Enter. Use /help for commands.[/dim]")
        self.console.print()
        
        try:
            while True:
                # Get user input
                try:
                    user_input = Prompt.ask(
                        "[bold blue]You[/bold blue]",
                        console=self.console
                    ).strip()
                except (KeyboardInterrupt, EOFError):
                    self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
                    break
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    if not self._handle_command(user_input):
                        break
                    continue
                
                # Display user message
                self._display_user_message(user_input)
                
                # Process with agent
                should_continue = await self._process_user_input(user_input)
                if not should_continue:
                    break
                
                self.console.print()  # Add spacing between interactions
                
        except Exception as e:
            self.logger.error("Chat loop error", error=str(e))
            self.console.print(f"[red]Chat error: {str(e)}[/red]")
        
        finally:
            self.console.print("[dim]Chat session ended.[/dim]")


def main():
    """Main entry point for CLI chat interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI File System Agent - CLI Chat Interface")
    parser.add_argument(
        "--workspace", "-w",
        type=str,
        default="./sandbox",
        help="Path to the agent workspace directory (default: ./sandbox)"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode to show reasoning steps"
    )
    parser.add_argument(
        "--session", "-s",
        type=str,
        help="Session name for conversation persistence"
    )
    parser.add_argument(
        "--env", "-e",
        type=str,
        default="development",
        help="Environment configuration to use (default: development)"
    )
    
    args = parser.parse_args()
    
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    try:
        # Initialize model configuration
        model_config = ModelConfig(environment=args.env)
        
        # Create and run chat interface
        chat = CLIChat(
            workspace_path=args.workspace,
            debug_mode=args.debug,
            session_name=args.session,
            model_config=model_config
        )
        
        # Run the chat loop
        asyncio.run(chat.run())
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Failed to start chat interface: {str(e)}[/red]")
        console.print(f"[dim]Error details: {type(e).__name__}[/dim]")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
