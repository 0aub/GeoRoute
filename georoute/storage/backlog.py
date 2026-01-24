"""
Backlog storage for tactical planning requests.
In-memory storage for now (can upgrade to SQLite/Postgres later).
"""

from typing import Optional
from datetime import datetime
from collections import OrderedDict

from ..models.tactical import BacklogEntry


class BacklogStore:
    """
    Thread-safe in-memory storage for planning request backlog.

    Stores complete audit trails of tactical planning requests including:
    - User input
    - All API calls made
    - All Gemini requests/responses
    - Generated routes
    - Images sent to Gemini
    """

    def __init__(self, max_entries: int = 100):
        """
        Initialize backlog store.

        Args:
            max_entries: Maximum number of entries to keep (oldest are dropped)
        """
        self.max_entries = max_entries
        self._store: OrderedDict[str, BacklogEntry] = OrderedDict()

    def add_entry(self, entry: BacklogEntry) -> None:
        """
        Add a new backlog entry.

        Args:
            entry: Complete backlog entry to store
        """
        # Add to store
        self._store[entry.request_id] = entry

        # Move to end (most recent)
        self._store.move_to_end(entry.request_id)

        # Trim if exceeds max
        while len(self._store) > self.max_entries:
            self._store.popitem(last=False)  # Remove oldest

    def get_entry(self, request_id: str) -> Optional[BacklogEntry]:
        """
        Get a specific backlog entry by ID.

        Args:
            request_id: UUID of the request

        Returns:
            BacklogEntry if found, None otherwise
        """
        return self._store.get(request_id)

    def list_entries(
        self,
        limit: int = 50,
        offset: int = 0,
        since: Optional[datetime] = None,
    ) -> list[BacklogEntry]:
        """
        List backlog entries (newest first).

        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            since: Only return entries after this timestamp

        Returns:
            List of backlog entries
        """
        # Get all entries (newest first)
        entries = list(reversed(self._store.values()))

        # Filter by timestamp if specified
        if since:
            entries = [e for e in entries if e.timestamp >= since]

        # Apply offset and limit
        return entries[offset : offset + limit]

    def count(self, since: Optional[datetime] = None) -> int:
        """
        Count total entries.

        Args:
            since: Only count entries after this timestamp

        Returns:
            Number of entries
        """
        if since is None:
            return len(self._store)

        return sum(1 for e in self._store.values() if e.timestamp >= since)

    def clear(self) -> None:
        """Clear all entries (useful for testing)."""
        self._store.clear()

    def get_images(self, request_id: str) -> dict[str, Optional[str]]:
        """
        Get images for a specific request.

        Args:
            request_id: UUID of the request

        Returns:
            Dict with satellite_image and terrain_image (base64 encoded)
        """
        entry = self.get_entry(request_id)
        if not entry:
            return {"satellite_image": None, "terrain_image": None}

        return {
            "satellite_image": entry.satellite_image,
            "terrain_image": entry.terrain_image,
        }


# Global singleton instance
_backlog_store: Optional[BacklogStore] = None


def get_backlog_store() -> BacklogStore:
    """Get the global backlog store instance."""
    global _backlog_store
    if _backlog_store is None:
        _backlog_store = BacklogStore(max_entries=100)
    return _backlog_store
