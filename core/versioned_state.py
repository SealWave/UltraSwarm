"""
core/versioned_state.py
=======================
Thread-safe versioned state for agents.
Handles shared state safely with versioning and conflict detection.
"""

import threading
from datetime import datetime
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class VersionedValue:
    """A versioned value with metadata"""
    value: Any
    version: int
    timestamp: datetime
    writer: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class VersionedState:
    """
    Thread-safe versioned state for agents.
    Handles shared state safely with versioning and conflict detection.
    
    Features:
    - Version tracking per key
    - Lock-based critical section handling
    - Conflict detection on read/write
    - Thread-safe operations
    """
    
    def __init__(self):
        self._state: Dict[str, VersionedValue] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        self._access_log: List[Dict[str, Any]] = []
    
    def acquire_lock(self, resource_name: str, timeout: float = 0.1) -> bool:
        """
        Acquire lock on a shared resource.
        
        Args:
            resource_name: Name of the resource to lock
            timeout: Lock acquisition timeout in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        with self._global_lock:
            if resource_name not in self._locks:
                self._locks[resource_name] = threading.Lock()
        
        acquired = self._locks[resource_name].acquire(blocking=True, timeout=timeout)
        if acquired:
            self._log_access(resource_name, "lock_acquired")
        return acquired
    
    def release_lock(self, resource_name: str):
        """Release lock on a shared resource"""
        if resource_name in self._locks:
            try:
                self._locks[resource_name].release()
                self._log_access(resource_name, "lock_released")
            except RuntimeError:
                pass  # Lock not held
    
    def read(self, key: str) -> Tuple[Optional[Any], Optional[int]]:
        """
        Read value with version.
        
        Args:
            key: The key to read
            
        Returns:
            Tuple of (value, version) or (None, None) if not found
        """
        with self._global_lock:
            if key in self._state:
                val = self._state[key]
                self._log_access(key, "read", val.writer)
                return val.value, val.version
            return None, None
    
    def read_with_metadata(self, key: str) -> Optional[VersionedValue]:
        """
        Read value with full metadata.
        
        Args:
            key: The key to read
            
        Returns:
            VersionedValue or None if not found
        """
        with self._global_lock:
            if key in self._state:
                val = self._state[key]
                self._log_access(key, "read_with_metadata", val.writer)
                return val
            return None
    
    def write(self, key: str, value: Any, writer: str, metadata: Dict[str, Any] = None) -> int:
        """
        Write value with version increment.
        
        Args:
            key: The key to write
            value: The value to store
            writer: Name of the agent writing the value
            metadata: Optional metadata to attach to the value
            
        Returns:
            New version number
        """
        with self._global_lock:
            current = self._state.get(key)
            current_version = current.version if current else 0
            new_version = current_version + 1
            
            self._state[key] = VersionedValue(
                value=value,
                version=new_version,
                timestamp=datetime.utcnow(),
                writer=writer,
                metadata=metadata or {}
            )
            self._log_access(key, "write", writer, new_version)
            return new_version
    
    def get_conflict(self, key: str, expected_version: int) -> Optional[str]:
        """
        Check if there's a conflict (version mismatch).
        
        Args:
            key: The key to check
            expected_version: The version expected by the reader
            
        Returns:
            Error message if conflict, None if no conflict
        """
        with self._global_lock:
            if key in self._state:
                current_version = self._state[key].version
                if current_version != expected_version:
                    writer = self._state[key].writer
                    return f"Version mismatch for '{key}': expected {expected_version}, got {current_version} (last writer: {writer})"
            return None
    
    def check_conflict_free(
        self, 
        key: str, 
        expected_version: int, 
        new_value: Any, 
        writer: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Atomically check for conflict and write if no conflict.
        
        Args:
            key: The key to check and write
            expected_version: The version expected by the reader
            new_value: The new value to write
            writer: Name of the agent writing
            metadata: Optional metadata to attach
            
        Returns:
            True if write succeeded, False if conflict detected
        """
        with self._global_lock:
            if key in self._state:
                current_version = self._state[key].version
                if current_version != expected_version:
                    self._log_access(key, "conflict_detected", writer, current_version)
                    return False
            
            self._state[key] = VersionedValue(
                value=new_value,
                version=expected_version + 1,
                timestamp=datetime.utcnow(),
                writer=writer,
                metadata=metadata or {}
            )
            self._log_access(key, "write_conflict_free", writer, expected_version + 1)
            return True
    
    def delete(self, key: str, writer: str) -> bool:
        """
        Delete a key from state.
        
        Args:
            key: The key to delete
            writer: Name of the agent deleting the key
            
        Returns:
            True if key existed and was deleted, False if key didn't exist
        """
        with self._global_lock:
            if key in self._state:
                del self._state[key]
                self._log_access(key, "delete", writer)
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in state"""
        with self._global_lock:
            return key in self._state
    
    def get_all_keys(self) -> List[str]:
        """Get all keys in state"""
        with self._global_lock:
            return list(self._state.keys())
    
    def get_version_history(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get version information for a key.
        
        Args:
            key: The key to check
            
        Returns:
            Dict with version info or None if key doesn't exist
        """
        with self._global_lock:
            if key in self._state:
                val = self._state[key]
                return {
                    "version": val.version,
                    "timestamp": val.timestamp.isoformat(),
                    "writer": val.writer,
                    "metadata": val.metadata
                }
            return None
    
    def _log_access(self, key: str, action: str, writer: str = None, version: int = None):
        """Log an access for debugging/auditing"""
        self._access_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "key": key,
            "action": action,
            "writer": writer,
            "version": version
        })
        # Keep log bounded
        if len(self._access_log) > 1000:
            self._access_log = self._access_log[-500:]
    
    def get_access_log(self, key: str = None) -> List[Dict[str, Any]]:
        """
        Get access log, optionally filtered by key.
        
        Args:
            key: Optional key to filter by
            
        Returns:
            List of access log entries
        """
        with self._global_lock:
            if key:
                return [entry for entry in self._access_log if entry["key"] == key]
            return self._access_log.copy()
    
    def clear_all(self):
        """Clear all state (useful for testing)"""
        with self._global_lock:
            self._state.clear()
            self._access_log.clear()
    
    def snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of the entire state"""
        with self._global_lock:
            return {
                key: {
                    "value": val.value,
                    "version": val.version,
                    "timestamp": val.timestamp.isoformat(),
                    "writer": val.writer,
                    "metadata": val.metadata
                }
                for key, val in self._state.items()
            }


# Global versioned state instance
_versioned_state = None


def get_versioned_state() -> VersionedState:
    """Get or create the global versioned state instance"""
    global _versioned_state
    if _versioned_state is None:
        _versioned_state = VersionedState()
    return _versioned_state
