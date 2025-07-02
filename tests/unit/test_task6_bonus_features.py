"""
Tests for Task 6 - Bonus Features implementation.

Tests enhanced safety features, lightweight model processing,
and structured error handling improvements.
"""
import pytest
import tempfile
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from agent.core.exceptions import (
    AgentError, AgentInitializationError, ModelConfigurationError,
    ToolExecutionError, ReasoningError, SafetyViolationError,
    ConversationError, RateLimitError, ErrorFormatter
)
from agent.supervisor.supervisor import (
    RequestSupervisor, ModerationRequest, ModerationResponse,
    SafetyRisk, ContentFilterResult
)
from agent.core.secure_agent import SecureAgent


class TestEnhancedExceptions:
    """Test the enhanced exception system."""
    
    def test_agent_error_base_functionality(self):
        """Test AgentError base class functionality."""
        error = AgentError(
            message="Test error",
            error_code="TEST_ERROR",
            recovery_suggestions=["Try again", "Check settings"],
            context={"test": "value"}
        )
        
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert len(error.recovery_suggestions) == 2
        assert error.context["test"] == "value"
        
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "AgentError"
        assert error_dict["message"] == "Test error"
    
    def test_tool_execution_error_with_specific_suggestions(self):
        """Test ToolExecutionError provides tool-specific suggestions."""
        error = ToolExecutionError(
            message="File not found",
            tool_name="read_file",
            tool_args={"filename": "missing.txt"}
        )
        
        # Should include tool-specific suggestions
        suggestions = error.recovery_suggestions
        assert any("list_files" in suggestion for suggestion in suggestions)
        assert error.context["tool_name"] == "read_file"
    
    def test_error_formatter_user_display(self):
        """Test error formatting for user display."""
        error = AgentError(
            message="Test error",
            recovery_suggestions=["Suggestion 1", "Suggestion 2"]
        )
        
        formatted = ErrorFormatter.format_error_for_user(error)
        assert "❌ **Error**: Test error" in formatted
        assert "💡 **Suggestions**:" in formatted
        assert "1. Suggestion 1" in formatted
        assert "2. Suggestion 2" in formatted
    
    def test_error_formatter_debug_display(self):
        """Test error formatting for debug display."""
        error = AgentError(
            message="Test error",
            error_code="TEST_ERROR",
            context={"debug": "info"}
        )
        
        formatted = ErrorFormatter.format_error_for_debug(error)
        assert "❌ **Error**: Test error" in formatted
        assert "📋 **Code**: TEST_ERROR" in formatted
        assert "🔍 **Context**:" in formatted
        assert "debug: info" in formatted


class TestEnhancedSafety:
    """Test enhanced safety features."""
    
    def test_content_filter_path_traversal_detection(self):
        """Test content filter detects path traversal attempts."""
        supervisor = RequestSupervisor(logger=Mock())
        
        dangerous_queries = [
            "read ../../../etc/passwd",
            "show me the file in ../config",
            "access /etc/shadow file"
        ]
        
        for query in dangerous_queries:
            result = supervisor.filter_content(query)
            assert not result.is_safe
            assert SafetyRisk.PATH_TRAVERSAL in result.detected_risks
            assert len(result.suggested_alternatives) > 0
    
    def test_content_filter_malicious_code_detection(self):
        """Test content filter detects malicious code attempts."""
        supervisor = RequestSupervisor(logger=Mock())
        
        malicious_queries = [
            "run rm -rf *",
            "execute del /s files",
            "format the drive"
        ]
        
        for query in malicious_queries:
            result = supervisor.filter_content(query)
            assert not result.is_safe
            assert SafetyRisk.MALICIOUS_CODE in result.detected_risks
    
    def test_content_filter_safe_queries(self):
        """Test content filter allows safe file operations."""
        supervisor = RequestSupervisor(logger=Mock())
        
        safe_queries = [
            "read the config file",
            "list all files in workspace",
            "write content to notes.txt",
            "what files are available?"
        ]
        
        for query in safe_queries:
            result = supervisor.filter_content(query)
            assert result.is_safe
            assert len(result.detected_risks) == 0
    
    def test_enhanced_rejection_response(self):
        """Test enhanced rejection responses with detailed explanations."""
        supervisor = RequestSupervisor(logger=Mock())
        
        request = ModerationRequest(
            user_query="read ../sensitive/file.txt",
            conversation_id="test-123"
        )
        
        filter_result = ContentFilterResult(
            is_safe=False,
            confidence=0.9,
            detected_risks=[SafetyRisk.PATH_TRAVERSAL],
            explanation="Path traversal attempt detected",
            suggested_alternatives=["Use simple filenames", "Work within workspace"]
        )
        
        response = supervisor._create_enhanced_rejection_response(request, filter_result)
        
        assert not response.allowed
        assert "🚫 Request rejected" in response.reason
        assert "📋 Specific concerns:" in response.reason
        assert "💡 Try instead:" in response.reason
        assert "attempts to access files outside workspace" in response.reason


class TestLightweightModelEnhancements:
    """Test enhanced lightweight model processing."""
    
    @pytest.mark.asyncio
    async def test_two_phase_processing_fast_rejection(self):
        """Test fast rejection path bypasses AI processing."""
        supervisor = RequestSupervisor(logger=Mock())
        supervisor.agent = AsyncMock()  # Mock AI agent
        
        # High-confidence malicious request
        request = ModerationRequest(
            user_query="rm -rf / --no-preserve-root",
            conversation_id="test-123"
        )
        
        response = await supervisor.moderate_request(request)
        
        # Should be rejected without calling AI agent
        assert not response.allowed
        assert response.decision.value == "rejected"  
        # AI agent should not have been called due to fast rejection
        supervisor.agent.run.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ai_fallback_on_uncertainty(self):
        """Test AI processing for uncertain content."""
        supervisor = RequestSupervisor(logger=Mock())
        supervisor.agent = AsyncMock()
        supervisor.agent.run.return_value = Mock(data={
            "decision": "allowed",
            "allowed": True,
            "intent": {
                "intent_type": "file_read",
                "confidence": 0.8,
                "parameters": {},
                "tools_needed": ["read_file"]
            },
            "reason": "Safe file operation",
            "risk_factors": []
        })
        
        # Ambiguous request that needs AI analysis
        request = ModerationRequest(
            user_query="show me the contents",
            conversation_id="test-123"
        )
        
        response = await supervisor.moderate_request(request)
        
        # Should be processed by AI agent
        supervisor.agent.run.assert_called_once()
        assert response.allowed
    
    @pytest.mark.asyncio
    async def test_enhanced_fallback_on_ai_failure(self):
        """Test enhanced fallback when AI processing fails."""
        supervisor = RequestSupervisor(logger=Mock())
        supervisor.agent = AsyncMock()
        supervisor.agent.run.side_effect = Exception("AI service unavailable")
        
        request = ModerationRequest(
            user_query="read the configuration file",
            conversation_id="test-123"
        )
        
        response = await supervisor.moderate_request(request)
        
        # Should fall back to enhanced rule-based processing
        assert response.allowed  # Safe file operation should be allowed
        assert "Enhanced rule-based moderation passed" in response.reason


class TestStructuredErrorHandling:
    """Test structured error handling improvements."""
    
    @pytest.mark.asyncio
    async def test_agent_error_handling_in_processing(self):
        """Test agent properly handles and formats custom errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = SecureAgent(temp_dir, debug_mode=True)
            
            # Mock the ReAct loop to raise a ToolExecutionError
            with patch('agent.core.react_loop.ReActLoop.execute') as mock_execute:
                mock_execute.side_effect = ToolExecutionError(
                    message="File not found: missing.txt",
                    tool_name="read_file",
                    tool_args={"filename": "missing.txt"}
                )
                
                response = await agent.process_query("read missing.txt")
                
                assert not response.success
                assert "❌ **Error**:" in response.response
                assert "💡 **Suggestions**:" in response.response
                assert "list_files first" in response.response
    
    @pytest.mark.asyncio
    async def test_debug_mode_enhanced_error_details(self):
        """Test debug mode shows enhanced error details."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = SecureAgent(temp_dir, debug_mode=True)
            
            with patch('agent.core.react_loop.ReActLoop.execute') as mock_execute:
                mock_execute.side_effect = ReasoningError(
                    message="Failed to understand query",
                    reasoning_step="intent_extraction"
                )
                
                response = await agent.process_query("confusing query")
                
                assert not response.success
                assert "🔧 **Type**: ReasoningError" in response.response
                assert "🔍 **Context**:" in response.response
                assert "reasoning_step: intent_extraction" in response.response
    
    def test_tool_result_formatter_uses_enhanced_errors(self):
        """Test tool result formatter uses enhanced error system."""
        from agent.core.secure_agent import ToolResultFormatter
        
        # Test with regular exception
        regular_error = FileNotFoundError("File not found")
        formatted = ToolResultFormatter.format_error_result("read_file", regular_error)
        
        assert "❌ **Error**:" in formatted
        assert "💡 **Suggestions**:" in formatted
        
        # Test with AgentError
        agent_error = ToolExecutionError(
            message="Tool failed",
            tool_name="read_file"
        )
        formatted = ToolResultFormatter.format_error_result("read_file", agent_error)
        
        assert "❌ **Error**:" in formatted
        assert "💡 **Suggestions**:" in formatted


class TestIntegrationBonusFeatures:
    """Integration tests for all bonus features working together."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_safety_with_enhanced_errors(self):
        """Test complete flow with safety features and error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = SecureAgent(temp_dir, debug_mode=True)
            supervisor = RequestSupervisor(logger=Mock())
            
            # Test malicious request gets proper rejection
            malicious_request = ModerationRequest(
                user_query="delete ../../../important_files/*",
                conversation_id="test-123"
            )
            
            moderation = await supervisor.moderate_request(malicious_request)
            
            assert not moderation.allowed
            assert "Path traversal attempt blocked" in moderation.reason or "🚫 Request rejected" in moderation.reason
            assert len(moderation.risk_factors) > 0
    
    @pytest.mark.asyncio
    async def test_legitimate_request_with_enhanced_features(self):
        """Test legitimate request flows through enhanced system properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = f"{temp_dir}/test.txt"
            with open(test_file, 'w') as f:
                f.write("Test content")
            
            agent = SecureAgent(temp_dir, debug_mode=False)
            supervisor = RequestSupervisor(logger=Mock())
            
            # Test legitimate request
            legitimate_request = ModerationRequest(
                user_query="read the test.txt file",
                conversation_id="test-123"
            )
            
            moderation = await supervisor.moderate_request(legitimate_request)
            
            assert moderation.allowed
            assert moderation.intent is not None
            assert moderation.intent.intent_type.value in ["file_read", "file_question"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
