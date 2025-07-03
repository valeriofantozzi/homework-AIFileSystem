"""
Integration tests for CLI Chat Interface.

This module contains comprehensive tests for the CLI chat interface,
verifying all major functionality including conversation management,
debug features, and agent integration.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from chat_interface.cli_chat.chat import CLIChat, ConversationHistory
from config.model_config import ModelConfig
from agent.supervisor.supervisor import ModerationRequest, ModerationResponse, ModerationDecision


class TestConversationHistory:
    """Test the ConversationHistory class."""
    
    def test_init_without_session_file(self):
        """Test initialization without session file."""
        history = ConversationHistory()
        assert history.messages == []
        assert history.session_file is None
    
    def test_init_with_session_file(self):
        """Test initialization with session file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"messages": [{"role": "user", "content": "test"}]}')
            session_file = Path(f.name)
        
        try:
            history = ConversationHistory(session_file)
            assert len(history.messages) == 1
            assert history.messages[0]["role"] == "user"
        finally:
            session_file.unlink(missing_ok=True)
    
    def test_add_message(self):
        """Test adding messages to history."""
        history = ConversationHistory()
        
        history.add_message("user", "Hello")
        assert len(history.messages) == 1
        assert history.messages[0]["role"] == "user"
        assert history.messages[0]["content"] == "Hello"
        assert "timestamp" in history.messages[0]
    
    def test_get_recent_messages(self):
        """Test getting recent messages."""
        history = ConversationHistory()
        
        # Add more messages than limit
        for i in range(15):
            history.add_message("user", f"Message {i}")
        
        recent = history.get_recent_messages(10)
        assert len(recent) == 10
        assert recent[0]["content"] == "Message 5"  # Should start from message 5
        assert recent[-1]["content"] == "Message 14"  # Should end at message 14
    
    def test_clear_history(self):
        """Test clearing history."""
        history = ConversationHistory()
        history.add_message("user", "Hello")
        
        history.clear()
        assert len(history.messages) == 0


class TestCLIChat:
    """Test the CLIChat class."""
    
    @pytest.fixture
    def workspace_path(self):
        """Provide a temporary workspace directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def mock_model_config(self):
        """Provide a mock model configuration."""
        config = Mock(spec=ModelConfig)
        config.environment = "local"
        return config
    
    @pytest.fixture
    def cli_chat(self, workspace_path, mock_model_config):
        """Provide a CLI chat instance for testing."""
        with patch('chat_interface.cli_chat.chat.SecureAgent') as mock_agent, \
             patch('chat_interface.cli_chat.chat.RequestSupervisor') as mock_supervisor:
            
            # Configure mocks
            mock_agent_instance = Mock()
            mock_agent_instance.get_workspace_info.return_value = {
                'workspace_path': workspace_path,
                'model': 'test-model',
                'debug_mode': False,
                'available_tools': ['read_file', 'write_file']
            }
            mock_agent.return_value = mock_agent_instance
            
            mock_supervisor_instance = Mock()
            mock_supervisor.return_value = mock_supervisor_instance
            
            cli = CLIChat(
                workspace_path=workspace_path,
                debug_mode=False,
                model_config=mock_model_config
            )
            
            cli.agent = mock_agent_instance
            cli.supervisor = mock_supervisor_instance
            
            yield cli
    
    def test_init(self, workspace_path, mock_model_config):
        """Test CLI chat initialization."""
        with patch('chat_interface.cli_chat.chat.SecureAgent') as mock_agent, \
             patch('chat_interface.cli_chat.chat.RequestSupervisor') as mock_supervisor:
            
            cli = CLIChat(
                workspace_path=workspace_path,
                debug_mode=True,
                session_name="test_session",
                model_config=mock_model_config
            )
            
            assert str(cli.workspace_path) == workspace_path
            assert cli.debug_mode is True
            assert cli.model_config == mock_model_config
            
            # Check that session file path is set correctly
            expected_session_path = Path.home() / ".ai-fs-chat" / "sessions" / "test_session.json"
            assert cli.history.session_file == expected_session_path
    
    def test_handle_quit_command(self, cli_chat):
        """Test quit command handling."""
        result = cli_chat._handle_command("/quit")
        assert result is False
        
        result = cli_chat._handle_command("/exit")
        assert result is False
    
    def test_handle_debug_command(self, cli_chat):
        """Test debug command handling."""
        initial_debug = cli_chat.debug_mode
        
        result = cli_chat._handle_command("/debug")
        assert result is True
        assert cli_chat.debug_mode != initial_debug
        assert cli_chat.agent.debug_mode == cli_chat.debug_mode
    
    def test_handle_clear_command(self, cli_chat):
        """Test clear command handling with coordinated memory clearing."""
        # Add some messages first
        cli_chat.history.add_message("user", "test")
        assert len(cli_chat.history.messages) > 0
        
        # Set up conversation ID
        cli_chat._current_conversation_id = "test-conversation-123"
        
        # Mock the memory tools
        mock_clear_tool = Mock(return_value="Successfully cleared conversation memory for test-conversation-123")
        cli_chat.agent.file_tools = {'clear_conversation_memory': mock_clear_tool}
        
        with patch.object(cli_chat.console, 'print') as mock_print:
            result = cli_chat._handle_command("/clear")
            assert result is True
            assert len(cli_chat.history.messages) == 0
            
            # Verify new conversation ID was generated
            assert cli_chat._current_conversation_id != "test-conversation-123"
            
            # Verify memory tool was called
            mock_clear_tool.assert_called_once_with("test-conversation-123")
            
            # Verify success message was printed
            mock_print.assert_called_once()
            printed_message = mock_print.call_args[0][0]
            assert "CLI history cleared" in printed_message
            assert "Successfully cleared conversation memory" in printed_message
    
    def test_handle_unknown_command(self, cli_chat):
        """Test unknown command handling."""
        with patch.object(cli_chat.console, 'print') as mock_print:
            result = cli_chat._handle_command("/unknown")
            assert result is True
            mock_print.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_user_input_rejected(self, cli_chat):
        """Test user input processing when request is rejected."""
        # Mock supervisor to reject request
        mock_response = ModerationResponse(
            conversation_id="test-id",
            decision=ModerationDecision.REJECTED,
            allowed=False,
            reason="Test rejection",
            risk_factors=["test_risk"],
            intent=None
        )
        cli_chat.supervisor.moderate_request = AsyncMock(return_value=mock_response)
        
        with patch.object(cli_chat.console, 'print') as mock_print:
            result = await cli_chat._process_user_input("dangerous request")
            
            assert result is True  # Should continue chat
            assert len(cli_chat.history.messages) == 1  # Should log the rejection
            assert cli_chat.history.messages[0]["metadata"]["moderation"] == "rejected"
            mock_print.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_user_input_approved(self, cli_chat):
        """Test user input processing when request is approved."""
        # Mock supervisor to approve request
        mock_moderation_response = ModerationResponse(
            conversation_id="test-id",
            decision=ModerationDecision.ALLOWED,
            allowed=True,
            reason="Test approval",
            risk_factors=[],
            intent=None
        )
        cli_chat.supervisor.moderate_request = AsyncMock(return_value=mock_moderation_response)
        
        # Mock agent response
        mock_agent_response = Mock()
        mock_agent_response.conversation_id = "test-id"
        mock_agent_response.response = "Test response"
        mock_agent_response.tools_used = ["read_file"]
        mock_agent_response.success = True
        cli_chat.agent.process_query = AsyncMock(return_value=mock_agent_response)
        
        with patch.object(cli_chat, '_display_agent_response') as mock_display:
            result = await cli_chat._process_user_input("safe request")
            
            assert result is True
            assert len(cli_chat.history.messages) == 2  # User message + agent response
            assert cli_chat.history.messages[0]["role"] == "user"
            assert cli_chat.history.messages[1]["role"] == "agent"
            mock_display.assert_called_once_with(mock_agent_response)
    
    @pytest.mark.asyncio 
    async def test_process_user_input_error(self, cli_chat):
        """Test user input processing when an error occurs."""
        # Mock supervisor to raise exception
        cli_chat.supervisor.moderate_request = AsyncMock(side_effect=Exception("Test error"))
        
        with patch.object(cli_chat.console, 'print') as mock_print:
            result = await cli_chat._process_user_input("test input")
            
            assert result is True  # Should continue despite error
            mock_print.assert_called()


class TestCLIIntegration:
    """Integration tests for the CLI interface."""
    
    def test_cli_help_command(self):
        """Test that CLI help command works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test help via argument parsing
            import sys
            from chat_interface.cli_chat.chat import main
            
            # Mock sys.argv to simulate --help
            original_argv = sys.argv
            try:
                sys.argv = ['chat.py', '--help']
                # main() should exit with code 0 for help, but we'll catch SystemExit
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            finally:
                sys.argv = original_argv
    
    def test_cli_import_chain(self):
        """Test that all CLI imports work correctly."""
        # Test the complete import chain
        from chat_interface.cli_chat.chat import CLIChat, ConversationHistory, main
        from chat_interface.cli_chat import CLIChat as CLIChatFromModule
        
        assert CLIChat is not None
        assert ConversationHistory is not None
        assert main is not None
        assert CLIChatFromModule is CLIChat
    
    def test_cli_with_local_environment(self):
        """Test CLI creation with local environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                model_config = ModelConfig(environment='local')
                cli = CLIChat(
                    workspace_path=tmpdir,
                    debug_mode=True,
                    model_config=model_config
                )
                
                assert cli.workspace_path == Path(tmpdir)
                assert cli.debug_mode is True
                assert cli.model_config == model_config
                
            except Exception as e:
                # If environment is not set up, that's expected
                assert "api_key" in str(e).lower() or "environment" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
