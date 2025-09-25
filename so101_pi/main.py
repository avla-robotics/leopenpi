import os
import time
import numpy as np
from openpi_client.websocket_client_policy import WebsocketClientPolicy
from so101_pi.utils.video_handler import VideoHandler

def main():
    # Connect to server on port 8000
    policy = WebsocketClientPolicy(host=os.getenv("OPENPI_IP"), port=8000)

    # Get server metadata
    metadata = policy.get_server_metadata()
    print(f"Connected to server. Metadata: {metadata}")

    # Initialize video handler
    video_handler = VideoHandler(camera_index=0, image_height=224, image_width=224)

    # Capture image from camera
    try:
        video_handler.start_continuous_capture()
        time.sleep(2)  # Wait for frames to be captured

        frames = video_handler.get_frames(num_frames=1)
        if frames:
            camera_image = frames[0]
            print(f"Captured image shape: {camera_image.shape}")

        else:
            raise RuntimeError("No frames captured")
    except Exception as e:
        print(f"Camera capture failed: {e}")
        # Fallback to random image
        camera_image = np.random.randint(256, size=(3, 224, 224), dtype=np.uint8)
        print("Using random image as fallback")
    finally:
        video_handler.stop_continuous_capture()

    # Create observation in the expected format
    obs = {
        "observation/exterior_image_1_left": camera_image,
        "observation/wrist_image_left": camera_image,
        "observation/gripper_position": np.array([0.9]).astype(np.float32),
        "observation/joint_position": np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.0, 0.0]).astype(np.float32),
        "prompt": "hello world"
    }

    # Run inference
    result = policy.infer(obs)
    print(f"Inference result: {result}")

if __name__ == "__main__":
    main()