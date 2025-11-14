# LeOpenPI

A Python package for controlling the SO-101 robot arm through OpenPI client runtime with video observation support.

## Overview

LeOpenPI provides a bridge between the SO-101 robot hardware and the OpenPI client runtime system. It enables remote control of the robot arm through WebSocket connections while capturing video observations from multiple cameras.

## Features

- **Robot Control**: Full 6-DOF control of the SO-101 robot arm
- **Video Capture**: Multi-camera support for observation collection
- **Remote Operation**: WebSocket-based policy execution
- **Configuration Management**: Flexible environment and robot configuration
- **Logging**: Comprehensive logging with configurable levels

## Requirements

- Python >=3.11,<3.12
- SO-101 robot hardware
- USB camera(s)

## Installation

```bash
# Install dependencies and setup development environment
uv sync

# For production installation
uv pip install -e .
```

## Dependencies

- `openpi-client`: OpenPI runtime client
- `opencv-python`: Computer vision and video capture

## Usage

### Basic Usage

```python
from draccus import parse
from leopenpi.main import main
from leopenpi.utils.configurations import EnvironmentConfiguration

# Parse configuration from command line
config = parse(EnvironmentConfiguration)
main(config)
```

### Configuration

The system uses `EnvironmentConfiguration` for setup:

```python
@dataclass
class EnvironmentConfiguration:
    prompt: str                    # Task prompt/description
    cameras: dict[str, int]        # Camera mapping (name -> device_id)
    robot: RobotConfiguration      # Robot hardware config
    server_ip: str                 # WebSocket server IP
    server_port: int = 8000        # WebSocket server port
    max_steps: int = 1000          # Maximum episode steps
    log_level: str = "INFO"        # Logging level
```

### Robot Configuration

The SO-101 robot configuration includes joint specifications:

```python
@dataclass
class RobotConfiguration:
    port: str                      # Serial port for robot communication
    joints: list[Joint]            # Joint configuration (auto-configured)
```

Default joints:
- `shoulder_pan`: Shoulder rotation (-1.0 to 1.0)
- `shoulder_lift`: Shoulder elevation (-1.0 to 1.0)
- `elbow_flex`: Elbow joint (-1.0 to 1.0)
- `wrist_flex`: Wrist pitch (-1.0 to 1.0)
- `wrist_roll`: Wrist rotation (-1.0 to 1.0)
- `gripper`: Gripper control (0.0 open to 1.0 closed)

## Architecture

### Core Components

- **`RobotWrapper`**: Hardware interface for SO-101 robot
- **`RobotEnvironment`**: OpenPI environment implementation
- **`VideoHandler`**: Camera capture and frame processing
- **`LoggingSubscriber`**: Runtime event logging

### Data Flow

1. **Initialization**: Robot connects and cameras initialize
2. **Observation**: System captures camera frames and robot state
3. **Policy**: WebSocket client receives observations and returns actions
4. **Execution**: Actions are sent to robot hardware
5. **Logging**: All events are logged for debugging and analysis

## Development

### Project Structure

```
leopenpi/
├── main.py                 # Entry point
├── robot_environment.py    # Environment implementation
└── utils/
    ├── configurations.py   # Configuration classes
    ├── robot_wrapper.py    # Robot hardware interface
    ├── video_handler.py    # Camera capture
    └── logging_subscriber.py # Event logging
```

### Running from Source

```bash
# Navigate to project directory
cd leopenpi

# Run with configuration
python -m leopenpi.main --prompt "Pick up the red block" \
                        --cameras '{"front": 0}' \
                        --robot.port "/dev/ttyUSB0" \
                        --server_ip "localhost"
```

## Hardware Setup

1. Connect SO-101 robot to computer via USB
2. Connect cameras to USB ports
3. Ensure robot is calibrated and operational
4. Verify camera device IDs with `ls /dev/video*`

## Troubleshooting

### Common Issues

- **Robot connection fails**: Check USB cable and port permissions
- **Camera not found**: Verify camera device ID and USB connection
- **WebSocket connection error**: Ensure server is running and accessible
- **Permission denied**: May need `sudo` for serial port access

### Logging

Enable debug logging for detailed troubleshooting:

```python
config.log_level = "DEBUG"
```
