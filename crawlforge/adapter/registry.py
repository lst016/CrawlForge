"""
Game Adapter Registry - central registry for all game adapters.

Provides:
- Adapter registration and lookup
- Lazy loading of adapter modules
- Game configuration from YAML
- Adapter factory pattern
"""

import importlib
import inspect
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Type, Any

from .base import GameAdapter, AdapterConfig, AdapterMetadata

logger = logging.getLogger(__name__)


@dataclass
class RegisteredAdapter:
    """A registered adapter entry."""
    adapter_class: Type[GameAdapter]
    metadata: AdapterMetadata
    config_schema: dict = field(default_factory=dict)
    module_path: str = ""


class AdapterRegistry:
    """
    Central registry for all game adapters.

    Usage:
        registry = AdapterRegistry()

        # Register an adapter
        registry.register(MyGameAdapter, game_name="MyGame")

        # Create an adapter instance
        adapter = registry.create("MyGame", runtime=my_runtime)

        # List all registered adapters
        for name, entry in registry.list_adapters():
            print(name, entry.metadata.game_type)
    """

    _instance: Optional["AdapterRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._adapters: dict[str, RegisteredAdapter] = {}
        self._initialized = True
        self._yaml_configs: dict[str, dict] = {}

    def register(
        self,
        adapter_class: Type[GameAdapter],
        game_name: Optional[str] = None,
        metadata: Optional[AdapterMetadata] = None,
    ) -> None:
        """
        Register an adapter class.

        Args:
            adapter_class: The adapter class to register
            game_name: Override the game name (uses class docstring or name if None)
            metadata: Optional adapter metadata
        """
        name = game_name or self._derive_game_name(adapter_class)

        if metadata is None:
            # Try to extract from class
            metadata = self._extract_metadata(adapter_class, name)

        entry = RegisteredAdapter(
            adapter_class=adapter_class,
            metadata=metadata,
            module_path=inspect.getfile(adapter_class),
        )
        self._adapters[name] = entry
        logger.debug(f"Registered adapter: {name}")

    def unregister(self, game_name: str) -> bool:
        """Unregister an adapter."""
        if game_name in self._adapters:
            del self._adapters[game_name]
            return True
        return False

    def get(self, game_name: str) -> Optional[RegisteredAdapter]:
        """Get a registered adapter by game name."""
        return self._adapters.get(game_name)

    def get_adapter_class(self, game_name: str) -> Optional[Type[GameAdapter]]:
        """Get an adapter class by game name."""
        entry = self._adapters.get(game_name)
        return entry.adapter_class if entry else None

    def create(
        self,
        game_name: str,
        runtime: Any,
        config: Optional[dict] = None,
        **kwargs,
    ) -> Optional[GameAdapter]:
        """
        Create an instance of a registered adapter.

        Args:
            game_name: Name of the registered adapter
            runtime: Runtime instance to pass to adapter
            config: Optional configuration dict
            **kwargs: Additional args passed to adapter constructor

        Returns:
            Adapter instance or None if not found
        """
        entry = self._adapters.get(game_name)
        if entry is None:
            logger.warning(f"Adapter not registered: {game_name}")
            return None

        adapter_config = None
        if config:
            adapter_config = AdapterConfig(
                game_name=game_name,
                runtime=runtime,
                **(config or {}),
            )

        try:
            adapter = entry.adapter_class(
                runtime=runtime,
                game_name=game_name,
                config=adapter_config,
                **kwargs,
            )
            return adapter
        except Exception as e:
            logger.error(f"Failed to create adapter {game_name}: {e}")
            return None

    def list_adapters(self) -> list[tuple[str, RegisteredAdapter]]:
        """List all registered adapters."""
        return sorted(self._adapters.items(), key=lambda x: x[0])

    def list_game_names(self) -> list[str]:
        """List all registered game names."""
        return sorted(self._adapters.keys())

    def load_from_yaml(self, yaml_path: Path) -> int:
        """
        Load adapter configurations from a YAML file.

        The YAML file should have entries like:
            games:
              - name: MySlotGame
                adapter: my_game_adapter.MySlotAdapter
                type: slot
                config:
                  confidence_threshold: 0.8
                  default_bet: 200

        Returns the number of configs loaded.
        """
        import yaml

        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            logger.warning(f"YAML config not found: {yaml_path}")
            return 0

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        count = 0
        games = data.get("games", [])
        for game in games:
            name = game.get("name")
            if not name:
                continue

            self._yaml_configs[name] = game
            count += 1

        return count

    def get_yaml_config(self, game_name: str) -> Optional[dict]:
        """Get YAML config for a game."""
        return self._yaml_configs.get(game_name)

    def get_config_for_game(self, game_name: str) -> dict:
        """
        Get merged configuration for a game from YAML + defaults.
        """
        base = {
            "confidence_threshold": 0.7,
            "max_retries": 3,
            "retry_delay_ms": 500,
            "default_bet": 100,
            "max_bet": 10000,
            "auto_collect": True,
            "screenshot_interval_ms": 200,
            "action_cooldown_ms": 300,
        }

        yaml_cfg = self._yaml_configs.get(game_name, {})
        game_config = yaml_cfg.get("config", {})
        base.update(game_config)

        return base

    def auto_register_builtins(self) -> None:
        """
        Auto-register all built-in adapters from the adapters package.
        """
        from .slot_adapter import SlotGameAdapter
        from .poker_adapter import PokerGameAdapter
        from .arcade_adapter import ArcadeGameAdapter

        self.register(
            SlotGameAdapter,
            metadata=AdapterMetadata(
                adapter_id="builtin-slot",
                game_name="SlotGame",
                game_type="slot",
                version="1.0",
                supported_phases=["idle", "spinning", "win", "bonus", "free_spin"],
                capabilities=["auto_spin", "bet_adjust", "collect", "free_spin"],
            ),
        )

    @staticmethod
    def _derive_game_name(adapter_class: Type[GameAdapter]) -> str:
        """Derive game name from class name."""
        name = adapter_class.__name__
        # Remove "Adapter" suffix
        if name.endswith("Adapter"):
            name = name[:-7]
        return name

    @staticmethod
    def _extract_metadata(
        adapter_class: Type[GameAdapter],
        game_name: str,
    ) -> AdapterMetadata:
        """Extract metadata from adapter class."""
        doc = inspect.getdoc(adapter_class)
        return AdapterMetadata(
            adapter_id=f"auto-{game_name.lower().replace(' ', '-')}",
            game_name=game_name,
            game_type="unknown",
            version="1.0",
            description=doc or "",
        )


# Global registry instance
_default_registry: Optional[AdapterRegistry] = None


def get_registry() -> AdapterRegistry:
    """Get the default registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = AdapterRegistry()
        _default_registry.auto_register_builtins()
    return _default_registry


def register_adapter(
    adapter_class: Type[GameAdapter],
    game_name: Optional[str] = None,
) -> None:
    """Convenience function to register an adapter."""
    get_registry().register(adapter_class, game_name=game_name)


def create_adapter(
    game_name: str,
    runtime: Any,
    config: Optional[dict] = None,
    **kwargs,
) -> Optional[GameAdapter]:
    """Convenience function to create an adapter."""
    return get_registry().create(game_name, runtime, config=config, **kwargs)
