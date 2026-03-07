"""
Adapter registry for managing channel adapters.

This module provides a centralized registry for all channel adapters,
allowing easy lookup by platform ID and capability queries.

设计参考:
- OpenClaw Channel Registry: https://github.com/openclaw/openclaw/blob/main/src/channels/registry.ts
"""
from typing import Dict, Optional, Type

from loguru import logger

from src.adapters.base import BaseAdapter


class AdapterRegistry:
    """
    Registry for managing channel adapters.

    Provides:
    - Registration of adapters by platform ID
    - Lazy loading of adapters
    - Capability queries
    - Health status tracking
    """

    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {}
        self._adapter_classes: Dict[str, Type[BaseAdapter]] = {}
        self._adapter_configs: Dict[str, dict] = {}

    def register_adapter_class(
        self,
        platform_id: str,
        adapter_class: Type[BaseAdapter],
        config: dict
    ) -> None:
        """
        Register an adapter class for lazy loading.

        Args:
            platform_id: Unique platform identifier (e.g., 'telegram', 'feishu')
            adapter_class: Adapter class (not instance)
            config: Configuration for the adapter
        """
        self._adapter_classes[platform_id] = adapter_class
        self._adapter_configs[platform_id] = config
        logger.info(f"Registered adapter class: {platform_id} -> {adapter_class.__name__}")

    def get_adapter(self, platform_id: str) -> Optional[BaseAdapter]:
        """
        Get an adapter instance, creating it if necessary.

        Args:
            platform_id: Platform identifier

        Returns:
            Adapter instance or None if not registered
        """
        # Return cached instance if available
        if platform_id in self._adapters:
            return self._adapters[platform_id]

        # Create instance if class is registered
        if platform_id in self._adapter_classes:
            adapter_class = self._adapter_classes[platform_id]
            config = self._adapter_configs.get(platform_id, {})
            adapter = adapter_class(config)
            self._adapters[platform_id] = adapter
            logger.info(f"Created adapter instance: {platform_id}")
            return adapter

        return None

    def register_adapter_instance(self, adapter: BaseAdapter) -> None:
        """
        Register an already-created adapter instance.

        Args:
            adapter: Adapter instance
        """
        platform_id = adapter.platform_id
        self._adapters[platform_id] = adapter
        logger.info(f"Registered adapter instance: {platform_id}")

    def remove_adapter(self, platform_id: str) -> None:
        """
        Remove an adapter from the registry.

        Args:
            platform_id: Platform identifier
        """
        if platform_id in self._adapters:
            del self._adapters[platform_id]
            logger.info(f"Removed adapter: {platform_id}")

    def list_adapters(self) -> list[str]:
        """
        List all registered platform IDs.

        Returns:
            List of platform IDs
        """
        return list(self._adapter_classes.keys())

    def list_active_adapters(self) -> list[str]:
        """
        List all active (created) adapter platform IDs.

        Returns:
            List of platform IDs with active adapters
        """
        return list(self._adapters.keys())

    def has_adapter(self, platform_id: str) -> bool:
        """
        Check if an adapter is registered.

        Args:
            platform_id: Platform identifier

        Returns:
            True if adapter is registered
        """
        return platform_id in self._adapter_classes

    def is_adapter_enabled(self, platform_id: str) -> bool:
        """
        Check if an adapter is enabled.

        Args:
            platform_id: Platform identifier

        Returns:
            True if adapter exists and is enabled
        """
        adapter = self.get_adapter(platform_id)
        return adapter is not None and adapter.is_enabled()

    def get_capabilities(self, platform_id: str) -> Optional[dict]:
        """
        Get capabilities for a platform without creating the adapter.

        Args:
            platform_id: Platform identifier

        Returns:
            Capabilities dict or None
        """
        adapter = self.get_adapter(platform_id)
        if adapter:
            return adapter.capabilities.to_dict()
        return None

    async def connect_all(self) -> Dict[str, bool]:
        """
        Connect all registered adapters.

        Returns:
            Dict mapping platform_id to connection success
        """
        results = {}
        for platform_id in self._adapter_classes:
            adapter = self.get_adapter(platform_id)
            if adapter:
                try:
                    results[platform_id] = await adapter.connect()
                except Exception as e:
                    logger.error(f"Failed to connect {platform_id}: {e}")
                    results[platform_id] = False
        return results

    async def disconnect_all(self) -> None:
        """Disconnect all active adapters."""
        for adapter in self._adapters.values():
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {adapter.platform_id}: {e}")

    async def health_check_all(self) -> Dict[str, dict]:
        """
        Check health status of all registered adapters.

        Returns:
            Dict mapping platform_id to health status
        """
        results = {}
        for platform_id in self._adapter_classes:
            try:
                adapter = self.get_adapter(platform_id)
                if adapter:
                    results[platform_id] = await adapter.health_check()
                else:
                    results[platform_id] = {
                        "healthy": False,
                        "message": "Adapter not initialized",
                        "platform": platform_id,
                    }
            except Exception as e:
                logger.error(f"Health check failed for {platform_id}: {e}")
                results[platform_id] = {
                    "healthy": False,
                    "message": str(e),
                    "platform": platform_id,
                }
        return results


# Global registry instance
_global_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Get the global adapter registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AdapterRegistry()
    return _global_registry


def register_adapter(
    platform_id: str,
    adapter_class: Type[BaseAdapter],
    config: dict
) -> None:
    """
    Register an adapter to the global registry.

    Args:
        platform_id: Unique platform identifier
        adapter_class: Adapter class
        config: Configuration dict
    """
    get_adapter_registry().register_adapter_class(platform_id, adapter_class, config)


def get_adapter(platform_id: str) -> Optional[BaseAdapter]:
    """
    Get an adapter from the global registry.

    Args:
        platform_id: Platform identifier

    Returns:
        Adapter instance or None
    """
    return get_adapter_registry().get_adapter(platform_id)
