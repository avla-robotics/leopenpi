import numpy as np
import logging
from .configurations import RobotConfiguration
from lerobot.robots.so101_follower import SO101Follower
from lerobot.robots.so101_follower.config_so101_follower import SO101FollowerConfig

class RobotWrapper:
    def __init__(self, config: RobotConfiguration, logger: logging.Logger = logging.Logger(__name__)):
        self.config = config
        self.logger = logger
        robot_config = SO101FollowerConfig(port=self.config.port)

        self.robot = SO101Follower(robot_config)
        self.is_connected = False

    def connect(self, calibrate: bool = True) -> None:
        """Connect to the robot hardware."""
        if self.is_connected:
            self.logger.warning("Robot already connected")
            return

        self.robot.connect(calibrate=calibrate)
        self.is_connected = True
        self.logger.info("Successfully connected to SO101 robot")

    def get_joint_observation(self) -> np.ndarray:
        """Get the current joint observation from the robot."""
        if not self.is_connected:
            raise RuntimeError("Robot not connected")

        obs = self.robot.get_observation()
        processed_obs = np.zeros(shape=(6,), dtype=np.float32)
        # Capture order from config
        for i, joint in enumerate(self.config.joints):
            joint_name = f"{joint.name}.pos"
            if joint_name not in obs:
                raise ValueError(f"Could not find {joint_name} in robot observation from config value `{joint}`")
            processed_obs[i] = obs[joint_name]

        return processed_obs

    def get_gripper_observation(self) -> np.ndarray:
        """Get the current gripper observation from the robot."""
        if not self.is_connected:
            raise RuntimeError("Robot not connected")

        obs = self.robot.get_observation()
        gripper_name = f"{self.config.gripper.name}.pos"
        if gripper_name not in obs:
            raise ValueError(f"Could not find {gripper_name} in robot observation from config value `{self.config.gripper.name}`")

        return np.array(obs[gripper_name], dtype=np.float32)

    def apply_action(self, action: np.ndarray) -> None:
        """Execute an action from the environment.

        Args:
            action: A numpy array of shape (6,) with values in range [-1, 1]
                   representing the desired position for each of the 6 motors.
        """
        if not isinstance(action, np.ndarray):
            raise ValueError("Action must be a numpy array")

        if action.shape != (6,):
            raise ValueError(f"Action must have shape (6,), got {action.shape}")

        if not self.is_connected:
            self.logger.warning("Robot not connected, skipping action")
            return

        # Convert action array to motor position dictionary
        goal_positions = {}

        for i, joint in enumerate(self.config.joints):
            motor_value = action[i]
            clipped_value = np.clip(motor_value, joint.min_limit, joint.max_limit)
            goal_positions[f"{joint.name}.pos"] = float(clipped_value)

        try:
            self.robot.send_action(goal_positions)
            self.logger.debug(f"Sent action: {goal_positions}")
        except Exception as e:
            self.logger.error(f"Failed to send motor commands: {e}")

    def disconnect(self) -> None:
        """Disconnect from the robot hardware."""
        if self.is_connected:
            self.robot.disconnect()
            self.is_connected = False
            self.logger.info("Disconnected from robot hardware")
        else:
            self.logger.warning("Attempted to disconnect when no robot was connected")