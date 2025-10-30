import numpy as np

from openpi_client.runtime.environment import Environment
from src import Camera

# HACK: Make inputs work within package, and script. This should be refactored later.
try:
    from utils.robot_wrapper import RobotWrapper
    from utils.video_handler import VideoHandler
except ImportError:
    from src.utils.robot_wrapper import RobotWrapper
    from src.utils.video_handler import VideoHandler


class RobotEnvironment(Environment):
    def __init__(self, prompt: str, robot: RobotWrapper, cameras: list[Camera]):
        self.robot = robot
        self._video_handlers = {camera.name: VideoHandler(camera_index=camera.index, flipped=camera.flipped) for camera in cameras}
        self._prompt = prompt

    @property
    def prompt(self):
        return self._prompt

    def reset(self) -> None:
        return

    def is_episode_complete(self) -> bool:
        # TODO: Implement logic for concluding episode
        return False

    def get_observation(self) -> dict:
        return {
            "prompt": self.prompt,
            "observation/gripper_position": self.robot.get_gripper_observation(),
            "observation/state": self._pad(self.robot.get_joint_observation(), 7),
            **{f"observation/{name}": handler.capture_frame() for name, handler in self._video_handlers.items()},
        }

    def apply_action(self, action: dict) -> None:
        act = self._trim(action["actions"]) * -1
        self.robot.apply_action(act)

    @staticmethod
    def _pad(observation: np.ndarray, size: int) -> np.ndarray:
        if observation.size >= size:
            return observation[:size]
        padded = np.zeros(size)
        padded[:observation.size] = observation.flatten()
        return padded

    @staticmethod
    def _trim(observation: np.ndarray) -> np.ndarray:
        return observation[:-1]