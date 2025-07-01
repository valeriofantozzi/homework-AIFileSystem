"""
Unit tests for OrchestratorLite.

Tests the lightweight LLM gatekeeper for safety moderation and intent extraction.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch

import structlog

from agent.orchestrator.orchestrator_lite import (
    OrchestratorLite,
    ModerationRequest,
    ModerationResponse,
    ModerationDecision,
    IntentType,
    IntentData
)


class TestOrchestratorLite:
    """Test suite for OrchestratorLite class."""
    
    @pytest.fixture
    def logger(self):
        """Create a test logger."""
        return structlog.get_logger("test")
    
    @pytest.fixture
    def mock_model_provider(self):
        """Create a mock model provider."""
        mock_provider = Mock()
        mock_provider.provider_name = "openai"
        mock_provider.model_name = "gpt-4.1-nano"
        mock_provider.get_client_params.return_value = {
            "api_key": "test-key",
            "model": "gpt-4.1-nano"
        }
        return mock_provider
    
    @pytest.fixture
    def moderation_request(self):
        """Create a test moderation request."""
        return ModerationRequest(
            user_query="Please read the file test.txt",
            conversation_id=str(uuid.uuid4())
        )
    
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    def test_orchestrator_initialization(self, mock_get_model, mock_model_provider, logger):
        """Test orchestrator initialization."""
        mock_get_model.return_value = mock_model_provider
        
        orchestrator = OrchestratorLite(logger)
        
        assert orchestrator.model_provider == mock_model_provider
        assert orchestrator.logger == logger
        assert orchestrator.system_prompt is not None
    
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    def test_orchestrator_initialization_failure(self, mock_get_model, logger):
        """Test orchestrator initialization with configuration failure."""
        mock_get_model.side_effect = Exception("Configuration error")
        
        with pytest.raises(Exception, match="Configuration error"):
            OrchestratorLite(logger)
    
    def test_create_request(self, mock_model_provider, logger):
        """Test creating a moderation request."""
        with patch('agent.orchestrator.orchestrator_lite.get_model_for_role', return_value=mock_model_provider):
            orchestrator = OrchestratorLite(logger)
            
            request = orchestrator.create_request("test query", "conv-123")
            
            assert request.user_query == "test query"
            assert request.conversation_id == "conv-123"
            assert request.timestamp is not None
    
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    @pytest.mark.asyncio
    async def test_fallback_moderation_safe_query(self, mock_get_model, mock_model_provider, logger):
        """Test fallback moderation with safe query."""
        mock_get_model.return_value = mock_model_provider
        
        # Force agent to be None to trigger fallback
        with patch.object(OrchestratorLite, '_setup_agent'):
            orchestrator = OrchestratorLite(logger)
            orchestrator.agent = None
            
            request = ModerationRequest(
                user_query="read file test.txt",
                conversation_id="test-conv"
            )
            
            response = await orchestrator.moderate_request(request)
            
            assert response.decision == ModerationDecision.ALLOWED
            assert response.allowed is True
            assert response.intent is not None
            assert response.intent.intent_type == IntentType.FILE_READ
            assert "read_file" in response.intent.tools_needed
    
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    @pytest.mark.asyncio
    async def test_fallback_moderation_unsafe_query(self, mock_get_model, mock_model_provider, logger):
        """Test fallback moderation with unsafe query."""
        mock_get_model.return_value = mock_model_provider
        
        # Force agent to be None to trigger fallback
        with patch.object(OrchestratorLite, '_setup_agent'):
            orchestrator = OrchestratorLite(logger)
            orchestrator.agent = None
            
            request = ModerationRequest(
                user_query="delete all files with rm -rf",
                conversation_id="test-conv"
            )
            
            response = await orchestrator.moderate_request(request)
            
            assert response.decision == ModerationDecision.REJECTED
            assert response.allowed is False
            assert response.intent is None
            assert "unsafe_pattern_detected" in response.risk_factors
    
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    @pytest.mark.asyncio
    async def test_fallback_moderation_write_query(self, mock_get_model, mock_model_provider, logger):
        """Test fallback moderation with write query."""
        mock_get_model.return_value = mock_model_provider
        
        # Force agent to be None to trigger fallback
        with patch.object(OrchestratorLite, '_setup_agent'):
            orchestrator = OrchestratorLite(logger)
            orchestrator.agent = None
            
            request = ModerationRequest(
                user_query="create a new file with some content",
                conversation_id="test-conv"
            )
            
            response = await orchestrator.moderate_request(request)
            
            assert response.decision == ModerationDecision.ALLOWED
            assert response.allowed is True
            assert response.intent is not None
            assert response.intent.intent_type == IntentType.FILE_WRITE
            assert "write_file" in response.intent.tools_needed
    
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    @pytest.mark.asyncio
    async def test_fallback_moderation_list_query(self, mock_get_model, mock_model_provider, logger):
        """Test fallback moderation with list query."""
        mock_get_model.return_value = mock_model_provider
        
        # Force agent to be None to trigger fallback
        with patch.object(OrchestratorLite, '_setup_agent'):
            orchestrator = OrchestratorLite(logger)
            orchestrator.agent = None
            
            request = ModerationRequest(
                user_query="list all files in the directory",
                conversation_id="test-conv"
            )
            
            response = await orchestrator.moderate_request(request)
            
            assert response.decision == ModerationDecision.ALLOWED
            assert response.allowed is True
            assert response.intent is not None
            assert response.intent.intent_type == IntentType.FILE_LIST
            assert "list_files" in response.intent.tools_needed
    
    def test_parse_agent_response_valid(self, mock_model_provider, logger):
        """Test parsing valid agent response."""
        with patch('agent.orchestrator.orchestrator_lite.get_model_for_role', return_value=mock_model_provider):
            orchestrator = OrchestratorLite(logger)
            
            response_data = {
                "decision": "allowed",
                "allowed": True,
                "intent": {
                    "intent_type": "file_read",
                    "confidence": 0.9,
                    "parameters": {"filename": "test.txt"},
                    "tools_needed": ["read_file"]
                },
                "reason": "Safe file read request",
                "risk_factors": []
            }
            
            result = orchestrator._parse_agent_response(response_data)
            
            assert result.decision == ModerationDecision.ALLOWED
            assert result.allowed is True
            assert result.intent is not None
            assert result.intent.intent_type == IntentType.FILE_READ
            assert result.intent.confidence == 0.9
            assert result.reason == "Safe file read request"
    
    def test_parse_agent_response_invalid(self, mock_model_provider, logger):
        """Test parsing invalid agent response."""
        with patch('agent.orchestrator.orchestrator_lite.get_model_for_role', return_value=mock_model_provider):
            orchestrator = OrchestratorLite(logger)
            
            response_data = {
                "invalid": "response"  # Missing required fields
            }
            
            result = orchestrator._parse_agent_response(response_data)
            
            assert result.decision == ModerationDecision.REJECTED
            assert result.allowed is False
            assert result.intent is None
            # The method defaults to "No reason provided" when decision key is missing
    
    def test_create_error_response(self, mock_model_provider, logger):
        """Test creating error response."""
        with patch('agent.orchestrator.orchestrator_lite.get_model_for_role', return_value=mock_model_provider):
            orchestrator = OrchestratorLite(logger)
            
            result = orchestrator._create_error_response("conv-123", "Test error")
            
            assert result.decision == ModerationDecision.REJECTED
            assert result.allowed is False
            assert result.intent is None
            assert "Test error" in result.reason
            assert "system_error" in result.risk_factors
    
    def test_moderation_response_to_dict(self):
        """Test ModerationResponse to_dict method."""
        intent = IntentData(
            intent_type=IntentType.FILE_READ,
            confidence=0.8,
            parameters={"filename": "test.txt"},
            tools_needed=["read_file"]
        )
        
        response = ModerationResponse(
            decision=ModerationDecision.ALLOWED,
            allowed=True,
            intent=intent,
            reason="Test response",
            risk_factors=[]
        )
        
        result = response.to_dict()
        
        assert result["allowed"] is True
        assert result["decision"] == "allowed"
        assert result["reason"] == "Test response"
        assert result["intent"] is not None
        assert result["intent"]["intent_type"] == "file_read"  # Now should work with custom model_dump
        assert result["risk_factors"] == []


if __name__ == "__main__":
    pytest.main([__file__])
