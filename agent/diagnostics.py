"""
Enhanced diagnostic and monitoring system for the AI File System Agent.
Provides detailed logging, performance tracking, and usage statistics.
"""

import logging
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import psutil
import os

from config.env_loader import EnvironmentLoader


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""
    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_usage: float
    success: bool
    error_message: Optional[str] = None
    
    @classmethod
    def create(cls, operation: str, start_time: float, end_time: float, 
               success: bool, error_message: Optional[str] = None) -> 'PerformanceMetrics':
        """Create performance metrics with calculated values."""
        return cls(
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            memory_usage=psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,  # MB
            success=success,
            error_message=error_message
        )


@dataclass
class UsageStatistics:
    """Usage statistics for the agent."""
    conversations: int = 0
    queries: int = 0
    tool_calls: int = 0
    errors: int = 0
    avg_response_time: float = 0.0
    most_used_tools: Dict[str, int] = None
    error_types: Dict[str, int] = None
    
    def __post_init__(self):
        if self.most_used_tools is None:
            self.most_used_tools = {}
        if self.error_types is None:
            self.error_types = {}


class DiagnosticLogger:
    """Enhanced logging system with structured output and multiple levels of detail."""
    
    def __init__(self):
        self.env = EnvironmentLoader()
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Set up different loggers for different purposes
        self._setup_loggers()
        
        # Performance and usage tracking
        self.performance_metrics: deque = deque(maxlen=1000)  # Keep last 1000 operations
        self.usage_stats = UsageStatistics()
        self.operation_start_times: Dict[str, float] = {}
        self._lock = threading.Lock()
        
    def _setup_loggers(self):
        """Set up structured logging with multiple output files."""
        
        # Main agent logger
        self.agent_logger = logging.getLogger("agent")
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        self.agent_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        
        # Performance logger
        self.perf_logger = logging.getLogger("performance")
        self.perf_logger.setLevel(logging.INFO)
        
        # Usage statistics logger
        self.usage_logger = logging.getLogger("usage")
        self.usage_logger.setLevel(logging.INFO)
        
        # Error logger
        self.error_logger = logging.getLogger("errors")
        self.error_logger.setLevel(logging.WARNING)
        
        # Clear existing handlers
        for logger in [self.agent_logger, self.perf_logger, self.usage_logger, self.error_logger]:
            logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
        )
        json_formatter = logging.Formatter('%(message)s')
        
        # Agent activity log (detailed)
        agent_handler = logging.FileHandler(self.log_dir / "agent_activity.log")
        agent_handler.setFormatter(detailed_formatter)
        self.agent_logger.addHandler(agent_handler)
        
        # Performance metrics (JSON)
        perf_handler = logging.FileHandler(self.log_dir / "performance.jsonl")
        perf_handler.setFormatter(json_formatter)
        self.perf_logger.addHandler(perf_handler)
        
        # Usage statistics (JSON)
        usage_handler = logging.FileHandler(self.log_dir / "usage.jsonl")
        usage_handler.setFormatter(json_formatter)
        self.usage_logger.addHandler(usage_handler)
        
        # Error log (detailed)
        error_handler = logging.FileHandler(self.log_dir / "errors.log")
        error_handler.setFormatter(detailed_formatter)
        self.error_logger.addHandler(error_handler)
        
        # Console output for debug mode
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        if debug_mode:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            console_handler.setLevel(logging.DEBUG)
            self.agent_logger.addHandler(console_handler)
    
    def start_operation(self, operation: str, context: Dict[str, Any] = None) -> str:
        """Start tracking an operation."""
        operation_id = f"{operation}_{int(time.time() * 1000)}"
        
        with self._lock:
            self.operation_start_times[operation_id] = time.time()
        
        context_str = f" | Context: {json.dumps(context)}" if context else ""
        self.agent_logger.info(f"OPERATION_START | {operation} | ID: {operation_id}{context_str}")
        
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, 
                     error_message: Optional[str] = None, result_summary: Optional[str] = None):
        """End tracking an operation and record metrics."""
        
        with self._lock:
            start_time = self.operation_start_times.pop(operation_id, time.time())
            
        end_time = time.time()
        operation = operation_id.split('_')[0]
        
        # Create performance metrics
        metrics = PerformanceMetrics.create(
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            success=success,
            error_message=error_message
        )
        
        # Store metrics
        self.performance_metrics.append(metrics)
        
        # Log performance data
        perf_data = {
            "timestamp": datetime.now().isoformat(),
            "operation_id": operation_id,
            **asdict(metrics)
        }
        self.perf_logger.info(json.dumps(perf_data))
        
        # Log operation end
        status = "SUCCESS" if success else "FAILURE"
        result_str = f" | Result: {result_summary}" if result_summary else ""
        error_str = f" | Error: {error_message}" if error_message else ""
        self.agent_logger.info(
            f"OPERATION_END | {operation} | ID: {operation_id} | Status: {status} | "
            f"Duration: {metrics.duration:.3f}s{result_str}{error_str}"
        )
        
        # Update usage statistics
        self._update_usage_stats(operation, success, metrics.duration)
        
        # Log errors separately
        if not success and error_message:
            self.error_logger.error(f"{operation} | {operation_id} | {error_message}")
    
    def log_conversation_start(self, conversation_id: str, user_query: str):
        """Log the start of a new conversation."""
        with self._lock:
            self.usage_stats.conversations += 1
            self.usage_stats.queries += 1
        
        self.agent_logger.info(f"CONVERSATION_START | ID: {conversation_id} | Query: {user_query[:100]}...")
        
        # Log usage update
        usage_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "conversation_start",
            "conversation_id": conversation_id,
            "query_preview": user_query[:100]
        }
        self.usage_logger.info(json.dumps(usage_data))
    
    def log_tool_usage(self, tool_name: str, parameters: Dict[str, Any] = None):
        """Log tool usage for statistics."""
        with self._lock:
            self.usage_stats.tool_calls += 1
            if tool_name not in self.usage_stats.most_used_tools:
                self.usage_stats.most_used_tools[tool_name] = 0
            self.usage_stats.most_used_tools[tool_name] += 1
        
        params_str = f" | Params: {json.dumps(parameters)}" if parameters else ""
        self.agent_logger.debug(f"TOOL_USAGE | {tool_name}{params_str}")
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], severity: str = "WARNING"):
        """Log security-related events."""
        timestamp = datetime.now().isoformat()
        
        security_data = {
            "timestamp": timestamp,
            "event_type": event_type,
            "severity": severity,
            **details
        }
        
        log_level = getattr(logging, severity)
        self.error_logger.log(log_level, f"SECURITY_EVENT | {event_type} | {json.dumps(details)}")
        
        # Also log to usage for statistics
        self.usage_logger.info(json.dumps({
            "timestamp": timestamp,
            "event": "security_event",
            "type": event_type,
            "severity": severity
        }))
    
    def _update_usage_stats(self, operation: str, success: bool, duration: float):
        """Update internal usage statistics."""
        with self._lock:
            if not success:
                self.usage_stats.errors += 1
            
            # Update average response time
            current_avg = self.usage_stats.avg_response_time
            total_ops = len(self.performance_metrics)
            if total_ops > 0:
                self.usage_stats.avg_response_time = (
                    (current_avg * (total_ops - 1) + duration) / total_ops
                )
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours."""
        cutoff_time = time.time() - (hours * 3600)
        
        recent_metrics = [m for m in self.performance_metrics if m.start_time >= cutoff_time]
        
        if not recent_metrics:
            return {"message": "No recent performance data"}
        
        total_operations = len(recent_metrics)
        successful_operations = sum(1 for m in recent_metrics if m.success)
        avg_duration = sum(m.duration for m in recent_metrics) / total_operations
        avg_memory = sum(m.memory_usage for m in recent_metrics) / total_operations
        
        operation_counts = defaultdict(int)
        for m in recent_metrics:
            operation_counts[m.operation] += 1
        
        return {
            "time_period_hours": hours,
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "success_rate": successful_operations / total_operations,
            "average_duration_seconds": round(avg_duration, 3),
            "average_memory_mb": round(avg_memory, 2),
            "operations_by_type": dict(operation_counts),
            "slowest_operations": [
                {"operation": m.operation, "duration": m.duration}
                for m in sorted(recent_metrics, key=lambda x: x.duration, reverse=True)[:5]
            ]
        }
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        with self._lock:
            return {
                "statistics_as_of": datetime.now().isoformat(),
                **asdict(self.usage_stats),
                "top_tools": sorted(
                    self.usage_stats.most_used_tools.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10],
                "error_breakdown": dict(self.usage_stats.error_types)
            }
    
    def export_diagnostics(self, output_file: Optional[Path] = None) -> Path:
        """Export comprehensive diagnostics to a file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.log_dir / f"diagnostics_{timestamp}.json"
        
        diagnostics = {
            "export_timestamp": datetime.now().isoformat(),
            "system_info": {
                "python_version": os.getenv("PYTHON_VERSION", "unknown"),
                "environment": os.getenv("AI_ENVIRONMENT", "unknown"),
                "debug_mode": os.getenv("DEBUG", "false").lower() == "true",
                "process_id": os.getpid(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            },
            "performance_summary": self.get_performance_summary(),
            "usage_statistics": self.get_usage_statistics(),
            "recent_errors": self._get_recent_errors(),
            "log_file_sizes": self._get_log_file_info()
        }
        
        with open(output_file, 'w') as f:
            json.dump(diagnostics, f, indent=2)
        
        self.agent_logger.info(f"Diagnostics exported to {output_file}")
        return output_file
    
    def _get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent error information."""
        recent_errors = []
        error_log_file = self.log_dir / "errors.log"
        
        if error_log_file.exists():
            try:
                with open(error_log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-count:]:
                        if line.strip():
                            recent_errors.append({"error_log": line.strip()})
            except Exception as e:
                recent_errors.append({"error": f"Could not read error log: {e}"})
        
        return recent_errors
    
    def _get_log_file_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about log files."""
        log_info = {}
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                stat = log_file.stat()
                log_info[log_file.name] = {
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            except Exception as e:
                log_info[log_file.name] = {"error": str(e)}
        
        return log_info
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check."""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "HEALTHY",
            "components": {}
        }
        
        # Check log directory
        try:
            self.log_dir.mkdir(exist_ok=True)
            health_status["components"]["logging"] = {
                "status": "HEALTHY",
                "log_directory": str(self.log_dir),
                "writable": os.access(self.log_dir, os.W_OK)
            }
        except Exception as e:
            health_status["components"]["logging"] = {
                "status": "UNHEALTHY",
                "error": str(e)
            }
            health_status["overall_status"] = "DEGRADED"
        
        # Check recent performance
        try:
            perf_summary = self.get_performance_summary(1)  # Last hour
            health_status["components"]["performance"] = {
                "status": "HEALTHY" if perf_summary.get("success_rate", 0) > 0.8 else "DEGRADED",
                "recent_operations": perf_summary.get("total_operations", 0),
                "success_rate": perf_summary.get("success_rate", 0)
            }
            
            if perf_summary.get("success_rate", 0) < 0.5:
                health_status["overall_status"] = "UNHEALTHY"
            elif perf_summary.get("success_rate", 0) < 0.8:
                health_status["overall_status"] = "DEGRADED"
                
        except Exception as e:
            health_status["components"]["performance"] = {
                "status": "UNKNOWN",
                "error": str(e)
            }
        
        # Check system resources
        try:
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('.').percent
            
            health_status["components"]["system_resources"] = {
                "status": "HEALTHY" if memory_percent < 80 and disk_percent < 90 else "DEGRADED",
                "memory_usage_percent": memory_percent,
                "disk_usage_percent": disk_percent
            }
            
            if memory_percent > 95 or disk_percent > 95:
                health_status["overall_status"] = "UNHEALTHY"
                
        except Exception as e:
            health_status["components"]["system_resources"] = {
                "status": "UNKNOWN",
                "error": str(e)
            }
        
        return health_status


# Global diagnostic logger instance
_diagnostic_logger: Optional[DiagnosticLogger] = None


def get_diagnostic_logger() -> DiagnosticLogger:
    """Get the global diagnostic logger instance."""
    global _diagnostic_logger
    if _diagnostic_logger is None:
        _diagnostic_logger = DiagnosticLogger()
    return _diagnostic_logger


# Convenience functions
def start_operation(operation: str, context: Dict[str, Any] = None) -> str:
    """Start tracking an operation."""
    return get_diagnostic_logger().start_operation(operation, context)


def end_operation(operation_id: str, success: bool = True, 
                 error_message: Optional[str] = None, result_summary: Optional[str] = None):
    """End tracking an operation."""
    get_diagnostic_logger().end_operation(operation_id, success, error_message, result_summary)


def log_conversation_start(conversation_id: str, user_query: str):
    """Log conversation start."""
    get_diagnostic_logger().log_conversation_start(conversation_id, user_query)


def log_tool_usage(tool_name: str, parameters: Dict[str, Any] = None):
    """Log tool usage."""
    get_diagnostic_logger().log_tool_usage(tool_name, parameters)


def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "WARNING"):
    """Log security event."""
    get_diagnostic_logger().log_security_event(event_type, details, severity)


def get_performance_summary(hours: int = 24) -> Dict[str, Any]:
    """Get performance summary."""
    return get_diagnostic_logger().get_performance_summary(hours)


def get_usage_statistics() -> Dict[str, Any]:
    """Get usage statistics."""
    return get_diagnostic_logger().get_usage_statistics()


def export_diagnostics(output_file: Optional[Path] = None) -> Path:
    """Export diagnostics."""
    return get_diagnostic_logger().export_diagnostics(output_file)


def health_check() -> Dict[str, Any]:
    """Perform health check."""
    return get_diagnostic_logger().health_check()
