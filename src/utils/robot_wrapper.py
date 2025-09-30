import numpy as np
import logging
from .configurations import RobotConfiguration, Joint
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


    def _get_observation(self, joints: list[Joint]):
        """Get the current joint observation from the robot."""
        if not self.is_connected:
            raise RuntimeError("Robot not connected")

        obs = self.robot.get_observation()
        processed_obs = np.zeros(shape=(len(joints),), dtype=np.float32)
        # Capture order from config
        for i, joint in enumerate(joints):
            joint_name = f"{joint.name}.pos"
            if joint_name not in obs:
                raise ValueError(f"Could not find {joint_name} in robot observation from config value `{joint}`")
            processed_obs[i] = obs[joint_name]
        return processed_obs

    def get_joint_observation(self) -> np.ndarray:
        """Get the current joint observation from the robot."""
        return self._get_observation(self.config.joints)

    def get_gripper_observation(self) -> np.ndarray:
        """Get the current gripper observation from the robot."""
        return self._get_observation([self.config.gripper])

    def apply_action(self, action: np.ndarray) -> None:
        """Execute an action from the environment.

        Args:
            action: A numpy array of shape (6,) with values in range [-1, 1]
                   representing the delta movement for each of the 6 motors.
                   Each value represents how much to move from current position.
        """
        if not isinstance(action, np.ndarray):
            raise ValueError("Action must be a numpy array")

        if action.shape != (6,):
            raise ValueError(f"Action must have shape (6,), got {action.shape}")

        if not self.is_connected:
            self.logger.warning("Robot not connected, skipping action")
            return

        current_positions = self._get_observation(self.config.all_joints)

        goal_positions = {}
        for i, joint in enumerate(self.config.all_joints):
            current_pos = current_positions[i]
            action_val = action[i]

            total_range = joint.max_limit - joint.min_limit
            delta_movement = action_val * total_range * 0.25
            new_position = current_pos + delta_movement
            clipped_value = np.clip(new_position, joint.min_limit, joint.max_limit)

            if clipped_value != new_position:
                print(
                    f"Clipping on {joint.name}: "
                    f"requested={new_position:.4f}, "
                    f"clipped={clipped_value:.4f}, "
                    f"min={joint.min_limit:.4f}, "
                    f"max={joint.max_limit:.4f}"
                )
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