from draccus import parse

from openpi_client.action_chunk_broker import ActionChunkBroker
from openpi_client.runtime.agents.policy_agent import PolicyAgent
from openpi_client.runtime.runtime import Runtime
from openpi_client.websocket_client_policy import WebsocketClientPolicy
from leopenpi.mocks import TeleopPolicy
from leopenpi.utils import EnvironmentConfiguration, LoggingSubscriber, RobotWrapper
from leopenpi.robot_environment import RobotEnvironment

def main(config: EnvironmentConfiguration):
    robot = RobotWrapper(config.robot, config.logger)
    robot.connect()

    if config.start_home:
        home_action = {}
        for joint in config.robot.joints:
            if joint.home is not None:
                home_action[f'{joint.name}.pos'] = joint.home
            else:
                break
        else:
            # Only send the action if all joints have a home
            robot.robot.send_action(home_action)

    environment = RobotEnvironment(config.prompt, robot, config.cameras)
    if config.policy_type == "openpi":
        if config.server_ip == None:
            raise Exception("IP address is required for openpi. Set `server_ip: x.x.x.x` in your config file.")
        policy = WebsocketClientPolicy(host=config.server_ip, port=config.server_port)
        policy = ActionChunkBroker(policy, action_horizon=10)
    elif config.policy_type == "teleop":
        policy = TeleopPolicy(config.teleop, config.robot)
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