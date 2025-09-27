from logging import Logger
from openpi_client.runtime.subscriber import Subscriber


class LoggingSubscriber(Subscriber):
    def __init__(self, logger: Logger):
        self.logger = logger

    def on_episode_start(self) -> None:
        self.logger.info("Episode started")

    def on_step(self, observation: dict, action: dict) -> None:
        self.logger.debug(f"Observation: {observation}")
        self.logger.debug(f"Action: {action}")

    def on_episode_end(self) -> None:
        self.logger.info("Episode ended")