from draccus import parse
from lerobot_wrapper import RobotWrapper
from openpi_client.runtime.agents.policy_agent import PolicyAgent
from openpi_client.runtime.runtime import Runtime
from openpi_client.websocket_client_policy import WebsocketClientPolicy
from so101_pi.utils.environment_configuration import EnvironmentConfiguration
from so101_pi.robot_environment import RobotEnvironment
from so101_pi.utils.logging_subscriber import LoggingSubscriber

def main(config: EnvironmentConfiguration):
    robot = RobotWrapper(config.robot_port)
    environment = RobotEnvironment(config.prompt, robot, config.cameras)
    policy = WebsocketClientPolicy(host=config.server_ip, port=config.server_port)
    agent = PolicyAgent(policy)
    runtime = Runtime(environment, agent, [LoggingSubscriber(config.log_level)])
    runtime.run()



if __name__ == "__main__":
    config = parse(EnvironmentConfiguration)
    main(config)