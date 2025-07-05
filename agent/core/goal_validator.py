"""
Goal Compliance Validator for ReAct Agent.

This module provides validation capabilities to ensure agent responses
align with stated objectives. Following single responsibility principle,
this validator has one clear purpose: verify goal-response alignment.
"""
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ComplianceLevel(Enum):
    """Levels of goal compliance."""
    FULLY_COMPLIANT = "fully_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    UNCLEAR = "unclear"


@dataclass
class GoalComplianceResult:
    """
    Result of goal compliance validation.
    
    This class encapsulates all information about how well a response
    achieves its stated goal, following data encapsulation principles.
    """
    compliance_level: ComplianceLevel
    confidence_score: float  # 0.0 to 1.0
    explanation: str
    missing_elements: List[str]
    suggestions: List[str]
    
    @property
    def is_compliant(self) -> bool:
        """Check if response is adequately compliant with goal."""
        return self.compliance_level in [
            ComplianceLevel.FULLY_COMPLIANT,
            ComplianceLevel.PARTIALLY_COMPLIANT
        ]


class GoalComplianceValidator:
    """
    High-cohesion validator for goal-response alignment.
    
    Single responsibility: verify that agent responses meet their stated objectives.
    Low coupling: depends only on goal and response abstractions, no external dependencies.
    
    This validator uses rule-based analysis to determine compliance without
    requiring external LLM calls, ensuring fast and reliable validation.
    """
    
    @staticmethod
    def validate_compliance(
        goal: str, 
        response: str, 
        tools_used: List[str],
        context: Optional[dict] = None
    ) -> GoalComplianceResult:
        """
        Validate if response achieves the stated goal.
        
        Args:
            goal: The explicit objective that was set for the request
            response: The agent's final response to validate
            tools_used: List of tools that were used to generate the response
            context: Optional additional context for validation
            
        Returns:
            GoalComplianceResult with detailed compliance analysis
        """
        if not goal or not response:
            return GoalComplianceResult(
                compliance_level=ComplianceLevel.UNCLEAR,
                confidence_score=0.0,
                explanation="Cannot validate compliance without both goal and response",
                missing_elements=["goal" if not goal else "response"],
                suggestions=["Ensure both goal and response are provided"]
            )
        
        # Analyze goal type and response content
        goal_analysis = GoalComplianceValidator._analyze_goal_type(goal)
        response_analysis = GoalComplianceValidator._analyze_response_content(response, tools_used)
        
        # Determine compliance level
        compliance_level = GoalComplianceValidator._determine_compliance_level(
            goal_analysis, response_analysis, goal, response
        )
        
        # Calculate confidence score
        confidence_score = GoalComplianceValidator._calculate_confidence(
            goal_analysis, response_analysis, tools_used
        )
        
        # Generate explanation and suggestions
        explanation = GoalComplianceValidator._generate_explanation(
            compliance_level, goal_analysis, response_analysis
        )
        
        missing_elements = GoalComplianceValidator._identify_missing_elements(
            goal_analysis, response_analysis
        )
        
        suggestions = GoalComplianceValidator._generate_suggestions(
            compliance_level, goal_analysis, missing_elements
        )
        
        return GoalComplianceResult(
            compliance_level=compliance_level,
            confidence_score=confidence_score,
            explanation=explanation,
            missing_elements=missing_elements,
            suggestions=suggestions
        )
    
    @staticmethod
    def _analyze_goal_type(goal: str) -> dict:
        """
        Analyze the type and characteristics of the goal.
        
        Returns dict with goal type indicators for compliance checking.
        """
        goal_lower = goal.lower()
        
        return {
            'is_information_request': any(word in goal_lower for word in [
                'show', 'display', 'list', 'get', 'find', 'see', 'view', 'check'
            ]),
            'is_action_request': any(word in goal_lower for word in [
                'create', 'write', 'delete', 'modify', 'update', 'change', 'execute'
            ]),
            'is_analysis_request': any(word in goal_lower for word in [
                'analyze', 'explain', 'understand', 'reason', 'compare', 'evaluate'
            ]),
            'requires_file_ops': any(word in goal_lower for word in [
                'file', 'directory', 'folder', 'content', 'tree', 'structure'
            ]),
            'requires_specific_format': any(word in goal_lower for word in [
                'tree', 'format', 'table', 'json', 'list', 'hierarchy'
            ])
        }
    
    @staticmethod
    def _analyze_response_content(response: str, tools_used: List[str]) -> dict:
        """
        Analyze the content and characteristics of the response.
        
        Returns dict with response characteristics for compliance checking.
        """
        return {
            'has_structured_output': any(indicator in response for indicator in [
                '├─', '└─', '│', '•', '-', '*', '1.', '2.'
            ]),
            'has_file_content': 'file' in response.lower() or 'directory' in response.lower(),
            'has_error_handling': any(indicator in response.lower() for indicator in [
                'error', 'failed', 'unable', 'cannot', 'not found'
            ]),
            'response_length': len(response),
            'tools_were_used': len(tools_used) > 0,
            'specific_tools_used': tools_used,
            'has_explanation': len(response.split('.')) > 2  # Multi-sentence response
        }
    
    @staticmethod
    def _determine_compliance_level(
        goal_analysis: dict, 
        response_analysis: dict, 
        goal: str, 
        response: str
    ) -> ComplianceLevel:
        """
        Determine the level of compliance between goal and response.
        
        Uses rule-based logic to assess how well the response meets the goal.
        """
        # Check for obvious non-compliance
        if response_analysis['has_error_handling'] and response_analysis['response_length'] < 50:
            return ComplianceLevel.NON_COMPLIANT
        
        # Check for information requests
        if goal_analysis['is_information_request']:
            if (response_analysis['has_file_content'] or 
                response_analysis['has_structured_output'] or
                response_analysis['tools_were_used']):
                return ComplianceLevel.FULLY_COMPLIANT
            elif response_analysis['response_length'] > 20:
                return ComplianceLevel.PARTIALLY_COMPLIANT
            else:
                return ComplianceLevel.NON_COMPLIANT
        
        # Check for action requests
        if goal_analysis['is_action_request']:
            if response_analysis['tools_were_used'] and not response_analysis['has_error_handling']:
                return ComplianceLevel.FULLY_COMPLIANT
            elif response_analysis['tools_were_used']:
                return ComplianceLevel.PARTIALLY_COMPLIANT
            else:
                return ComplianceLevel.NON_COMPLIANT
        
        # Check for analysis requests
        if goal_analysis['is_analysis_request']:
            if (response_analysis['has_explanation'] and 
                response_analysis['response_length'] > 100):
                return ComplianceLevel.FULLY_COMPLIANT
            elif response_analysis['response_length'] > 50:
                return ComplianceLevel.PARTIALLY_COMPLIANT
            else:
                return ComplianceLevel.NON_COMPLIANT
        
        # Default: if response has content and no errors, consider partially compliant
        if response_analysis['response_length'] > 30 and not response_analysis['has_error_handling']:
            return ComplianceLevel.PARTIALLY_COMPLIANT
        
        return ComplianceLevel.UNCLEAR
    
    @staticmethod
    def _calculate_confidence(
        goal_analysis: dict, 
        response_analysis: dict, 
        tools_used: List[str]
    ) -> float:
        """Calculate confidence score for the compliance assessment."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for clear indicators
        if response_analysis['tools_were_used'] and goal_analysis['requires_file_ops']:
            confidence += 0.3
        
        if response_analysis['has_structured_output'] and goal_analysis['requires_specific_format']:
            confidence += 0.2
        
        if response_analysis['response_length'] > 100:
            confidence += 0.1
        
        # Decrease confidence for unclear situations
        if response_analysis['has_error_handling']:
            confidence -= 0.2
        
        if not response_analysis['tools_were_used'] and goal_analysis['requires_file_ops']:
            confidence -= 0.3
        
        return max(0.0, min(1.0, confidence))
    
    @staticmethod
    def _generate_explanation(
        compliance_level: ComplianceLevel,
        goal_analysis: dict,
        response_analysis: dict
    ) -> str:
        """Generate human-readable explanation of compliance assessment."""
        if compliance_level == ComplianceLevel.FULLY_COMPLIANT:
            return "Response fully achieves the stated goal with appropriate tools and content."
        
        elif compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT:
            return "Response partially achieves the goal but may be missing some elements or details."
        
        elif compliance_level == ComplianceLevel.NON_COMPLIANT:
            if response_analysis['has_error_handling']:
                return "Response indicates an error occurred, preventing goal achievement."
            else:
                return "Response does not adequately address the stated goal."
        
        else:  # UNCLEAR
            return "Unable to clearly determine if response achieves the goal."
    
    @staticmethod
    def _identify_missing_elements(goal_analysis: dict, response_analysis: dict) -> List[str]:
        """Identify what elements might be missing from the response."""
        missing = []
        
        if goal_analysis['requires_file_ops'] and not response_analysis['tools_were_used']:
            missing.append("file system operations")
        
        if goal_analysis['requires_specific_format'] and not response_analysis['has_structured_output']:
            missing.append("structured formatting")
        
        if goal_analysis['is_analysis_request'] and not response_analysis['has_explanation']:
            missing.append("detailed explanation")
        
        return missing
    
    @staticmethod
    def _generate_suggestions(
        compliance_level: ComplianceLevel,
        goal_analysis: dict,
        missing_elements: List[str]
    ) -> List[str]:
        """Generate suggestions for improving goal compliance."""
        suggestions = []
        
        if compliance_level == ComplianceLevel.NON_COMPLIANT:
            suggestions.append("Consider restating the goal more clearly")
            suggestions.append("Verify that appropriate tools are available")
        
        if missing_elements:
            for element in missing_elements:
                suggestions.append(f"Consider adding {element} to the response")
        
        if goal_analysis['requires_specific_format']:
            suggestions.append("Ensure response uses the requested format")
        
        return suggestions
