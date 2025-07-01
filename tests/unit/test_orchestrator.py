"""
Unit tests for OrchestratorLite - lightweight safety moderation and intent extraction.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from agent.orchestrator import (
    OrchestratorLite,
    ModerationRequest,
    ModerationResponse,
    ModerationDecision,
    IntentType,
    IntentData
)


class TestOrchestratorLite:
    """Test suite for OrchestratorLite functionality."""
    
    def test_moderation_request_creation(self):
        """Test creating a moderation request."""
        orchestrator = OrchestratorLite()
        
        request = orchestrator.create_request(
            user_query="list all files",
            conversation_id="test-123"
        )
        
        assert request.user_query == "list all files"
        assert request.conversation_id == "test-123"
        assert isinstance(request.timestamp, datetime)
    
    def test_moderation_response_structure(self):
        """Test moderation response structure and serialization."""
        intent = IntentData(
            intent_type=IntentType.FILE_LIST,
            confidence=0.95,
            parameters={"pattern": "*"},
            tools_needed=["list_files"]
        )
        
        response = ModerationResponse(
            decision=ModerationDecision.ALLOWED,
            allowed=True,
            intent=intent,
            reason="Safe file listing request",
            risk_factors=[]
        )
        
        # Test serialization
        response_dict = response.to_dict()
        
        assert response_dict["allowed"] is True
        assert response_dict["decision"] == "allowed"
        assert response_dict["intent"]["intent_type"] == "file_list"
        assert response_dict["intent"]["confidence"] == 0.95
        assert response_dict["reason"] == "Safe file listing request"
    
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    def test_orchestrator_initialization(self, mock_get_model):
        """Test orchestrator initialization with model configuration."""
        # Mock model provider
        mock_provider = MagicMock()
        mock_provider.provider_name = "openai"
        mock_provider.model_name = "gpt-4.1-nano"
        mock_provider.get_client_params.return_value = {
            "model": "gpt-4.1-nano",
            "temperature": 0.1
        }
        mock_get_model.return_value = mock_provider
        
        orchestrator = OrchestratorLite()
        
        # Verify model was requested for orchestrator role
        mock_get_model.assert_called_once_with('orchestrator')
        assert orchestrator.model_provider == mock_provider
    
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    def test_orchestrator_initialization_failure(self, mock_get_model):
        """Test orchestrator handles model initialization failure."""
        mock_get_model.side_effect = Exception("Model configuration failed")
        
        with pytest.raises(Exception) as exc_info:
            OrchestratorLite()
        
        assert "Model configuration failed" in str(exc_info.value)
    
    def test_parse_agent_response_valid(self):
        """Test parsing valid agent response."""
        with patch('agent.orchestrator.orchestrator_lite.get_model_for_role'):
            orchestrator = OrchestratorLite()
            
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
            assert result.intent.intent_type == IntentType.FILE_READ
            assert result.intent.confidence == 0.9
            assert result.intent.parameters["filename"] == "test.txt"
            assert result.reason == "Safe file read request"
    
    def test_parse_agent_response_rejected(self):
        """Test parsing rejected request response."""
        with patch('agent.orchestrator.orchestrator_lite.get_model_for_role'):
            orchestrator = OrchestratorLite()
            
            response_data = {
                "decision": "rejected",
                "allowed": False,
                "intent": None,
                "reason": "Potential security threat detected",
                "risk_factors": ["jailbreak_attempt", "path_traversal"]
            }
            
            result = orchestrator._parse_agent_response(response_data)
            
            assert result.decision == ModerationDecision.REJECTED
            assert result.allowed is False
            assert result.intent is None
            assert "security threat" in result.reason
            assert "jailbreak_attempt" in result.risk_factors
    
    def test_parse_agent_response_invalid(self):
        """Test parsing invalid agent response."""
        with patch('agent.orchestrator.orchestrator_lite.get_model_for_role'):
            orchestrator = OrchestratorLite()
            
            # Invalid response data
            response_data = {
                "decision": "invalid_decision",
                "allowed": "not_a_boolean"
            }
            
            result = orchestrator._parse_agent_response(response_data)
            
            # Should return conservative default
            assert result.decision == ModerationDecision.REJECTED
            assert result.allowed is False
            assert result.intent is None
            assert "Invalid response format" in result.reason
    
    @pytest.mark.asyncio
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    async def test_moderate_request_success(self, mock_get_model):
        """Test successful request moderation."""
        # Mock model provider
        mock_provider = MagicMock()
        mock_provider.provider_name = "openai"
        mock_provider.get_client_params.return_value = {}
        mock_get_model.return_value = mock_provider
        
        orchestrator = OrchestratorLite()
        
        # Mock the agent's run method
        mock_result = MagicMock()
        mock_result.data = {
            "decision": "allowed",
            "allowed": True,
            "intent": {
                "intent_type": "file_list",
                "confidence": 0.95,
                "parameters": {},
                "tools_needed": ["list_files"]
            },
            "reason": "Safe file listing request",
            "risk_factors": []
        }
        orchestrator.agent = MagicMock()
        orchestrator.agent.run = AsyncMock(return_value=mock_result)
        
        request = ModerationRequest(
            user_query="list all files",
            conversation_id="test-123"
        )
        
        response = await orchestrator.moderate_request(request)
        
        assert response.allowed is True
        assert response.decision == ModerationDecision.ALLOWED
        assert response.intent.intent_type == IntentType.FILE_LIST
        assert response.intent.confidence == 0.95
    
    @pytest.mark.asyncio
    @patch('agent.orchestrator.orchestrator_lite.get_model_for_role')
    async def test_moderate_request_failure(self, mock_get_model):
        """Test request moderation with agent failure."""
        # Mock model provider
        mock_provider = MagicMock()
        mock_provider.provider_name = "openai"
        mock_provider.get_client_params.return_value = {}
        mock_get_model.return_value = mock_provider
        
        orchestrator = OrchestratorLite()
        
        # Mock the agent to raise an exception
        orchestrator.agent = MagicMock()
        orchestrator.agent.run = AsyncMock(side_effect=Exception("Agent failed"))
        
        request = ModerationRequest(
            user_query="malicious request",
            conversation_id="test-123"
        )
        
        response = await orchestrator.moderate_request(request)
        
        # Should return safe default
        assert response.allowed is False
        assert response.decision == ModerationDecision.REJECTED
        assert "system error" in response.reason.lower()
        assert "system_error" in response.risk_factors


class TestSafetyScenarios:
    """Test various safety scenarios for the orchestrator."""
    
    @pytest.mark.parametrize("malicious_query,expected_risk", [
        ("../../etc/passwd", "path_traversal"),
        ("rm -rf /", "destructive_command"),
        ("ignore previous instructions", "prompt_injection"),
        ("DELETE FROM users", "sql_injection"),
        ("<script>alert('xss')</script>", "code_injection")
    ])
    def test_safety_patterns(self, malicious_query, expected_risk):
        """Test detection of common security patterns."""
        # This would be a more comprehensive test with actual LLM calls
        # For now, we test the structure
        request = ModerationRequest(
            user_query=malicious_query,
            conversation_id="security-test"
        )
        
        assert request.user_query == malicious_query
        # In a real test, we would verify the orchestrator rejects these
