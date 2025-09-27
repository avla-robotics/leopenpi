#!/usr/bin/env python3
"""
Joint Limits Calibration Script

This script allows users to calibrate joint limits by using teleoperation
to move the robot through its full range of motion and recording the
min/max positions for each joint.

Usage:
    python calibrate_joint_limits.py --robot-port /dev/ttyUSB0 --teleop-port /dev/ttyUSB1
    python calibrate_joint_limits.py --config config.yaml  # Uses ports from config file
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
import sys
import yaml
import json
import logging
from pathlib import Path

from lerobot.robots.so101_follower.config_so101_follower import SO101FollowerConfig
from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig
from lerobot.robots import make_robot_from_config
from lerobot.teleoperators import make_teleoperator_from_config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class JointLimitsCalibrator:
    """
    Interactive joint limits calibration tool.

    Tracks joint positions during teleoperation and updates min/max limits.
    """

    def __init__(self, robot_port: str = None, teleop_port: str = None, config_path: str = None):
        self.config_path = config_path

        # Load existing config if provided
        self.config_data = self._load_config() if config_path else self._create_default_config()

        # Get ports from config or arguments
        self.robot_port = robot_port or self.config_data.get('robot', {}).get('port')
        self.teleop_port = teleop_port or self.config_data.get('teleop', {}).get('port')

        if not self.robot_port:
            raise ValueError("Robot port must be provided via --robot-port or in config file")
        if not self.teleop_port:
            raise ValueError("Teleop port must be provided via --teleop-port or in config file")

        # Teleoperation objects and thread
        self.teleop_thread = None
        self.teleop_running = False
        self.lerobot_robot = None
        self.lerobot_teleop = None
        self.current_observation = None
        self.observation_lock = threading.Lock()

        # Track if any limits were updated
        self.limits_updated = False

        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    return yaml.safe_load(f)
                elif self.config_path.endswith('.json'):
                    return json.load(f)
                else:
                    raise ValueError("Config file must be .yaml, .yml, or .json")
        except Exception as e:
            logger.error(f"Failed to load config file {self.config_path}: {e}")
            sys.exit(1)

    def _create_default_config(self) -> dict:
        """Create default configuration structure."""
        return {
            'robot': {
                'joints': [
                    {'name': 'shoulder_pan', 'min_limit': -1.0, 'max_limit': 1.0},
                    {'name': 'shoulder_lift', 'min_limit': -1.0, 'max_limit': 1.0},
                    {'name': 'elbow_flex', 'min_limit': -1.0, 'max_limit': 1.0},
                    {'name': 'wrist_flex', 'min_limit': -1.0, 'max_limit': 1.0},
                    {'name': 'wrist_roll', 'min_limit': -1.0, 'max_limit': 1.0},
                ],
                'gripper': {
                    'name': 'gripper',
                    'min_limit': -1.0,
                    'max_limit': 1.0
                }
            }
        }

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
        # Update joint limits
        for joint_config in self.config_data['robot']['joints']:
            joint_name = joint_config['name']
            joint_key = f"{joint_name}.pos"

            if joint_key in observation:
                current_pos = observation[joint_key]

                # Update min limit
                if current_pos < joint_config['min_limit']:
                    joint_config['min_limit'] = current_pos
                    self.limits_updated = True

                # Update max limit
                if current_pos > joint_config['max_limit']:
                    joint_config['max_limit'] = current_pos
                    self.limits_updated = True

        # Update gripper limits
        gripper_config = self.config_data['robot']['gripper']
        gripper_name = gripper_config['name']
        gripper_key = f"{gripper_name}.pos"

        if gripper_key in observation:
            current_pos = observation[gripper_key]

            # Update min limit
            if current_pos < gripper_config['min_limit']:
                gripper_config['min_limit'] = current_pos
                self.limits_updated = True

            # Update max limit
            if current_pos > gripper_config['max_limit']:
                gripper_config['max_limit'] = current_pos
                self.limits_updated = True

    def start_teleoperation(self) -> bool:
        """Start the teleoperation in a background thread."""
        try:
            logger.info("Starting teleoperation...")

            self.teleop_running = True
            self.teleop_thread = threading.Thread(target=self._teleoperation_loop, daemon=True)
            self.teleop_thread.start()

            # Wait a moment for teleoperation to initialize
            time.sleep(3.0)

            if not self.teleop_running:
                logger.error("Teleoperation failed to start")
                return False

            logger.info("Teleoperation started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start teleoperation: {e}")
            return False

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

            status_lines = []
            status_lines.append("Current Joint Positions and Limits:")
            status_lines.append("-" * 50)

            # Show joint status
            for joint_config in self.config_data['robot']['joints']:
                joint_name = joint_config['name']
                joint_key = f"{joint_name}.pos"

                if joint_key in self.current_observation:
                    current_pos = self.current_observation[joint_key]
                    min_limit = joint_config['min_limit']
                    max_limit = joint_config['max_limit']

                    status_lines.append(
                        f"{joint_name:15}: {current_pos:8.4f} "
                        f"(limits: {min_limit:8.4f} to {max_limit:8.4f})"
                    )

            # Show gripper status
            gripper_config = self.config_data['robot']['gripper']
            gripper_name = gripper_config['name']
            gripper_key = f"{gripper_name}.pos"

            if gripper_key in self.current_observation:
                current_pos = self.current_observation[gripper_key]
                min_limit = gripper_config['min_limit']
                max_limit = gripper_config['max_limit']

                status_lines.append(
                    f"{gripper_name:15}: {current_pos:8.4f} "
                    f"(limits: {min_limit:8.4f} to {max_limit:8.4f})"
                )

            return "\n".join(status_lines)

    def run_calibration(self):
        """Run the calibration process."""
        print("=" * 60)
        print("JOINT LIMITS CALIBRATION")
        print("=" * 60)
        print()
        print("This script will track joint positions during teleoperation")
        print("and automatically update min/max limits as you move the robot.")
        print()
        print("Make sure:")
        print("- Both robot and leader device are connected and powered on")
        print("- The workspace is clear of obstacles")
        print("- You have emergency stop readily available")
        print()

        input("Press ENTER to start teleoperation...")

        # Start teleoperation
        if not self.start_teleoperation():
            raise RuntimeError("Failed to start teleoperation")

        try:
            print()
            print("Teleoperation is now active!")
            print("Move the robot through its full range of motion.")
            print("Joint limits will be updated automatically.")
            print()
            print("Press ENTER to stop calibration...")

            # Show status updates while running
            last_status_time = 0
            while True:
                try:
                    # Show status every 2 seconds
                    current_time = time.time()
                    if current_time - last_status_time > 2.0:
                        print("\r" + " " * 80 + "\r", end="")  # Clear line
                        print(self.get_current_status())
                        print("\nPress ENTER to stop calibration...")
                        last_status_time = current_time

                    # Check if user pressed enter (non-blocking)
                    import select
                    if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                        input()  # Consume the input
                        break

                    time.sleep(0.1)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error during calibration: {e}")
                    time.sleep(0.5)

        finally:
            self.stop_teleoperation()

        print("\n" + "=" * 60)
        print("CALIBRATION COMPLETE!")
        print("=" * 60)

        if self.limits_updated:
            print("\nJoint limits were updated during calibration.")
        else:
            print("\nNo joint limits were updated (robot stayed within existing limits).")

    def save_config(self):
        """Save updated configuration to file."""
        if not self.config_path:
            return

        try:
            # Create backup of original file
            backup_path = f"{self.config_path}.backup"
            if Path(self.config_path).exists():
                import shutil
                shutil.copy2(self.config_path, backup_path)
                print(f"Backup saved to: {backup_path}")

            # Save updated config
            with open(self.config_path, 'w') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    yaml.dump(self.config_data, f, default_flow_style=False, sort_keys=False)
                elif self.config_path.endswith('.json'):
                    json.dump(self.config_data, f, indent=2)

            print(f"Updated configuration saved to: {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to save config file: {e}")

    def print_config_formats(self):
        """Print the updated configuration in both JSON and YAML formats."""
        print("\n" + "=" * 60)
        print("UPDATED CONFIGURATION")
        print("=" * 60)

        # Print JSON format
        print("\nJSON Format:")
        print("-" * 20)
        print(json.dumps(self.config_data, indent=2))

        print("\n")

        # Print YAML format
        print("YAML Format:")
        print("-" * 20)
        print(yaml.dump(self.config_data, default_flow_style=False, sort_keys=False))

    def cleanup(self):
        """Clean up resources."""
        self.stop_teleoperation()


def main():
    parser = argparse.ArgumentParser(
        description="Calibrate robot joint limits using teleoperation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--robot-port",
        help="Serial port for the follower robot (e.g., /dev/ttyUSB0). If not provided, will use port from config file."
    )

    parser.add_argument(
        "--teleop-port",
        help="Serial port for the leader device (e.g., /dev/ttyUSB1). If not provided, will use port from config file."
    )

    parser.add_argument(
        "--config",
        help="Path to config file to update (JSON or YAML). If not provided, results are printed to console."
    )

    args = parser.parse_args()

    try:
        # Create calibrator
        calibrator = JointLimitsCalibrator(
            robot_port=args.robot_port,
            teleop_port=args.teleop_port,
            config_path=args.config
        )

        # Run calibration
        calibrator.run_calibration()

        # Save config if path provided, otherwise print to console
        if args.config:
            calibrator.save_config()
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