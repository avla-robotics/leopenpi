import numpy as np
from openpi_client.runtime.environment import Environment
from lerobot_wrapper import RobotWrapper
from so101_pi.utils.video_handler import VideoHandler


class RobotEnvironment(Environment):
    def __init__(self, prompt: str, robot: RobotWrapper, cameras: dict[str, int]):
        self.robot = robot
        self._video_handlers = {name: VideoHandler(index) for name, index in cameras.items()}
        self._start_position = robot.position
        self._prompt = prompt

    @property
    def prompt(self):
        return self._prompt

    def reset(self) -> None:
        self.robot.set_goal_position(self._start_position)

    def is_episode_complete(self) -> bool:
        # TODO: Implement logic for concluding episode
        return False

    def get_observation(self) -> dict:
        return {
            "prompt": self.prompt,
            "observation/gripper_position": np.array([self.robot.position]).astype(np.float32),
            "observation/joint_position": np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.0, 0.0]).astype(np.float32), # TODO: Get real data
            **{f"observation/{name}": handler.capture_frame() for name, handler in self._video_handlers.items()},
        }

    def apply_action(self, action: dict) -> None:
        pass # TODO: Send action to robot