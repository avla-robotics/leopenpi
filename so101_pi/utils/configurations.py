from dataclasses import dataclass
from logging import Logger


@dataclass(frozen=True)
class Joint:
    name: str
    min_limit: float
    max_limit: float


@dataclass(frozen=True)
class RobotConfiguration:
    port: str
    joints: list[Joint] = None

    def __post_init__(self):
        if self.joints is None:
            # Default joints for SO-101 robot with 6 motors in order
            # Motor names match LeRobot SO101Follower configuration
            object.__setattr__(self, 'joints', [
                Joint('shoulder_pan', -1.0, 1.0),
                Joint('shoulder_lift', -1.0, 1.0),
                Joint('elbow_flex', -1.0, 1.0),
                Joint('wrist_flex', -1.0, 1.0),
                Joint('wrist_roll', -1.0, 1.0),
                Joint('gripper', 0.0, 1.0),  # Gripper ranges from 0 (open) to 1 (closed)
            ])

@dataclass(frozen=True)
class EnvironmentConfiguration:
    prompt: str
    cameras: dict[str, int]
    robot: RobotConfiguration
    server_ip: str
    server_port: int = 8000
    max_steps: int = 1000
    log_level: str = "INFO"
    logger: Logger = None

    def __post_init__(self):
        if self.logger is None:
            object.__setattr__(self, 'logger', Logger(__name__, self.log_level))
