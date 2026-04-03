"""
Threshold configuration registry with YAML persistence.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from .config import MatchingMethod, ThresholdConfig

logger = logging.getLogger(__name__)


class ThresholdConfigRegistry:
    """
    Registry of threshold configs per game/element.

    YAML format:
        game_id:
            element_type:
                template_path: "path/to/template.png"
                default_threshold: 0.8
                calibrated_threshold: 0.85
                matching_method: tm_sqdiff
                scale_range: [0.8, 1.2]
                use_grayscale: true
                preprocessed: true
    """

    def __init__(self):
        self._configs: dict[str, dict[str, ThresholdConfig]] = {}  # game_id → element_type → config

    def register(self, game_id: str, element_type: str, config: ThresholdConfig) -> None:
        """Register a threshold config for a game element."""
        if game_id not in self._configs:
            self._configs[game_id] = {}
        self._configs[game_id][element_type] = config

    def get(self, game_id: str, element_type: str) -> Optional[ThresholdConfig]:
        """Get threshold config for a game element."""
        return self._configs.get(game_id, {}).get(element_type)

    def get_for_template(self, template_path: str) -> Optional[ThresholdConfig]:
        """Find config by template path across all games."""
        for game_configs in self._configs.values():
            for config in game_configs.values():
                if config.template_path == template_path:
                    return config
        return None

    def list_games(self) -> list[str]:
        """List all registered game IDs."""
        return list(self._configs.keys())

    def list_elements(self, game_id: str) -> list[str]:
        """List all element types for a game."""
        return list(self._configs.get(game_id, {}).keys())

    def remove(self, game_id: str, element_type: str) -> bool:
        """Remove a config entry."""
        if game_id in self._configs and element_type in self._configs[game_id]:
            del self._configs[game_id][element_type]
            return True
        return False

    def clear(self) -> None:
        """Clear all configs."""
        self._configs.clear()

    def load_from_yaml(self, yaml_path: Path) -> None:
        """
        Load configs from a YAML file.

        Args:
            yaml_path: Path to YAML file with threshold configs.
        """
        if not yaml_path.exists():
            logger.warning(f"YAML file not found: {yaml_path}")
            return

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        if not data:
            return

        for game_id, elements in data.items():
            if not isinstance(elements, dict):
                continue
            for element_type, cfg in elements.items():
                if not isinstance(cfg, dict):
                    continue
                method_str = cfg.get("matching_method", "tm_sqdiff")
                method = self._method_from_string(method_str)
                scale = cfg.get("scale_range", [0.8, 1.2])
                if isinstance(scale, list) and len(scale) == 2:
                    scale = tuple(scale)  # type: ignore

                config = ThresholdConfig(
                    element_type=str(element_type),
                    template_path=cfg.get("template_path", ""),
                    default_threshold=cfg.get("default_threshold", 0.8),
                    calibrated_threshold=cfg.get("calibrated_threshold"),
                    matching_method=method,
                    scale_range=scale,  # type: ignore
                    use_grayscale=cfg.get("use_grayscale", True),
                    preprocessed=cfg.get("preprocessed", True),
                    description=cfg.get("description", ""),
                )
                self.register(str(game_id), str(element_type), config)

    def save_to_yaml(self, yaml_path: Path) -> None:
        """
        Save configs to a YAML file.

        Args:
            yaml_path: Path to output YAML file.
        """
        data: dict = {}

        for game_id, elements in sorted(self._configs.items()):
            game_data: dict = {}
            for element_type, config in sorted(elements.items()):
                game_data[str(element_type)] = {
                    "template_path": config.template_path,
                    "default_threshold": config.default_threshold,
                    "calibrated_threshold": config.calibrated_threshold,
                    "matching_method": config.matching_method.value,
                    "scale_range": list(config.scale_range),
                    "use_grayscale": config.use_grayscale,
                    "preprocessed": config.preprocessed,
                    "description": config.description,
                }
            data[str(game_id)] = game_data

        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    @staticmethod
    def _method_from_string(s: str) -> MatchingMethod:
        """Convert string to MatchingMethod enum."""
        mapping = {
            "tm_sqdiff": MatchingMethod.TEMPLATE_SQDIFF,
            "tmccoef": MatchingMethod.TEMPLATE_CCOEFF,
            "tmccorr": MatchingMethod.TEMPLATE_CCORR,
            "feature_orb": MatchingMethod.FEATURE_ORB,
            "feature_akaze": MatchingMethod.FEATURE_AKAZE,
        }
        return mapping.get(s, MatchingMethod.TEMPLATE_SQDIFF)
