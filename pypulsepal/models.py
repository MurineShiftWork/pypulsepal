from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Voltage = Annotated[float, Field(ge=-10.0, le=10.0)]
Duration = Annotated[float, Field(ge=0.0)]
Flag = Annotated[int, Field(ge=0, le=1)]
TriggerModeValue = Annotated[int, Field(ge=0, le=2)]


class ChannelConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    isBiphasic: bool = False
    phase1Voltage: Voltage = 5.0
    phase2Voltage: Voltage = -5.0
    restingVoltage: Voltage = 0.0
    phase1Duration: Duration = 0.001
    interPhaseInterval: Duration = 0.001
    phase2Duration: Duration = 0.001
    interPulseInterval: Duration = 0.01
    burstDuration: Duration = 0.0
    interBurstInterval: Duration = 0.0
    pulseTrainDuration: Duration = 1.0
    pulseTrainDelay: Duration = 0.0
    linkTriggerChannel1: Flag = 1
    linkTriggerChannel2: Flag = 0
    customTrainID: Flag = 0
    customTrainTarget: Flag = 0
    customTrainLoop: Flag = 0


class TriggerConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    triggerMode: TriggerModeValue = 0


class PulsePalConfig(BaseModel):
    channels: list[ChannelConfig] = Field(
        default_factory=lambda: [ChannelConfig() for _ in range(4)]
    )
    triggers: list[TriggerConfig] = Field(
        default_factory=lambda: [TriggerConfig() for _ in range(2)]
    )
