import json
from unittest.mock import patch

import pytest

from pypulsepal.config_io import load_config, save_config
from pypulsepal.models import ChannelConfig, PulsePalConfig, TriggerConfig

yaml = pytest.importorskip("yaml", reason="pyyaml not installed")


class TestSaveLoadJSON:
    def test_round_trip_defaults(self, tmp_path):
        path = tmp_path / "cfg.json"
        cfg = PulsePalConfig()
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded == cfg

    def test_round_trip_custom_voltage(self, tmp_path):
        path = tmp_path / "cfg.json"
        cfg = PulsePalConfig(
            channels=[ChannelConfig(phase1Voltage=3.5)] + [ChannelConfig()] * 3
        )
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded.channels[0].phase1Voltage == 3.5

    def test_round_trip_trigger_mode(self, tmp_path):
        path = tmp_path / "cfg.json"
        cfg = PulsePalConfig(triggers=[TriggerConfig(triggerMode=2), TriggerConfig()])
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded.triggers[0].triggerMode == 2

    def test_json_is_valid(self, tmp_path):
        path = tmp_path / "cfg.json"
        save_config(PulsePalConfig(), path)
        data = json.loads(path.read_text())
        assert "channels" in data
        assert "triggers" in data
        assert len(data["channels"]) == 4

    def test_json_indented(self, tmp_path):
        path = tmp_path / "cfg.json"
        save_config(PulsePalConfig(), path)
        text = path.read_text()
        assert "\n" in text

    def test_load_partial_channel_uses_defaults(self, tmp_path):
        path = tmp_path / "cfg.json"
        path.write_text(
            json.dumps(
                {"channels": [{"phase1Voltage": 2.0}] + [{}] * 3, "triggers": [{}, {}]}
            )
        )
        loaded = load_config(path)
        assert loaded.channels[0].phase1Voltage == 2.0
        assert loaded.channels[1].phase1Voltage == ChannelConfig().phase1Voltage


class TestSaveLoadYAML:
    def test_round_trip_defaults(self, tmp_path):
        path = tmp_path / "cfg.yaml"
        cfg = PulsePalConfig()
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded == cfg

    def test_round_trip_yml_suffix(self, tmp_path):
        path = tmp_path / "cfg.yml"
        cfg = PulsePalConfig(
            channels=[ChannelConfig(phase1Voltage=1.0)] + [ChannelConfig()] * 3
        )
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded.channels[0].phase1Voltage == 1.0

    def test_round_trip_custom_duration(self, tmp_path):
        path = tmp_path / "cfg.yaml"
        cfg = PulsePalConfig(
            channels=[ChannelConfig(phase1Duration=0.005)] + [ChannelConfig()] * 3
        )
        save_config(cfg, path)
        loaded = load_config(path)
        assert abs(loaded.channels[0].phase1Duration - 0.005) < 1e-9

    def test_yaml_is_readable(self, tmp_path):
        path = tmp_path / "cfg.yaml"
        save_config(PulsePalConfig(), path)
        data = yaml.safe_load(path.read_text())
        assert "channels" in data
        assert len(data["channels"]) == 4


class TestMissingYaml:
    def test_save_raises_without_pyyaml(self, tmp_path):
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("mocked missing")
            return real_import(name, *args, **kwargs)

        path = tmp_path / "cfg.yaml"
        with (
            patch("builtins.__import__", side_effect=mock_import),
            pytest.raises(ImportError, match="pyyaml"),
        ):
            save_config(PulsePalConfig(), path)

    def test_load_raises_without_pyyaml(self, tmp_path):
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("mocked missing")
            return real_import(name, *args, **kwargs)

        path = tmp_path / "cfg.yaml"
        path.write_text("channels: []\ntriggers: []\n")
        with (
            patch("builtins.__import__", side_effect=mock_import),
            pytest.raises(ImportError, match="pyyaml"),
        ):
            load_config(path)


class TestPulsePalConfigMethods:
    def test_save_config_writes_file(self, tmp_path):
        from tests.test_pulsepal import _make_pp

        pp, _ = _make_pp()
        path = tmp_path / "cfg.json"
        pp.save_config(path)
        assert path.exists()

    def test_load_config_applies_to_instance(self, tmp_path):
        from tests.test_pulsepal import _make_pp

        pp, _ = _make_pp()
        path = tmp_path / "cfg.json"
        cfg = PulsePalConfig(
            channels=[ChannelConfig(phase1Voltage=4.0)] + [ChannelConfig()] * 3
        )
        save_config(cfg, path)
        pp.load_config(path)
        assert pp.channel_configs[0].phase1Voltage == 4.0

    def test_save_load_round_trip_via_instance(self, tmp_path):
        from tests.test_pulsepal import _make_pp

        pp1, _ = _make_pp()
        pp1.channel_configs[0].phase1Voltage = 2.2
        path = tmp_path / "cfg.json"
        pp1.save_config(path)

        pp2, _ = _make_pp()
        pp2.load_config(path)
        assert pp2.channel_configs[0].phase1Voltage == pytest.approx(2.2)
