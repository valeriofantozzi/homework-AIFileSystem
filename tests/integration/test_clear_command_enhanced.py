"""
Integration tests for the enhanced clear command functionality.

Tests the coordinated clearing of both CLI history and memory tools,
ensuring proper synchronization and error handling.
"""

import pytest
import asyncio
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from chat_interface.cli_chat.chat import CLIChat, ConversationHistory
from config.model_config import ModelConfig
from agent.core.secure_agent import SecureAgent


class TestClearCommandEnhanced:
    """Test enhanced clear command functionality."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_config(self):
        """Create mock model configuration."""
        config = Mock(spec=ModelConfig)
        config.get_model_config.return_value = {
            'provider': 'openai',
            'model': 'gpt-4',
            'temperature': 0.7
        }
        return config

    @pytest.fixture
    def cli_chat_with_history(self, temp_workspace, mock_config):
        """Create CLI chat instance with some conversation history."""
        with patch('chat_interface.cli_chat.chat.SecureAgent') as mock_agent_class:
            # Mock SecureAgent
            mock_agent = Mock(spec=SecureAgent)
            mock_agent.get_workspace_info.return_value = {
                'workspace_path': temp_workspace,
                'model': 'openai:gpt-4',
                'debug_mode': False,
                'available_tools': ['test_tool']
            }
            
            # Mock memory tools
            mock_memory_tools = {
                'clear_conversation_memory': Mock(return_value="Successfully cleared conversation memory for test-id"),
                'get_conversation_context': Mock(return_value=None),
                'store_interaction': Mock(return_value="Interaction stored")
            }
            mock_agent.file_tools = mock_memory_tools
            mock_agent_class.return_value = mock_agent

            # Mock supervisor
            with patch('chat_interface.cli_chat.chat.RequestSupervisor') as mock_supervisor:
                mock_supervisor_instance = Mock()
                mock_supervisor.return_value = mock_supervisor_instance

                cli = CLIChat(
                    workspace_path=temp_workspace,
                    debug_mode=True,
                    model_config=mock_config
                )
                
                # Add some test messages
                cli.history.add_message("user", "Hello, how are you?")
                cli.history.add_message("agent", "I'm doing well, thank you!")
                cli.history.add_message("user", "Can you help me with files?")
                cli.history.add_message("agent", "Of course! I can help with file operations.")
                
                # Set a conversation ID
                cli._current_conversation_id = "test-conversation-123"
                
                yield cli

    def test_clear_command_with_confirmation_yes(self, cli_chat_with_history):
        """Test clear command when user confirms the operation."""
        cli = cli_chat_with_history
        initial_message_count = len(cli.history.messages)
        initial_conversation_id = cli._current_conversation_id
        
        # Mock user confirmation to 'yes'
        with patch('rich.prompt.Prompt.ask', return_value='y'):
            result = cli._handle_command('/clear')
        
        # Verify command executed successfully
        assert result is True
        
        # Verify CLI history was cleared
        assert len(cli.history.messages) == 0
        
        # Verify new conversation ID was generated
        assert cli._current_conversation_id != initial_conversation_id
        assert cli._current_conversation_id is not None
        
        # Verify memory tools clear function was called
        clear_memory_tool = cli.agent.file_tools['clear_conversation_memory']
        clear_memory_tool.assert_called_once_with("test-conversation-123")

    def test_clear_command_with_confirmation_no(self, cli_chat_with_history):
        """Test clear command when user cancels the operation."""
        cli = cli_chat_with_history
        initial_message_count = len(cli.history.messages)
        initial_conversation_id = cli._current_conversation_id
        
        # Mock user confirmation to 'no'
        with patch('rich.prompt.Prompt.ask', return_value='n'):
            result = cli._handle_command('/clear')
        
        # Verify command executed successfully but didn't clear
        assert result is True
        
        # Verify CLI history was NOT cleared
        assert len(cli.history.messages) == initial_message_count
        
        # Verify conversation ID was NOT changed
        assert cli._current_conversation_id == initial_conversation_id
        
        # Verify memory tools clear function was NOT called
        clear_memory_tool = cli.agent.file_tools['clear_conversation_memory']
        clear_memory_tool.assert_not_called()

    def test_clear_command_with_empty_history(self, cli_chat_with_history):
        """Test clear command when history is already empty."""
        cli = cli_chat_with_history
        
        # Clear history first
        cli.history.clear()
        assert len(cli.history.messages) == 0
        
        # Set conversation ID
        old_conversation_id = "test-conv-456"
        cli._current_conversation_id = old_conversation_id
        
        # Call clear command (should not prompt for confirmation)
        result = cli._handle_command('/clear')
        
        # Verify command executed successfully
        assert result is True
        
        # Verify new conversation ID was still generated
        assert cli._current_conversation_id != old_conversation_id
        assert cli._current_conversation_id is not None

    def test_clear_all_conversation_data_direct_call(self, cli_chat_with_history):
        """Test the _clear_all_conversation_data method directly."""
        cli = cli_chat_with_history
        initial_message_count = len(cli.history.messages)
        
        # Call the clear method directly
        result_message = cli._clear_all_conversation_data()
        
        # Verify result message format
        assert "✅" in result_message
        assert f"Cleared {initial_message_count} messages" in result_message
        assert "Memory: Successfully cleared conversation memory" in result_message
        assert "New conversation started" in result_message
        
        # Verify state changes
        assert len(cli.history.messages) == 0
        assert cli._current_conversation_id is not None

    def test_clear_with_memory_tool_error(self, cli_chat_with_history):
        """Test clear command when memory tool clearing fails."""
        cli = cli_chat_with_history
        
        # Make memory tool raise an exception
        cli.agent.file_tools['clear_conversation_memory'].side_effect = Exception("Memory error")
        
        result_message = cli._clear_all_conversation_data()
        
        # Verify CLI history was still cleared
        assert len(cli.history.messages) == 0
        
        # Verify error was handled gracefully
        assert "✅" in result_message
        assert "Memory clearing failed: Memory error" in result_message
        assert cli._current_conversation_id is not None

    def test_clear_without_memory_tools(self, temp_workspace, mock_config):
        """Test clear command when agent doesn't have memory tools."""
        with patch('chat_interface.cli_chat.chat.SecureAgent') as mock_agent_class:
            # Mock SecureAgent without memory tools
            mock_agent = Mock(spec=SecureAgent)
            mock_agent.get_workspace_info.return_value = {
                'workspace_path': temp_workspace,
                'model': 'openai:gpt-4',
                'debug_mode': False,
                'available_tools': []
            }
            # No file_tools attribute
            del mock_agent.file_tools
            mock_agent_class.return_value = mock_agent

            with patch('chat_interface.cli_chat.chat.RequestSupervisor'):
                cli = CLIChat(
                    workspace_path=temp_workspace,
                    debug_mode=False,
                    model_config=mock_config
                )
                
                # Add some messages
                cli.history.add_message("user", "test message")
                cli._current_conversation_id = "test-id"
                
                result_message = cli._clear_all_conversation_data()
                
                # Verify CLI history was cleared
                assert len(cli.history.messages) == 0
                
                # Verify appropriate message for no memory tools
                assert "✅" in result_message
                assert "No active conversation to clear from memory" in result_message

    def test_clear_with_session_file(self, temp_workspace, mock_config):
        """Test clear command with session file persistence."""
        session_file = Path(temp_workspace) / "test_session.json"
        
        with patch('chat_interface.cli_chat.chat.SecureAgent') as mock_agent_class:
            mock_agent = Mock(spec=SecureAgent)
            mock_agent.get_workspace_info.return_value = {
                'workspace_path': temp_workspace,
                'model': 'openai:gpt-4',
                'debug_mode': False,
                'available_tools': []
            }
            mock_agent_class.return_value = mock_agent

            with patch('chat_interface.cli_chat.chat.RequestSupervisor'):
                # Create conversation history with session file
                history = ConversationHistory(session_file=session_file)
                history.add_message("user", "test message")
                
                # Verify session file was created
                assert session_file.exists()
                
                # Clear the history
                history.clear()
                
                # Verify session file was removed
                assert not session_file.exists()
                assert len(history.messages) == 0

    def test_conversation_id_tracking(self, cli_chat_with_history):
        """Test that conversation ID is properly tracked and regenerated."""
        cli = cli_chat_with_history
        
        # Initial state
        old_id = cli._current_conversation_id
        assert old_id is not None
        
        # Clear conversation
        result_message = cli._clear_all_conversation_data()
        
        # Verify new ID was generated
        new_id = cli._current_conversation_id
        assert new_id is not None
        assert new_id != old_id
        
        # Verify the ID looks like a UUID
        uuid.UUID(new_id)  # Should not raise exception if valid UUID

    def test_logging_during_clear_operation(self, cli_chat_with_history):
        """Test that proper logging occurs during clear operation."""
        cli = cli_chat_with_history
        
        with patch.object(cli.logger, 'info') as mock_log_info, \
             patch.object(cli.logger, 'error') as mock_log_error:
            
            cli._clear_all_conversation_data()
            
            # Verify logging calls were made
            assert mock_log_info.call_count >= 2  # At least start and completion logs
            
            # Verify no errors were logged
            mock_log_error.assert_not_called()
