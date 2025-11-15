#!/usr/bin/env python3
"""Script to set home positions for the robot via teleoperation.

This script allows you to:
1. Connect to the robot and teleop device
2. Move the robot to desired home position using teleoperation
3. Save the current position as home positions in the config file

Usage:
    python set_home.py --robot.port /dev/ttyUSB0 --teleop.port /dev/ttyUSB1
    python set_home.py --config config.yaml  # Uses ports from config file
    python set_home.py --config config.json  # Also supports JSON
    set_home --config config.yaml  # If installed as package

The script will:
1. Start teleoperation
2. Allow you to move the robot to the desired home position
3. Save the position as home when you press ENTER
"""
import argparse
import threading
import time
import signal
import select
import sys
import yaml
import json
import logging
from pathlib import Path
from draccus import parse

from lerobot.robots.so101_follower.config_so101_follower import SO101FollowerConfig
from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig
from lerobot.robots import make_robot_from_config
from lerobot.teleoperators import make_teleoperator_from_config

from leopenpi import EnvironmentConfiguration

# Keep project_root for config file resolution
project_root = Path(__file__).parent.parent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class HomePositionSetter:
    """
    Interactive home position setting tool.

    Allows users to move the robot to desired home position via teleoperation
    and save the position to the configuration file.
    """

    def __init__(self, config: EnvironmentConfiguration):
        self.config = config
        self.robot_port = config.robot.port
        self.teleop_port = config.teleop.port

        self.teleop_thread = None
        self.teleop_running = False
        self.lerobot_robot = None
        self.lerobot_teleop = None
        self.current_observation = None
        self.observation_lock = threading.Lock()

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal, cleaning up...")
        self.cleanup()
        sys.exit(0)

    def _teleoperation_loop(self):
        """Run teleoperation loop and track current positions."""
        try:
            # Create robot configuration
            robot_config = SO101FollowerConfig(
                port=self.robot_port,
                id=self.config.robot.id
            )

            # Create teleoperator configuration
            teleop_config = SO101LeaderConfig(
                port=self.teleop_port,
                id=self.config.teleop.id
            )

            logger.info("Creating robot and teleoperator...")

            # Create robot and teleoperator objects
            self.lerobot_robot = make_robot_from_config(robot_config)
            self.lerobot_teleop = make_teleoperator_from_config(teleop_config)

            # Connect to devices
            self.lerobot_teleop.connect()
            self.lerobot_robot.connect()

            logger.info("Starting teleoperation loop...")

            # Run the teleoperation loop
            while self.teleop_running:
                try:
                    # Get action from teleoperator
                    action = self.lerobot_teleop.get_action()

                    # Get current observation from robot
                    observation = self.lerobot_robot.get_observation()

                    # Store observation
                    with self.observation_lock:
                        self.current_observation = observation

                    # Send action to robot
                    self.lerobot_robot.send_action(action)

                    # Control loop timing (60 Hz)
                    time.sleep(1.0 / 60.0)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error in teleoperation loop: {e}")
                    time.sleep(0.1)

        except Exception as e:
            logger.error(f"Teleoperation thread error: {e}")
            self.teleop_running = False
        finally:
            # Cleanup connections
            if self.lerobot_teleop:
                try:
                    self.lerobot_teleop.disconnect()
                except:
                    pass
            if self.lerobot_robot:
                try:
                    self.lerobot_robot.disconnect()
                except:
                    pass

    def stop_teleoperation(self):
        """Stop the teleoperation thread."""
        if self.teleop_running:
            try:
                logger.info("Stopping teleoperation...")
                self.teleop_running = False

                # Wait for thread to finish
                if self.teleop_thread and self.teleop_thread.is_alive():
                    self.teleop_thread.join(timeout=5.0)

                logger.info("Teleoperation stopped")

            except Exception as e:
                logger.error(f"Error stopping teleoperation: {e}")

            finally:
                self.teleop_thread = None
                self.teleop_running = False

    def get_current_status(self) -> str:
        """Get current joint positions as a formatted string."""
        with self.observation_lock:
            if self.current_observation is None:
                return "No observation data available"

            status_lines = ["Current Joint Positions:", "-" * 50]

            # Collect status for all joints
            for joint in self.config.robot.all_joints:
                key = f"{joint.name}.pos"

                if key in self.current_observation:
                    current_pos = self.current_observation[key]
                    status_lines.append(
                        f"{joint.name:15}: {current_pos:8.4f}"
                    )
            return "\n".join(status_lines)

    def run_home_setting(self):
        """Run the home position setting process."""
        print("=" * 60)
        print("SET HOME POSITION")
        print("=" * 60)
        print("\nThis script will help you set home positions for your robot.")
        print("\nInstructions:")
        print("1. Press ENTER to start teleoperation")
        print("2. Use the teleop device to move robot to desired home position")
        print("3. Press ENTER when satisfied with the position")
        print("4. The current position will be saved as home in your config file")
        input("\nPress ENTER to start teleoperation...")

        logger.info("Starting teleoperation...")

        self.teleop_running = True
        self.teleop_thread = threading.Thread(target=self._teleoperation_loop, daemon=True)
        self.teleop_thread.start()

        if not self.teleop_running:
            raise RuntimeError("Failed to start teleoperation")

        logger.info("Teleoperation started successfully")

        try:
            print("\nMove robot to home position using teleop device.")
            print("Press ENTER to save the position...")
            while True:
                try:
                    print("\r" + " " * 80 + "\r", end="")  # Clear line
                    print(self.get_current_status())
                    print("\nPress ENTER to save the position...")
                    if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                        input()  # Consume the input
                        break

                    time.sleep(0.1)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    raise e

        finally:
            self.stop_teleoperation()

        print("\n" + "=" * 60)
        print("SAVING HOME POSITION")
        print("=" * 60)

    def update_config_with_home_positions(self, config_path: str):
        """Update the config file with current robot positions as home values."""
        with self.observation_lock:
            if self.current_observation is None:
                logger.error("No observation data available to save")
                return

            # Read the existing config
            config_file = Path(config_path)
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    config_data = yaml.safe_load(f)

            # Update home positions for joints
            for joint_config in config_data['robot']['joints']:
                joint_name = joint_config['name']
                joint_pos_key = f"{joint_name}.pos"
                if joint_pos_key in self.current_observation:
                    joint_config['home'] = float(self.current_observation[joint_pos_key])
                    print(f"Set {joint_name} home to: {self.current_observation[joint_pos_key]:.4f}")

            # Update home position for gripper
            gripper_name = config_data['robot']['gripper']['name']
            gripper_pos_key = f"{gripper_name}.pos"
            if gripper_pos_key in self.current_observation:
                config_data['robot']['gripper']['home'] = float(self.current_observation[gripper_pos_key])
                print(f"Set {gripper_name} home to: {self.current_observation[gripper_pos_key]:.4f}")

            # Write back to config file
            with open(config_file, 'w') as f:
                if config_file.suffix.lower() == '.json':
                    json.dump(config_data, f, indent=2)
                else:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

            print(f"\nSuccessfully updated home positions in {config_path}")

    def cleanup(self):
        """Clean up resources."""
        self.stop_teleoperation()


def main():
    config = parse(EnvironmentConfiguration)
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config_path")
    args = argparser.parse_args()

    try:
        setter = HomePositionSetter(config)
        setter.run_home_setting()

        # Determine which config file to use
        config_path = args.config_path if args.config_path else "config.yaml"

        # If path is relative, resolve it from project root
        if not Path(config_path).is_absolute():
            config_path = str(project_root / config_path)

        # Update config file with current positions
        setter.update_config_with_home_positions(config_path)

        print("\nHome position setting completed successfully!")

    except KeyboardInterrupt:
        print("\nHome position setting interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Home position setting failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
