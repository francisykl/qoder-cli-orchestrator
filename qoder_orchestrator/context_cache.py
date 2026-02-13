#!/usr/bin/env python3
"""
Context caching for improved performance.
Implements LRU cache with disk persistence.
"""

import os
import time
import pickle
import hashlib
from pathlib import Path
from typing import Optional, Any, Dict
from collections import OrderedDict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entry in the cache."""
    key: str
    value: Any
    timestamp: float
    size_bytes: int


class ContextCache:
    """LRU cache for context with disk persistence."""
    
    def __init__(self, config: Any, cache_dir: Optional[Path] = None):
        """
        Initialize context cache.
        
        Args:
            config: CacheConfig instance
            cache_dir: Directory for cache storage
        """
        self.config = config
        self.cache_dir = cache_dir or Path(config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_size_bytes = 0
        self.max_size_bytes = config.max_size_mb * 1024 * 1024
        
        # Statistics
        self.hits = 0
        self.misses = 0
        
        if config.enabled:
            self._load_from_disk()
    
    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        key_str = "|".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            return len(pickle.dumps(value))
        except:
            return 1024  # Default estimate
    
    def get(self, *args) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            *args: Arguments to generate cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self.config.enabled:
            return None
        
        key = self._get_cache_key(*args)
        
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if time.time() - entry.timestamp > self.config.ttl_seconds:
            logger.debug(f"Cache entry expired: {key[:8]}")
            self.cache.pop(key)
            self.current_size_bytes -= entry.size_bytes
            self.misses += 1
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        
        self.hits += 1
        logger.debug(f"Cache hit: {key[:8]}")
        return entry.value
    
    def put(self, value: Any, *args):
        """
        Put value in cache.
        
        Args:
            value: Value to cache
            *args: Arguments to generate cache key
        """
        if not self.config.enabled:
            return
        
        key = self._get_cache_key(*args)
        size = self._estimate_size(value)
        
        # Check if value is too large
        if size > self.max_size_bytes:
            logger.warning(f"Value too large for cache: {size} bytes")
            return
        
        # Remove existing entry if present
        if key in self.cache:
            old_entry = self.cache.pop(key)
            self.current_size_bytes -= old_entry.size_bytes
        
        # Evict entries if needed
        while self.current_size_bytes + size > self.max_size_bytes and self.cache:
            evicted_key, evicted_entry = self.cache.popitem(last=False)
            self.current_size_bytes -= evicted_entry.size_bytes
            logger.debug(f"Evicted cache entry: {evicted_key[:8]}")
        
        # Add new entry
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            size_bytes=size
        )
        
        self.cache[key] = entry
        self.current_size_bytes += size
        
        logger.debug(f"Cached: {key[:8]} ({size} bytes)")
        
        # Periodically save to disk
        if len(self.cache) % 10 == 0:
            self._save_to_disk()
    
    def _load_from_disk(self):
        """Load cache from disk."""
        cache_file = self.cache_dir / "context_cache.pkl"
        
        if not cache_file.exists():
            return
        
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                
            # Restore cache entries
            for key, entry in data.items():
                # Check if expired
                if time.time() - entry.timestamp <= self.config.ttl_seconds:
                    self.cache[key] = entry
                    self.current_size_bytes += entry.size_bytes
            
            logger.info(f"Loaded {len(self.cache)} entries from cache")
            
        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")
    
    def _save_to_disk(self):
        """Save cache to disk."""
        cache_file = self.cache_dir / "context_cache.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(dict(self.cache), f)
            
            logger.debug(f"Saved {len(self.cache)} entries to disk")
            
        except Exception as e:
            logger.warning(f"Failed to save cache to disk: {e}")
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.current_size_bytes = 0
        self.hits = 0
        self.misses = 0
        
        cache_file = self.cache_dir / "context_cache.pkl"
        if cache_file.exists():
            cache_file.unlink()
        
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "enabled": self.config.enabled,
            "entries": len(self.cache),
            "size_mb": self.current_size_bytes / (1024 * 1024),
            "max_size_mb": self.config.max_size_mb,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.config.ttl_seconds
        }
    
    def print_stats(self):
        """Print cache statistics."""
        stats = self.get_stats()
        
        print("\n" + "="*40)
        print("CACHE STATISTICS")
        print("="*40)
        print(f"Enabled: {stats['enabled']}")
        print(f"Entries: {stats['entries']}")
        print(f"Size: {stats['size_mb']:.2f} MB / {stats['max_size_mb']} MB")
        print(f"Hits: {stats['hits']}")
        print(f"Misses: {stats['misses']}")
        print(f"Hit Rate: {stats['hit_rate']:.1%}")
        print(f"TTL: {stats['ttl_seconds']}s")
        print("="*40 + "\n")
    
    def __del__(self):
        """Save cache on destruction."""
        if self.config.enabled:
            self._save_to_disk()
