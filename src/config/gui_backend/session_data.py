"""Thread safe session data storage."""

from threading import Lock
from typing import Any, Dict


class SessionData:
    """
    The SessionData class.

    The SessionData class is used to store the session data in a thread safe
    way.
    """

    def __init__(self):
        """Initialize the SessionData."""
        self._session_data: Dict[str, Any] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any:
        """Get the value of the key."""
        with self._lock:
            return self._session_data.get(key)

    def set(self, key: str, value: Any):
        """Set the value of the key."""
        with self._lock:
            self._session_data[key] = value

    def delete(self, key: str):
        """Delete the key."""
        with self._lock:
            self._session_data.pop(key, None)

    def clear(self):
        """Clear the session data."""
        with self._lock:
            self._session_data.clear()

    def __getitem__(self, key: str):
        """Get the value of the key."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any):
        """Set the value of the key."""
        self.set(key, value)

    def __delitem__(self, key: str):
        """Delete the key."""
        self.delete(key)

    def __len__(self):
        """Get the length of the session data."""
        with self._lock:
            return len(self._session_data)

    def __contains__(self, key: str):
        """Check if the key is in the session data."""
        with self._lock:
            return key in self._session_data

    def __iter__(self):
        """Iterate over the session data."""
        with self._lock:
            return iter(self._session_data)
