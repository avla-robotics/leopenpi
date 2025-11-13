from dataclasses import dataclass
from logging import Logger


@dataclass
class Joint:
    name: str
    min_limit: float
    max_limit: float
    home: float | None = None

@dataclass
class Camera:
    name: str
    index: int
    flipped: bool = False
    minX: int = None
    maxX: int = None
    minY: int = None
    maxY: int = None


@dataclass
class RobotConfiguration:
    port: str
    id: str = 'follower'
    joints: list[Joint] = None
    gripper: Joint = None
    all_joints: list[Joint] = None

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
            ])
        if self.gripper is None:
            object.__setattr__(self, 'gripper', Joint('gripper', -1.0, 1.0))
        self.all_joints = self.joints + [self.gripper]

@dataclass(frozen=True)
class TeleopConfiguration:
    port: str
    id: str = 'leader'

@dataclass
class EnvironmentConfiguration:
    prompt: str
    cameras: list[Camera]
    robot: RobotConfiguration
    teleop: TeleopConfiguration
    server_ip: str | None = None
    start_home: bool = False
    policy_type: str = "openpi"
    server_port: int = 8000
    max_steps: int = 1000
    log_level: str = "INFO"
    logger: Logger = None

    def __post_init__(self):
        if self.logger is None:
            object.__setattr__(self, 'logger', Logger(__name__, self.log_level))
