import os
import sys
from pathlib import Path

import numpy as np
from openpi_client.websocket_client_policy import WebsocketClientPolicy
sys.path.append(str(Path(__file__).parent.parent))
from src import VideoHandler

def test_server():
    # Connect to server on port 8000
    policy = WebsocketClientPolicy(host=os.getenv("OPENPI_IP"), port=8000)

    # Get server metadata
    metadata = policy.get_server_metadata()
    print(f"Connected to server. Metadata: {metadata}")

    # Initialize video handler
    video_handler = VideoHandler(camera_index=0, image_height=224, image_width=224)

    camera_image = video_handler.capture_frame()

    # Create observation in the expected format
    obs = {
        "observation/image": camera_image,
        "observation/wrist_image": camera_image,
        "observation/state": np.array([0.9]).astype(np.float32),
        "observation/gripper_position": np.array([0.1, 0.2, 0.3, 0.4, 0.5]).astype(np.float32),
        "prompt": "hello world"
    }

    # Run inference
    result = policy.infer(obs)
    print(f"Inference result: {result}")

if __name__ == "__main__":
    test_server()