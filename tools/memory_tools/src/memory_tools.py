"""
Memory Tools for AI File System Agent.

This module provides conversation memory capabilities to maintain context
across multiple interactions within the same conversation session.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

import structlog


class MemoryError(Exception):
    """Base exception for memory-related errors."""
    pass


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    role: str  # 'user' or 'agent'
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary."""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass 
class ConversationContext:
    """Context information for a conversation."""
    conversation_id: str
    messages: List[ConversationMessage]
    created_at: datetime
    last_updated: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def get_recent_context(self, limit: int = 5) -> str:
        """Get recent conversation context as formatted string."""
        recent_messages = self.messages[-limit:] if self.messages else []
        
        if not recent_messages:
            return "No previous conversation context."
        
        context_lines = ["Recent conversation context:"]
        for msg in recent_messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            role = msg.role.title()
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            context_lines.append(f"[{timestamp}] {role}: {content}")
        
        return "\n".join(context_lines)
    
    def get_last_agent_question(self) -> Optional[str]:
        """Get the last question asked by the agent."""
        for msg in reversed(self.messages):
            if msg.role == 'agent' and ('?' in msg.content or 'would you like' in msg.content.lower()):
                return msg.content
        return None
    
    def has_pending_response(self) -> bool:
        """Check if agent asked a question that's waiting for user response."""
        return self.get_last_agent_question() is not None and (
            not self.messages or self.messages[-1].role == 'agent'
        )


class ConversationMemory:
    """Manages memory for a single conversation."""
    
    def __init__(self, conversation_id: str, storage_path: Optional[Path] = None):
        self.conversation_id = conversation_id
        self.messages: List[ConversationMessage] = []
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.metadata: Dict[str, Any] = {}
        self.storage_path = storage_path
        self.logger = structlog.get_logger("memory.conversation")
        
        # Load from storage if exists
        if self.storage_path and self.storage_path.exists():
            self._load_from_storage()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the conversation."""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.messages.append(message)
        self.last_updated = datetime.now()
        
        self.logger.info(
            "Added message to conversation",
            conversation_id=self.conversation_id,
            role=role,
            content_length=len(content)
        )
        
        # Save to storage if configured
        if self.storage_path:
            self._save_to_storage()
    
    def get_context(self) -> ConversationContext:
        """Get the full conversation context."""
        return ConversationContext(
            conversation_id=self.conversation_id,
            messages=self.messages.copy(),
            created_at=self.created_at,
            last_updated=self.last_updated,
            metadata=self.metadata.copy()
        )
    
    def get_recent_messages(self, limit: int = 10) -> List[ConversationMessage]:
        """Get recent messages."""
        return self.messages[-limit:] if self.messages else []
    
    def search_messages(self, query: str, limit: int = 5) -> List[ConversationMessage]:
        """Search for messages containing specific text."""
        matching_messages = []
        query_lower = query.lower()
        
        for msg in reversed(self.messages):  # Search from most recent
            if query_lower in msg.content.lower():
                matching_messages.append(msg)
                if len(matching_messages) >= limit:
                    break
        
        return list(reversed(matching_messages))  # Return in chronological order
    
    def _save_to_storage(self) -> None:
        """Save conversation to storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'conversation_id': self.conversation_id,
                'created_at': self.created_at.isoformat(),
                'last_updated': self.last_updated.isoformat(),
                'metadata': self.metadata,
                'messages': [msg.to_dict() for msg in self.messages]
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(
                "Failed to save conversation to storage",
                conversation_id=self.conversation_id,
                error=str(e)
            )
            raise MemoryError(f"Failed to save conversation: {e}")
    
    def _load_from_storage(self) -> None:
        """Load conversation from storage."""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.conversation_id = data['conversation_id']
            self.created_at = datetime.fromisoformat(data['created_at'])
            self.last_updated = datetime.fromisoformat(data['last_updated'])
            self.metadata = data.get('metadata', {})
            self.messages = [
                ConversationMessage.from_dict(msg_data) 
                for msg_data in data.get('messages', [])
            ]
            
            self.logger.info(
                "Loaded conversation from storage",
                conversation_id=self.conversation_id,
                message_count=len(self.messages)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to load conversation from storage",
                conversation_id=self.conversation_id,
                error=str(e)
            )
            raise MemoryError(f"Failed to load conversation: {e}")


class MemoryManager:
    """Central manager for all conversation memories."""
    
    def __init__(self, storage_dir: Optional[Path] = None, max_conversations: int = 100):
        self.storage_dir = storage_dir or Path("logs/conversations")
        self.max_conversations = max_conversations
        self.conversations: Dict[str, ConversationMemory] = {}
        self.logger = structlog.get_logger("memory.manager")
        
        # Create storage directory
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing conversations
        self._load_existing_conversations()
    
    def get_or_create_conversation(self, conversation_id: Optional[str] = None) -> tuple[str, ConversationMemory]:
        """Get existing conversation or create new one."""
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        
        if conversation_id not in self.conversations:
            storage_path = self.storage_dir / f"{conversation_id}.json"
            conversation = ConversationMemory(conversation_id, storage_path)
            self.conversations[conversation_id] = conversation
            
            self.logger.info(
                "Created new conversation",
                conversation_id=conversation_id
            )
            
            # Clean up old conversations if we exceed limit
            self._cleanup_old_conversations()
        
        return conversation_id, self.conversations[conversation_id]
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationMemory]:
        """Get existing conversation by ID."""
        return self.conversations.get(conversation_id)
    
    def get_conversation_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context by ID."""
        conversation = self.get_conversation(conversation_id)
        return conversation.get_context() if conversation else None
    
    def add_interaction(
        self, 
        conversation_id: str, 
        user_query: str, 
        agent_response: str,
        tools_used: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a complete interaction (user query + agent response) to conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            _, conversation = self.get_or_create_conversation(conversation_id)
        
        # Add user message
        conversation.add_message("user", user_query)
        
        # Add agent response with metadata
        agent_metadata = metadata or {}
        if tools_used:
            agent_metadata["tools_used"] = tools_used
        
        conversation.add_message("agent", agent_response, agent_metadata)
        
        self.logger.info(
            "Added interaction to conversation",
            conversation_id=conversation_id,
            tools_used=tools_used
        )
    
    def _load_existing_conversations(self) -> None:
        """Load existing conversations from storage."""
        if not self.storage_dir.exists():
            return
        
        for file_path in self.storage_dir.glob("*.json"):
            try:
                conversation_id = file_path.stem
                conversation = ConversationMemory(conversation_id, file_path)
                self.conversations[conversation_id] = conversation
                
            except Exception as e:
                self.logger.warning(
                    "Failed to load conversation",
                    file_path=str(file_path),
                    error=str(e)
                )
        
        self.logger.info(
            "Loaded existing conversations",
            conversation_count=len(self.conversations)
        )
    
    def _cleanup_old_conversations(self) -> None:
        """Remove old conversations if we exceed the limit."""
        if len(self.conversations) <= self.max_conversations:
            return
        
        # Sort by last_updated and keep the most recent ones
        sorted_conversations = sorted(
            self.conversations.items(),
            key=lambda x: x[1].last_updated,
            reverse=True
        )
        
        # Keep only the most recent conversations
        conversations_to_keep = dict(sorted_conversations[:self.max_conversations])
        conversations_to_remove = [
            conv_id for conv_id in self.conversations 
            if conv_id not in conversations_to_keep
        ]
        
        # Remove old conversations and their files
        for conv_id in conversations_to_remove:
            conversation = self.conversations.pop(conv_id)
            if conversation.storage_path and conversation.storage_path.exists():
                conversation.storage_path.unlink()
        
        self.logger.info(
            "Cleaned up old conversations",
            removed_count=len(conversations_to_remove),
            remaining_count=len(self.conversations)
        )
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear a specific conversation from memory and storage.
        
        Args:
            conversation_id: The ID of the conversation to clear
            
        Returns:
            True if conversation was cleared, False if not found
        """
        conversation = self.conversations.get(conversation_id)
        
        if not conversation:
            self.logger.warning(
                "Attempted to clear non-existent conversation",
                conversation_id=conversation_id
            )
            return False
        
        # Remove storage file if it exists
        if conversation.storage_path and conversation.storage_path.exists():
            try:
                conversation.storage_path.unlink()
                self.logger.info(
                    "Removed conversation storage file",
                    conversation_id=conversation_id,
                    file_path=str(conversation.storage_path)
                )
            except Exception as e:
                self.logger.error(
                    "Failed to remove conversation storage file",
                    conversation_id=conversation_id,
                    file_path=str(conversation.storage_path),
                    error=str(e)
                )
        
        # Remove from memory
        self.conversations.pop(conversation_id)
        
        self.logger.info(
            "Cleared conversation from memory",
            conversation_id=conversation_id
        )
        
        return True
    
    def clear_all_conversations(self) -> int:
        """
        Clear all conversations from memory and storage.
        
        Returns:
            Number of conversations cleared
        """
        cleared_count = 0
        conversation_ids = list(self.conversations.keys())
        
        for conversation_id in conversation_ids:
            if self.clear_conversation(conversation_id):
                cleared_count += 1
        
        self.logger.info(
            "Cleared all conversations",
            cleared_count=cleared_count
        )
        
        return cleared_count


class MemoryTool:
    """Tool interface for memory operations within the agent system."""
    
    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        self.memory_manager = memory_manager or MemoryManager()
        self.logger = structlog.get_logger("memory.tool")
    
    def get_conversation_context(self, conversation_id: str) -> str:
        """Get formatted conversation context for the agent."""
        context = self.memory_manager.get_conversation_context(conversation_id)
        
        if not context:
            return "No conversation history available."
        
        # Check for pending questions
        last_question = context.get_last_agent_question()
        if last_question and context.has_pending_response():
            return f"""
{context.get_recent_context()}

IMPORTANT: The agent previously asked: "{last_question}"
This query might be a response to that question. Consider the context when interpreting ambiguous responses like "yes", "no", "sure", etc.
"""
        
        return context.get_recent_context()
    
    def store_interaction(
        self, 
        conversation_id: str, 
        user_query: str, 
        agent_response: str,
        tools_used: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a complete interaction in memory."""
        try:
            self.memory_manager.add_interaction(
                conversation_id, user_query, agent_response, tools_used, metadata
            )
            return f"Interaction stored successfully for conversation {conversation_id}"
            
        except Exception as e:
            self.logger.error(
                "Failed to store interaction",
                conversation_id=conversation_id,
                error=str(e)
            )
            return f"Failed to store interaction: {e}"
    
    def search_conversation_history(self, conversation_id: str, query: str) -> str:
        """Search conversation history for specific content."""
        conversation = self.memory_manager.get_conversation(conversation_id)
        
        if not conversation:
            return "No conversation found."
        
        messages = conversation.search_messages(query, limit=5)
        
        if not messages:
            return f"No messages found containing '{query}'"
        
        results = [f"Found {len(messages)} relevant messages:"]
        for msg in messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            results.append(f"[{timestamp}] {msg.role.title()}: {content}")
        
        return "\n".join(results)
    
    def get_conversation_summary(self, conversation_id: str) -> str:
        """Get a summary of the conversation."""
        conversation = self.memory_manager.get_conversation(conversation_id)
        
        if not conversation:
            return "No conversation found."
        
        context = conversation.get_context()
        message_count = len(context.messages)
        
        if message_count == 0:
            return "Empty conversation."
        
        duration = context.last_updated - context.created_at
        
        # Get message counts by role
        user_messages = sum(1 for msg in context.messages if msg.role == 'user')
        agent_messages = sum(1 for msg in context.messages if msg.role == 'agent')
        
        return f"""Conversation Summary:
- ID: {conversation_id}
- Duration: {duration}
- Total messages: {message_count}
- User messages: {user_messages}
- Agent messages: {agent_messages}
- Created: {context.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- Last updated: {context.last_updated.strftime('%Y-%m-%d %H:%M:%S')}"""


# Global memory manager instance
_global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager


def create_memory_tools() -> Dict[str, Any]:
    """Create memory tools for use in SecureAgent."""
    memory_tool = MemoryTool(get_memory_manager())
    
    # Create tool functions with proper metadata
    def get_conversation_context(conversation_id: str) -> str:
        """Get conversation context to understand previous interactions."""
        return memory_tool.get_conversation_context(conversation_id)
    
    def store_interaction(
        conversation_id: str, 
        user_query: str, 
        agent_response: str,
        tools_used: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a complete interaction in conversation memory."""
        return memory_tool.store_interaction(
            conversation_id, user_query, agent_response, tools_used, metadata
        )
    
    def search_conversation_history(conversation_id: str, query: str) -> str:
        """Search conversation history for specific content."""
        return memory_tool.search_conversation_history(conversation_id, query)
    
    def get_conversation_summary(conversation_id: str) -> str:
        """Get a summary of the conversation."""
        return memory_tool.get_conversation_summary(conversation_id)
    
    def check_ambiguous_response(conversation_id: str, user_query: str) -> str:
        """Check if user query is an ambiguous response to a previous question."""
        memory_mgr = get_memory_manager()
        conversation = memory_mgr.get_conversation(conversation_id)
        
        if not conversation:
            return "No previous conversation context available."
        
        context = conversation.get_context()
        
        # Check for ambiguous responses
        ambiguous_words = {'yes', 'sure', 'ok', 'okay', 'no', 'nope', 'si', 'sì'}
        user_words = set(user_query.lower().split())
        
        if user_words.intersection(ambiguous_words) and len(user_words) <= 2:
            # This seems like an ambiguous response
            last_question = context.get_last_agent_question()
            if last_question:
                return f"""AMBIGUOUS RESPONSE DETECTED:
User query: "{user_query}"
Previous agent question: "{last_question}"

This appears to be a response to the previous question. Consider interpreting "{user_query}" in context of the previous conversation."""
        
        return "Query appears clear and not ambiguous."
    
    def clear_conversation_memory(conversation_id: str) -> str:
        """Clear conversation memory and associated storage files."""
        memory_mgr = get_memory_manager()
        
        if memory_mgr.clear_conversation(conversation_id):
            return f"Successfully cleared conversation memory for {conversation_id}"
        else:
            return f"No conversation found with ID {conversation_id}"
    
    # Attach metadata for tool selection
    get_conversation_context.tool_metadata = {
        "description": "Get previous conversation context to understand user intent and follow-up queries",
        "parameters": {
            "conversation_id": {
                "type": "string",
                "description": "The conversation ID to retrieve context for"
            }
        },
        "examples": [
            "understand previous conversation",
            "get conversation context",
            "what did we discuss before"
        ]
    }
    
    store_interaction.tool_metadata = {
        "description": "Store a complete interaction (user query + agent response) in conversation memory",
        "parameters": {
            "conversation_id": {"type": "string", "description": "The conversation ID"},
            "user_query": {"type": "string", "description": "The user's query"},
            "agent_response": {"type": "string", "description": "The agent's response"},
            "tools_used": {"type": "array", "description": "List of tools used (optional)"},
            "metadata": {"type": "object", "description": "Additional metadata (optional)"}
        },
        "examples": [
            "store this conversation",
            "save interaction to memory",
            "remember this exchange"
        ]
    }
    
    search_conversation_history.tool_metadata = {
        "description": "Search previous conversation messages for specific content or topics",
        "parameters": {
            "conversation_id": {"type": "string", "description": "The conversation ID to search"},
            "query": {"type": "string", "description": "Search term or phrase"}
        },
        "examples": [
            "search for files mentioned earlier",
            "find when we discussed directories",
            "search conversation for specific topic"
        ]
    }
    
    get_conversation_summary.tool_metadata = {
        "description": "Get a summary of the conversation including message counts and duration",
        "parameters": {
            "conversation_id": {"type": "string", "description": "The conversation ID to summarize"}
        },
        "examples": [
            "summarize our conversation",
            "get conversation overview",
            "conversation statistics"
        ]
    }
    
    check_ambiguous_response.tool_metadata = {
        "description": "Check if user query is ambiguous and might be responding to a previous question",
        "parameters": {
            "conversation_id": {"type": "string", "description": "The conversation ID"},
            "user_query": {"type": "string", "description": "The user's current query"}
        },
        "examples": [
            "check if yes/no response",
            "detect ambiguous response",
            "understand vague answer"
        ]
    }
    
    clear_conversation_memory.tool_metadata = {
        "description": "Clear conversation memory and remove associated storage files",
        "parameters": {
            "conversation_id": {"type": "string", "description": "The conversation ID to clear"}
        },
        "examples": [
            "clear conversation memory",
            "remove conversation history",
            "reset conversation context"
        ]
    }
    
    return {
        "get_conversation_context": get_conversation_context,
        "store_interaction": store_interaction,
        "search_conversation_history": search_conversation_history,
        "get_conversation_summary": get_conversation_summary,
        "check_ambiguous_response": check_ambiguous_response,
        "clear_conversation_memory": clear_conversation_memory,
    }
