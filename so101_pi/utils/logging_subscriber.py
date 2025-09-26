import logging
from openpi_client.runtime.subscriber import Subscriber


class LoggingSubscriber(Subscriber):
    def __init__(self, log_level: str = "INFO"):
        logging.basicConfig(level=log_level.upper())
        self.logger = logging.getLogger(__name__)

    def on_episode_start(self) -> None:
        self.logger.info("Episode started")

    def on_step(self, observation: dict, action: dict) -> None:
        self.logger.debug(f"Observation: {observation}")
        self.logger.debug(f"Action: {action}")

    def on_episode_end(self) -> None:
        self.logger.info("Episode ended")