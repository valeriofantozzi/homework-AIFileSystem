import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from chat_interface.cli_chat.chat import ConversationHistory, CLIChat

# ---------------------------
# ConversationHistory Tests
# ---------------------------

def test_add_message_and_persistence(tmp_path):
    session_file = tmp_path / "session.json"
    history = ConversationHistory(session_file=session_file)
    history.add_message("user", "Hello!", {"foo": "bar"})
    assert len(history.messages) == 1
    assert history.messages[0]["role"] == "user"
    assert history.messages[0]["content"] == "Hello!"
    assert history.messages[0]["metadata"]["foo"] == "bar"
    # File should exist and contain the message
    assert session_file.exists()
    with open(session_file) as f:
        data = json.load(f)
    assert data["messages"][0]["content"] == "Hello!"

def test_get_recent_messages_limit(tmp_path):
    history = ConversationHistory()
    for i in range(15):
        history.add_message("user", f"msg{i}")
    recent = history.get_recent_messages(10)
    assert len(recent) == 10
    assert recent[0]["content"] == "msg5"
    assert recent[-1]["content"] == "msg14"

def test_clear_history_and_file(tmp_path):
    session_file = tmp_path / "session.json"
    history = ConversationHistory(session_file=session_file)
    history.add_message("user", "test")
    assert len(history.messages) == 1
    assert session_file.exists()
    history.clear()
    assert history.messages == []
    assert not session_file.exists()

# ---------------------------
# CLIChat Tests (with mocks)
# ---------------------------

@pytest.fixture
def cli_chat_mocks():
    with patch("chat_interface.cli_chat.chat.Console") as MockConsole, \
         patch("chat_interface.cli_chat.chat.SecureAgent") as MockAgent, \
         patch("chat_interface.cli_chat.chat.RequestSupervisor") as MockSupervisor, \
         patch("chat_interface.cli_chat.chat.ModelConfig") as MockModelConfig:
        yield {
            "Console": MockConsole,
            "SecureAgent": MockAgent,
            "RequestSupervisor": MockSupervisor,
            "ModelConfig": MockModelConfig,
        }

def make_cli_chat(cli_chat_mocks):
    # Use a dummy workspace path and session name
    chat = CLIChat(
        workspace_path=".",
        debug_mode=False,
        session_name=None,
        model_config=cli_chat_mocks["ModelConfig"].return_value
    )
    chat.console = MagicMock()
    chat.logger = MagicMock()
    chat.agent = MagicMock()
    chat.supervisor = MagicMock()
    chat.history = ConversationHistory()
    return chat

def test_handle_known_commands(cli_chat_mocks):
    chat = make_cli_chat(cli_chat_mocks)
    # /help should call _print_welcome
    chat._print_welcome = MagicMock()
    assert chat._handle_command("/help") is True
    chat._print_welcome.assert_called_once()
    # /debug toggles debug_mode
    chat.agent.debug_mode = False
    chat.debug_mode = False
    chat.console.print.reset_mock()
    assert chat._handle_command("/debug") is True
    assert chat.debug_mode is True
    # /history calls _show_history
    chat._show_history = MagicMock()
    assert chat._handle_command("/history") is True
    chat._show_history.assert_called_once()
    # /workspace calls _show_workspace_info
    chat._show_workspace_info = MagicMock()
    assert chat._handle_command("/workspace") is True
    chat._show_workspace_info.assert_called_once()
    # /quit returns False
    assert chat._handle_command("/quit") is False

def test_handle_unknown_command(cli_chat_mocks):
    chat = make_cli_chat(cli_chat_mocks)
    chat.console.print.reset_mock()
    assert chat._handle_command("/unknown") is True
    # Should print error about unknown command
    assert chat.console.print.call_count >= 2

def test_clear_all_conversation_data_coordination(cli_chat_mocks):
    chat = make_cli_chat(cli_chat_mocks)
    chat.history.add_message("user", "test")
    chat._current_conversation_id = "cid"
    # Mock agent.file_tools with clear_conversation_memory
    clear_mock = MagicMock(return_value="cleared")
    chat.agent.file_tools = {"clear_conversation_memory": clear_mock}
    result = chat._clear_all_conversation_data()
    assert "Cleared 1 messages" in result
    assert "Memory: cleared" in result
    clear_mock.assert_called_once_with("cid")
    # After clear, conversation id should be new
    assert chat._current_conversation_id != "cid"

@pytest.mark.asyncio
async def test_process_user_input_moderation_rejects(cli_chat_mocks):
    chat = make_cli_chat(cli_chat_mocks)
    # Mock supervisor.moderate_request to reject
    mod_resp = MagicMock()
    mod_resp.allowed = False
    mod_resp.reason = "Not allowed"
    chat.supervisor.moderate_request = AsyncMock(return_value=mod_resp)
    chat.console.print = MagicMock()
    # Should return True (continue), print rejection, and add message with moderation
    result = await chat._process_user_input("bad input")
    assert result is True
    assert chat.console.print.call_count >= 1
    assert chat.history.messages[-1]["metadata"]["moderation"] == "rejected"

@pytest.mark.asyncio
async def test_process_user_input_agent_success(cli_chat_mocks):
    chat = make_cli_chat(cli_chat_mocks)
    # Mock supervisor.moderate_request to allow
    mod_resp = MagicMock()
    mod_resp.allowed = True
    chat.supervisor.moderate_request = AsyncMock(return_value=mod_resp)
    # Mock agent.process_query_with_conversation to return a response
    agent_resp = MagicMock()
    agent_resp.success = True
    agent_resp.response = "Agent says hi"
    agent_resp.tools_used = ["tool1"]
    agent_resp.reasoning_steps = [{"phase": "think", "content": "thinking"}]
    agent_resp.conversation_id = "cid"
    chat.agent.process_query_with_conversation = AsyncMock(return_value=agent_resp)
    chat.console.print = MagicMock()
    # Should return True (continue), print agent response, and add agent message
    result = await chat._process_user_input("hello")
    assert result is True
    assert chat.console.print.call_count >= 1
    assert chat.history.messages[-1]["role"] == "agent"
    assert chat.history.messages[-1]["content"] == "Agent says hi"
