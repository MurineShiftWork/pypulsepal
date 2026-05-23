import json
from pathlib import Path

from pypulsepal.models import PulsePalConfig

_YAML_SUFFIXES = {".yaml", ".yml"}


def _require_yaml():
    try:
        import yaml

        return yaml
    except ImportError:
        raise ImportError(
            "pyyaml is required for YAML support: pip install 'pypulsepal[yaml]'"
        )


def load_config(path: str | Path) -> PulsePalConfig:
    """Load a PulsePalConfig from a JSON or YAML file."""
    path = Path(path)
    text = path.read_text()
    if path.suffix in _YAML_SUFFIXES:
        yaml = _require_yaml()
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return PulsePalConfig.model_validate(data)


def save_config(config: PulsePalConfig, path: str | Path) -> None:
    """Save a PulsePalConfig to a JSON or YAML file."""
    path = Path(path)
    data = config.model_dump()
    if path.suffix in _YAML_SUFFIXES:
        yaml = _require_yaml()
        path.write_text(yaml.dump(data, default_flow_style=False))
    else:
        path.write_text(json.dumps(data, indent=2))
