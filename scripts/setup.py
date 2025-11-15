#!/usr/bin/env python3
"""
Interactive setup script for creating robot configuration files.
This script guides users through setting up their robot, teleop device, cameras, and workspace.
"""

import os
import sys
import subprocess
import json
import yaml
from pathlib import Path


def get_input(prompt: str, default: str = None) -> str:
    """Get user input with optional default value."""
    if default:
        user_input = input(f"{prompt} (default: {default}): ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()


def get_yes_no(prompt: str, default: bool = False) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} ({default_str}): ").strip().lower()
    if not response:
        return default
    return response in ['y', 'yes']


def run_script(script_name: str, *args):
    """Run a script from the scripts directory."""
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        print(f"Error: Script {script_name} not found at {script_path}")
        sys.exit(1)

    try:
        subprocess.run([sys.executable, str(script_path)] + list(args), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")
        sys.exit(1)


def print_step(step_number: int, title: str):
    """Print a formatted step header."""
    print(f"Step {step_number}: {title}")
    print("-" * 60)


def remove_none_values(d):
    """Recursively remove None values from dictionaries."""
    if isinstance(d, dict):
        return {k: remove_none_values(v) for k, v in d.items() if v is not None}
    elif isinstance(d, list):
        return [remove_none_values(item) for item in d]
    else:
        return d


def save_config(config: dict, filepath: str):
    """Save configuration to JSON or YAML file."""
    path = Path(filepath)

    # Create parent directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Remove None values to avoid draccus issues
    cleaned_config = remove_none_values(config)

    if path.suffix.lower() == '.json':
        with open(path, 'w') as f:
            json.dump(cleaned_config, f, indent=2)
    elif path.suffix.lower() in ['.yaml', '.yml']:
        with open(path, 'w') as f:
            yaml.dump(cleaned_config, f, default_flow_style=False, sort_keys=False)
    else:
        print(f"Error: Unsupported file format. Please use .json or .yaml")
        sys.exit(1)

    print(f"✓ Configuration saved to {filepath}")


def main():
    print("=" * 60)
    print("SO-101 Robot Setup Wizard")
    print("=" * 60)
    print()

    # Initialize configuration dictionary
    config = {}

    # Step 1: Get config file path
    print_step(1, "Configuration File Location")
    config_path = get_input("Where would you like to save the config?", "config.yaml")
    print()

    # Step 2: Leader (Teleop) Configuration
    print_step(2, "Leader (Teleop) Configuration")
    leader_port = input("Enter leader port: ").strip()
    leader_id = get_input("Enter leader ID", "leader")

    config['teleop'] = {
        'port': leader_port,
        'id': leader_id
    }
    print()

    # Step 3: Follower (Robot) Configuration
    print_step(3, "Follower (Robot) Configuration")
    follower_port = input("Enter follower port: ").strip()
    follower_id = get_input("Enter follower ID", "follower")

    config['robot'] = {
        'port': follower_port,
        'id': follower_id
    }
    print()

    # Step 4: Task Prompt (needed before calibration)
    print_step(4, "Task Configuration")
    config['prompt'] = input("Enter task prompt: ").strip()
    print()

    # Step 5: Server Configuration (needed before calibration)
    print_step(5, "Server Configuration")
    config['server_ip'] = get_input("Enter server IP", "0.0.0.0")
    server_port = get_input("Enter server port", "8000")
    try:
        config['server_port'] = int(server_port)
    except ValueError:
        print("Invalid port number. Using default: 8000")
        config['server_port'] = 8000
    print()

    # Step 6: Camera Configuration (needed before calibration)
    print_step(6, "Camera Configuration")
    cameras = []

    while get_yes_no("Would you like to add a camera?", default=False):
        camera = {}

        # Get camera index
        camera_index = input("Enter camera index (e.g., 0, 1, 2): ").strip()
        try:
            camera['index'] = int(camera_index)
        except ValueError:
            print("Invalid camera index. Skipping this camera.")
            continue

        # Get camera name
        camera['name'] = get_input("Enter camera name (e.g., 'image', 'wrist_image')")

        # Ask about flipping first
        camera['flipped'] = get_yes_no("Would you like to flip this camera?", default=False)

        # Don't initialize crop values yet - only add them if cropping is done

        # Ask about cropping
        if get_yes_no("Would you like to crop this camera?", default=False):
            # Need to save config with all required fields first
            temp_config = config.copy()
            temp_config['cameras'] = cameras + [camera]
            save_config(temp_config, config_path)

            print("Running crop camera script...")
            run_script("crop_camera.py", "--config_path", config_path)

            # Reload config to get crop values
            config_file = Path(config_path)
            if config_file.exists():
                if config_file.suffix.lower() == '.json':
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                else:
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)

            # Update camera with crop values from reloaded config
            if 'cameras' in config and len(config['cameras']) > len(cameras):
                updated_camera = config['cameras'][-1]
                # Only add crop fields if they have values
                if 'minX' in updated_camera and updated_camera['minX'] is not None:
                    camera['minX'] = updated_camera['minX']
                    camera['maxX'] = updated_camera['maxX']
                    camera['minY'] = updated_camera['minY']
                    camera['maxY'] = updated_camera['maxY']

        cameras.append(camera)
        print()

    config['cameras'] = cameras
    print()

    # Step 7: Workspace Calibration
    print_step(7, "Workspace Calibration")
    print("You are going to create a workspace calibration, which determines")
    print("the safe working bounds of your workspace.")
    input("Press Enter to continue...")
    print()

    # Save initial config before running calibration
    save_config(config, config_path)

    # Run calibration script
    print("Running calibration script...")
    run_script("calibrate.py", "--config_path", config_path)
    print()

    # Reload config to get calibrated joints
    config_file = Path(config_path)
    if config_file.exists():
        if config_file.suffix.lower() == '.json':
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

    # Step 8: Home Position
    print_step(8, "Home Position Configuration")
    if get_yes_no("Would you like to set a starting position for the robot?", default=False):
        # Save current config before running set_home
        save_config(config, config_path)

        print("Running set home script...")
        run_script("set_home.py", "--config_path", config_path)
        config['start_home'] = True

        # Reload config to get home positions
        if config_file.exists():
            if config_file.suffix.lower() == '.json':
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
    else:
        config['start_home'] = False
    print()

    # Save final configuration
    save_config(config, config_path)

    # Success message
    print()
    print("=" * 60)
    print("✓ Setup Complete!")
    print("=" * 60)
    print(f"Your robot configuration has been saved to: {config_path}. Now run:")
    print()
    print(f"uv run leopenpi/main.py --config_path={config_path}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError during setup: {e}")
        sys.exit(1)
