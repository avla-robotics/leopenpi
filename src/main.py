from draccus import parse

from openpi_client.action_chunk_broker import ActionChunkBroker
from openpi_client.runtime.agents.policy_agent import PolicyAgent
from openpi_client.runtime.runtime import Runtime
from openpi_client.websocket_client_policy import WebsocketClientPolicy
from utils import TeleopPolicy
from utils import EnvironmentConfiguration, LoggingSubscriber, RobotWrapper
from robot_environment import RobotEnvironment

def main(config: EnvironmentConfiguration):
    robot = RobotWrapper(config.robot, config.logger)
    robot.connect()

    environment = RobotEnvironment(config.prompt, robot, config.cameras)
    if config.policy_type == "openpi":
        policy = WebsocketClientPolicy(host=config.server_ip, port=config.server_port)
        policy = ActionChunkBroker(policy, action_horizon=10)
    elif config.policy_type == "teleop":
        policy = TeleopPolicy(config.teleop.port, config.robot)
    else:
        raise Exception("Unrecognized policy type: ", config.policy_type)

    agent = PolicyAgent(policy)
    runtime = Runtime(environment, agent, [LoggingSubscriber(config.logger)])

    try:
        runtime.run()
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main(parse(EnvironmentConfiguration))