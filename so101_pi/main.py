import cv2
import numpy as np
from openpi_client.websocket_client_policy import WebsocketClientPolicy

def capture_camera_image(camera_id=0, width=224, height=224):
    """Capture an image from the camera and resize it to the expected format."""
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera {camera_id}")

    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError("Failed to capture image from camera")

    # Resize to expected dimensions
    frame = cv2.resize(frame, (width, height))

    # Convert from BGR to RGB (OpenCV uses BGR by default)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Convert to format expected by the model: (C, H, W) uint8
    frame = np.transpose(frame, (2, 0, 1))

    return frame.astype(np.uint8)

def main():
    # Connect to server on port 8000
    policy = WebsocketClientPolicy(host="165.227.47.97", port=8000)

    # Get server metadata
    metadata = policy.get_server_metadata()
    print(f"Connected to server. Metadata: {metadata}")

    # Capture image from camera 0
    try:
        camera_image = capture_camera_image(camera_id=0)
        print(f"Captured image shape: {camera_image.shape}")
    except Exception as e:
        print(f"Camera capture failed: {e}")
        # Fallback to random image
        camera_image = np.random.randint(256, size=(3, 224, 224), dtype=np.uint8)
        print("Using random image as fallback")

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