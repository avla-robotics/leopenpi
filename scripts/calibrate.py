#!/usr/bin/env python3
"""
Joint Limits Calibration Script

This script allows users to calibrate joint limits by using teleoperation
to move the robot through its full range of motion and recording the
min/max positions for each joint.

Usage:
    python calibrate.py --robot.port /dev/ttyUSB0 --teleop.port /dev/ttyUSB1
    python calibrate.py --config config.yaml  # Uses ports from config file
    calibrate --config config.yaml  # If installed as package

The script will:
1. Start teleoperation
2. Track joint positions during teleoperation
3. Update min/max limits as joints move beyond current limits
4. Save updated configuration or print results to console
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

sys.path.append(str(Path(__file__).parent.parent))
from src import EnvironmentConfiguration

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class JointLimitsCalibrator:
    """
    Interactive joint limits calibration tool.

    Tracks joint positions during teleoperation and updates min/max limits.
    """

    def __init__(self, config: EnvironmentConfiguration):
        self.config = config

        # Reset limits
        for joint in config.robot.joints:
            joint.min_limit = 0
            joint.max_limit = 0
        self.config.robot.gripper.min_limit = 0
        self.config.robot.gripper.max_limit = 0

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
        """Run teleoperation loop and track joint positions."""
        try:
            # Create robot configuration
            robot_config = SO101FollowerConfig(
                port=self.robot_port,
                id='follower'
            )

            # Create teleoperator configuration
            teleop_config = SO101LeaderConfig(
                port=self.teleop_port,
                id='leader'
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

                    # Store observation and update limits
                    with self.observation_lock:
                        self.current_observation = observation
                        self._update_limits(observation)

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

    def _update_limits(self, observation: dict):
        """Update joint limits based on current observation."""
        for joint_config in self.config.robot.all_joints:
            joint_key = f"{joint_config.name}.pos"
            if joint_key in observation:
                current_pos = observation[joint_key]
                joint_config.min_limit = min(joint_config.min_limit, current_pos)
                joint_config.max_limit = max(joint_config.max_limit, current_pos)

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
        """Get current joint positions and limits as a formatted string."""
        with self.observation_lock:
            if self.current_observation is None:
                return "No observation data available"

            status_lines = ["Current Joint Positions and Limits:", "-" * 50]

            # Collect status
            for joint in self.config.robot.all_joints:
                key = f"{joint.name}.pos"

                if key in self.current_observation:
                    current_pos = self.current_observation[key]
                    status_lines.append(
                        f"{joint.name:15}: {current_pos:8.4f} "
                        f"(limits: {joint.min_limit:8.4f} to {joint.max_limit:8.4f})"
                    )
            return "\n".join(status_lines)

    def run_calibration(self):
        """Run the calibration process."""
        print("=" * 60)
        print("JOINT LIMITS CALIBRATION")
        print("=" * 60)
        input("Press ENTER to start teleoperation...")

        logger.info("Starting teleoperation...")

        self.teleop_running = True
        self.teleop_thread = threading.Thread(target=self._teleoperation_loop, daemon=True)
        self.teleop_thread.start()


        if not self.teleop_running:
            raise RuntimeError("Failed to start teleoperation")

        logger.info("Teleoperation started successfully")

        try:
            print("Press ENTER to stop calibration...")
            while True:
                try:
                    print("\r" + " " * 80 + "\r", end="")  # Clear line
                    print(self.get_current_status())
                    print("\nPress ENTER to stop calibration...")
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
        print("CALIBRATION COMPLETE!")
        print("=" * 60)

    def _config_to_dict(self, obj):
        """Recursively convert configuration objects to dictionaries."""
        if hasattr(obj, '__dict__'):
            result = {}
            for key, value in obj.__dict__.items():
                if key == 'logger':  # Skip logger objects
                    continue
                result[key] = self._config_to_dict(value)
            return result
        elif isinstance(obj, list):
            return [self._config_to_dict(item) for item in obj]
        else:
            return obj

    def save_config(self, path: str):
        # Convert config to dict for serialization
        config_dict = self._config_to_dict(self.config)

        # Reorder keys to put 'robot' last
        if 'robot' in config_dict:
            ordered_dict = {k: v for k, v in sorted(config_dict.items()) if k != 'robot'}
            ordered_dict['robot'] = config_dict['robot']

            # This should be computed on the fly
            del ordered_dict['robot']['all_joints']

            config_dict = ordered_dict

        with open(path, 'w') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            elif path.endswith('.json'):
                json.dump(config_dict, f, indent=2)
            else:
                raise ValueError("Config file must be either YAML or JSON.")
            print(f"Updated configuration saved to: {path}")


    def print_config_formats(self):
        """Print the updated configuration in both JSON and YAML formats."""
        print("\n" + "=" * 60)
        print("UPDATED CONFIGURATION")
        print("=" * 60)

        # Print JSON format
        print("\nJSON Format:")
        print("-" * 20)
        print(json.dumps(self.config, indent=2))

        print("\n")

        # Print YAML format
        print("YAML Format:")
        print("-" * 20)
        print(yaml.dump(self.config, default_flow_style=False, sort_keys=False))

    def cleanup(self):
        """Clean up resources."""
        self.stop_teleoperation()


def main():
    config = parse(EnvironmentConfiguration)
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config_path")
    args = argparser.parse_args()

    try:
        calibrator = JointLimitsCalibrator(config)
        calibrator.run_calibration()

        if args.config_path:
            calibrator.save_config(args.config_path)
        else:
            calibrator.print_config_formats()

        print("\nCalibration completed successfully!")

    except KeyboardInterrupt:
        print("\nCalibration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()