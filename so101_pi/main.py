from draccus import parse
from openpi_client.runtime.agents.policy_agent import PolicyAgent
from openpi_client.runtime.runtime import Runtime
from openpi_client.websocket_client_policy import WebsocketClientPolicy
from utils.configurations import EnvironmentConfiguration
from utils.logging_subscriber import LoggingSubscriber
from utils.robot_wrapper import RobotWrapper
from robot_environment import RobotEnvironment

def main(config: EnvironmentConfiguration):
    robot = RobotWrapper(config.robot)
    robot.connect()

    environment = RobotEnvironment(config.prompt, robot, config.cameras)
    policy = WebsocketClientPolicy(host=config.server_ip, port=config.server_port)
    agent = PolicyAgent(policy)
    runtime = Runtime(environment, agent, [LoggingSubscriber(config.log_level)])

    try:
        runtime.run()
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main(parse(EnvironmentConfiguration))