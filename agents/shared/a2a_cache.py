"""
Global A2A Client Cache
Lazy loads and caches A2A clients to avoid repeated expensive creation
"""
import logging
from typing import Dict, Optional
from strands_tools.a2a_client import A2AClientToolProvider

logger = logging.getLogger(__name__)

class A2AClientCache:
    """Global cache for A2A clients to avoid repeated creation"""
    
    _instance = None
    _providers: Dict[str, A2AClientToolProvider] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_provider(self, agent_urls: list, cache_key: str = None) -> A2AClientToolProvider:
        """Get or create A2A client provider with caching and stale connection handling"""
        if cache_key is None:
            cache_key = "_".join(sorted(agent_urls))
        
        if cache_key not in self._providers:
            logger.info(f"🔧 Creating new A2A provider for cache key: {cache_key}")
            try:
                self._providers[cache_key] = A2AClientToolProvider(known_agent_urls=agent_urls)
                logger.info(f"✅ A2A provider cached with {len(self._providers[cache_key].tools)} tools")
            except Exception as e:
                logger.error(f"❌ Failed to create A2A provider: {e}")
                raise
        else:
            # Force recreation every 10 minutes to avoid stale connections
            import time
            if not hasattr(self, '_creation_times'):
                self._creation_times = {}
            
            current_time = time.time()
            if cache_key not in self._creation_times:
                self._creation_times[cache_key] = current_time
            elif current_time - self._creation_times[cache_key] > 600:  # 10 minutes
                logger.info(f"🔄 Recreating A2A provider due to age: {cache_key}")
                del self._providers[cache_key]
                self._providers[cache_key] = A2AClientToolProvider(known_agent_urls=agent_urls)
                self._creation_times[cache_key] = current_time
            else:
                logger.info(f"♻️ Reusing cached A2A provider for: {cache_key}")
        
        return self._providers[cache_key]
    
    def clear_cache(self):
        """Clear all cached providers"""
        logger.info("🗑️ Clearing A2A client cache")
        self._providers.clear()

# Global instance
a2a_cache = A2AClientCache()