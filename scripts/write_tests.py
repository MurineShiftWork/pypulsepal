from pypulsepal import PulsePal
from pypulsepal.definitions import CHANNEL_PARAM_TEST, TRIGGER_PARAM_TEST
from pypulsepal.models import ChannelConfig, TriggerConfig


def write_test_settings_for_manual_check(serial_port=None):
    pp = PulsePal(serial_port=serial_port)

    channel_fields = ChannelConfig.model_fields
    channel_kwargs = {
        k: v for k, v in CHANNEL_PARAM_TEST.items() if k in channel_fields
    }
    for channel in range(pp.nr_output_channels):
        pp.channel_configs[channel] = ChannelConfig(**channel_kwargs)

    for channel in range(pp.nr_trigger_channels):
        pp.trigger_configs[channel] = TriggerConfig(
            triggerMode=TRIGGER_PARAM_TEST["triggerMode"]
        )

    print("ENTER test write")
    pp.upload_all()
    print("EXIT test write")


def write_default_settings(serial_port=None):
    print("ENTER default write")
    PulsePal(serial_port=serial_port).upload_all()
    print("EXIT default write")
