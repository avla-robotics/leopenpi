from openpi_client.runtime.environment import Environment
from so101_pi import Camera
from so101_pi.utils.robot_wrapper import RobotWrapper
from so101_pi.utils.video_handler import VideoHandler


class RobotEnvironment(Environment):
    def __init__(self, prompt: str, robot: RobotWrapper, cameras: list[Camera]):
        self.robot = robot
        self._video_handlers = {camera.name: VideoHandler(camera=camera) for camera in cameras}
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
            "observation/state": self.robot.get_joint_observation(),
            **{f"observation/{name}": handler.capture_frame() for name, handler in self._video_handlers.items()},
        }

    def apply_action(self, action: dict) -> None:
        # Larger gripper motions. You can tune this.
        act = action["actions"] * [1, 1, 1, 1, 1, 3]
        self.robot.apply_action(act)
