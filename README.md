# LeOpenPI

A Python client for controlling the Lerobot SO-101 robot arm through an OpenPI server.

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
uv pip install -e .
```


### Robot Configuration

The client uses a configuration to describe the workspace. To generate a configuration, run
```bash
uv run scripts/setup.py
````
This will produce a configuration file like this:
```yaml
prompt: Some prompt
teleop:
  port: /dev/tty.usbmodemXXXXX
  id: leader
server_ip: 0.0.0.0
start_home: true
policy_type: openpi OR teleop
server_port: 8000
max_steps: 1000
log_level: INFO
robot:
  port: /dev/tty.usbmodemXXXXX
  id: follower
  joints:
  - name: shoulder_pan
    min_limit: -100
    max_limit: 100
    home: 0
  - name: shoulder_lift
    min_limit: -100
    max_limit: 100
    home: 0
  - name: elbow_flex
    min_limit: -100
    max_limit: 100
    home: 0
  - name: wrist_flex
    min_limit: -100
    max_limit: 100
    home: 0
  - name: wrist_roll
    min_limit: -100
    max_limit: 100
    home: 0
  gripper:
    name: gripper
    min_limit: -100
    max_limit: 100
    home: 0
cameras:
- name: image
  index: 1
  flipped: false
  minX: 0
  maxX: 1000
  minY: 0
  maxY: 1000
```

## Running

To inference from an Openpi server, run:
```bash
uv run leopenpi/main.py --config_path=config.yaml
```
You can set `policy_type` in your config to `teleop` to run a mock policy using a leader arm.

To set up an Openpi server, follow the instructions from the [openpi repo](https://github.com/Physical-Intelligence/openpi):

### Notes
- Openpi does not provide a server side policy for lerobot
  - The simplest thing to do is modify the [libero policy](https://github.com/Physical-Intelligence/openpi/blob/175f89c31d1b2631a8ff3b678768f17489c5ead4/src/openpi/policies/libero_policy.py#L100) to output 6 joints instead of 7. This library will automatically only use the first 6 joints, even if 7 are sent. 
  - If you train your own policy, you may want to create your own config to best handle your own inputs
- Running OpenPi requires a Nvidia GPU. Best results come from cloud hosting.
  - During testing, we've been using [Digital Ocean](https://m.do.co/c/1fc674ab871a)*, which offers antiquate servers for under $2/hr
  - We are working on building our own cheaper and easier to use server solution. If you'd like to beta test it with some free credits, send an email to `founders@avla.ai`.

 *referral link

### Common Issues

- **Camera not found**: Verify camera device ID and USB connection. It may help to use lerobot's `find-cameras` util.
- **Failed to read from camera**: You might be overloading your USB bus. If you have multiple cameras, connect them to different busses.
- **Client immediately hangs**: It is likely waiting for a web socket response. Check your server.

### Logging

Enable debug logging for detailed troubleshooting:

```python
log_level = "DEBUG"
```
## Contributing

We welcome contributions! If you find a bug, please create a Github issue. If you know the solution, feel free to submit a PR and we'll review it within 2 days.

If you'd like to contact the maintainers, email `founders@avla.ai`.