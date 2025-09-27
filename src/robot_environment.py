from openpi_client.runtime.environment import Environment
from utils.robot_wrapper import RobotWrapper
from utils.video_handler import VideoHandler


class RobotEnvironment(Environment):
    def __init__(self, prompt: str, robot: RobotWrapper, cameras: dict[str, int]):
        self.robot = robot
        self._video_handlers = {name: VideoHandler(index) for name, index in cameras.items()}
        self._start_position = robot.get_joint_observation()
        self._prompt = prompt

    @property
    def prompt(self):
        return self._prompt

    def reset(self) -> None:
        # TODO
        pass

    def is_episode_complete(self) -> bool:
        # TODO: Implement logic for concluding episode
        return False

    def get_observation(self) -> dict:
        return {
            "prompt": self.prompt,
            "observation/gripper_position": self.robot.get_gripper_observation(),
            "observation/joint_position": self.robot.get_joint_observation(),
            **{f"observation/{name}": handler.capture_frame() for name, handler in self._video_handlers.items()},
        }

    def apply_action(self, action: dict) -> None:
        # TODO: Send action to robot
        print("Received action:", action)