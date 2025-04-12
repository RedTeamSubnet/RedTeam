import collections
from typing import Any, Generic, Optional, TypeVar, Union, TYPE_CHECKING, Iterator

from redteam_core.validator.models import ComparisonLog, ScoringLog

T = TypeVar('T')
KT = TypeVar('KT')  # Key type

class LRUCache(Generic[KT, T]):
    """
    A simple LRU (Least Recently Used) cache implementation.
    Uses OrderedDict to keep track of access order.
    """

    def __init__(self, maxsize: int):
        """
        Initialize the LRU cache with a maximum size.

        Args:
            maxsize: Maximum size of the cache
        """
        self.maxsize: int = maxsize
        self.cache: collections.OrderedDict[KT, T] = collections.OrderedDict()
        self.evictions: int = 0

    def get(self, key: KT) -> Optional[T]:
        """
        Get an item from the cache and mark it as recently used.

        Args:
            key: The key to look up

        Returns:
            The value if found, None otherwise
        """
        if key not in self.cache:
            return None

        # Move to end (mark as recently used)
        value = self.cache.pop(key)
        self.cache[key] = value
        return value

    def set(self, key: KT, value: T) -> None:
        """
        Add or update an item in the cache.

        Args:
            key: The key to set
            value: The value to set
        """
        # If key exists, remove it first
        if key in self.cache:
            self.cache.pop(key)

        # If cache is full, remove oldest item
        if len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)  # Remove first item (oldest)
            self.evictions += 1

        # Add new item
        self.cache[key] = value

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()

    def __len__(self) -> int:
        """Return number of items in cache."""
        return len(self.cache)

    def __contains__(self, key: KT) -> bool:
        """Support 'in' operator."""
        return key in self.cache

    def __getitem__(self, key: KT) -> T:
        """Support dict-like access."""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: KT, value: T) -> None:
        """Support dict-like assignment."""
        self.set(key, value)

    def keys(self) -> Iterator[KT]:
        """Return all keys in the cache."""
        return self.cache.keys()

    def values(self) -> Iterator[T]:
        """Return all values in the cache."""
        return self.cache.values()

    def items(self) -> Iterator[tuple[KT, T]]:
        """Return all (key, value) pairs in the cache."""
        return self.cache.items()

    def pop(self, key: KT, default: Optional[T] = None) -> Optional[T]:
        """Remove and return an item from the cache."""
        return self.cache.pop(key, default)


# Define the specific type for scoring results
if TYPE_CHECKING:
    ScoringResultType = dict[str, Union[list[ScoringLog], dict[str, list[ComparisonLog]]]]
else:
    ScoringResultType = dict[str, Any]


class ScoringLRUCache:
    """
    Specialized LRU cache for storing scoring results by challenge and docker_hub_id.
    Provides a clean interface for working with scoring results while managing memory usage.
    """

    def __init__(self, challenges: list[str], maxsize_per_challenge: int = 256):
        """
        Initialize the scoring cache with a separate LRU cache for each challenge.

        Args:
            challenges: List of challenge names to initialize caches for
            maxsize_per_challenge: Maximum number of entries per challenge cache
        """
        self.maxsize_per_challenge: int = maxsize_per_challenge
        self.caches: dict[str, LRUCache[str, ScoringResultType]] = {}
        for challenge in challenges:
            self.caches[challenge] = LRUCache[str, ScoringResultType](maxsize=self.maxsize_per_challenge)

        self.hits: int = 0
        self.misses: int = 0

    def get(self, challenge: str, docker_hub_id: str) -> Optional[ScoringResultType]:
        """
        Get scoring result for a specific challenge and docker_hub_id.

        Args:
            challenge: Challenge name
            docker_hub_id: Docker hub ID

        Returns:
            The scoring result or None if not found
        """
        if challenge not in self.caches:
            self.misses += 1
            return None

        result = self.caches[challenge].get(docker_hub_id)
        if result:
            self.hits += 1
        else:
            self.misses += 1

        return result

    def set(self, challenge: str, docker_hub_id: str, result: ScoringResultType) -> None:
        """
        Store scoring result for a specific challenge and docker_hub_id.

        Args:
            challenge: Challenge name
            docker_hub_id: Docker hub ID
            result: Scoring result to store
        """
        if challenge not in self.caches:
            # Create a new cache if it doesn't exist
            self.caches[challenge] = LRUCache[str, ScoringResultType](maxsize=self.maxsize_per_challenge)

        self.caches[challenge].set(docker_hub_id, result)

    def get_all_for_challenge(self, challenge: str) -> dict[str, ScoringResultType]:
        """
        Get all cached results for a specific challenge.

        Args:
            challenge: Challenge name

        Returns:
            Dictionary mapping docker_hub_id to scoring result
        """
        if challenge not in self.caches:
            return {}

        return dict(self.caches[challenge].items())

    def get_challenges(self) -> set[str]:
        """
        Get all challenge names that have caches.

        Returns:
            Set of challenge names
        """
        return set(self.caches.keys())

    def clear_challenge(self, challenge: str) -> None:
        """
        Clear all cached results for a specific challenge.

        Args:
            challenge: Challenge name to clear
        """
        if challenge in self.caches:
            self.caches[challenge].clear()

    def clear_all(self) -> None:
        """
        Clear all cached results for all challenges.
        """
        for cache in self.caches.values():
            cache.clear()

    def contains(self, challenge: str, docker_hub_id: str) -> bool:
        """
        Check if a specific docker_hub_id exists in the cache for a challenge.

        Args:
            challenge: Challenge name
            docker_hub_id: Docker hub ID to check

        Returns:
            True if the entry exists, False otherwise
        """
        return challenge in self.caches and docker_hub_id in self.caches[challenge]

    def remove(self, challenge: str, docker_hub_id: str) -> bool:
        """
        Remove a specific entry from the cache.

        Args:
            challenge: Challenge name
            docker_hub_id: Docker hub ID to remove

        Returns:
            True if the entry was removed, False if it didn't exist
        """
        if challenge in self.caches and docker_hub_id in self.caches[challenge]:
            self.caches[challenge].pop(docker_hub_id)
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit/miss/eviction statistics
        """
        total_evictions = sum(cache.evictions for cache in self.caches.values())
        total_entries = sum(len(cache) for cache in self.caches.values())
        challenge_counts = {
            challenge: len(cache)
            for challenge, cache in self.caches.items()
        }

        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": total_evictions,
            "total_entries": total_entries,
            "challenge_counts": challenge_counts
        }

    def log_stats(self) -> None:
        """
        Log cache statistics.
        """
        stats = self.get_stats()
        import bittensor as bt
        bt.logging.info(f"ScoringLRUCache stats: {stats}")

    def setdefault(self, challenge: str, docker_hub_id: str, default: ScoringResultType) -> ScoringResultType:
        """
        Get the value for a key, setting it to default if not present.

        Args:
            challenge: Challenge name
            docker_hub_id: Docker hub ID
            default: Default value to use if key is not present

        Returns:
            The existing or new value
        """
        if challenge not in self.caches:
            self.caches[challenge] = LRUCache[str, ScoringResultType](maxsize=self.maxsize_per_challenge)

        result = self.caches[challenge].get(docker_hub_id)
        if result is None:
            self.caches[challenge].set(docker_hub_id, default)
            return default

        return result