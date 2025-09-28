from typing import Dict

import numpy as np
from lerobot.robots.so101_follower import SO101FollowerConfig
from typing_extensions import override
from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig
from lerobot.teleoperators import make_teleoperator_from_config
from lerobot.robots import make_robot_from_config
from . import RobotConfiguration
from openpi_client import base_policy as _base_policy


class TeleopPolicy(_base_policy.BasePolicy):
    """Policy that controls the robot directly via teleoperation.

    This policy creates a teleoperator device and uses it to generate actions
    for the robot, bypassing the need for a remote policy server.
    """

    def __init__(self, teleop_port: str, robot: RobotConfiguration):
        teleop_config = SO101LeaderConfig(
            port=teleop_port,
            id='leader'
        )
        robot_config = SO101FollowerConfig(
            port=robot.port,
            id='follower'
        )
        self.teleop = make_teleoperator_from_config(teleop_config)
        self.robot = make_robot_from_config(robot_config)
        self.robot_config = robot
        self.teleop.connect()
        self.robot.connect()

    @override
    def infer(self, obs: Dict) -> Dict:
        """Get action from the teleoperator device."""
        telop_pos = self.teleop.get_action()
        robot_pos = self.robot.get_observation()
        delta = np.zeros(shape=(8,), dtype=np.float32)
        for i, joint in enumerate(self.robot_config.all_joints):
            joint_name = f"{joint.name}.pos"
            diff = telop_pos[joint_name] - robot_pos[joint_name]
            joint_range = joint.max_limit - joint.min_limit
            delta[i] = diff / joint_range

        return {
            "actions": delta
        }

    @override
    def reset(self) -> None:
        """Reset policy state."""
        # TODO
        pass


    def __del__(self):
        """Ensure cleanup happens when object is garbage collected."""
        self.teleop.disconnect()
