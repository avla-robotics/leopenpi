#!/usr/bin/env python3

import time
import cv2
import base64
import os
import threading
import numpy as np
from PIL import Image
from openpi_client.image_tools import convert_to_uint8, resize_with_pad

class VideoHandler:
    """
    Handles video capture operations including continuous frame capture and goal image capture.
    """

    def __init__(self, camera_index: int = 0, fps: float = 4.0, cleanup_threshold: int = 30,
                 image_height: int = 224, image_width: int = 224):
        """
        Initialize VideoHandler.

        Args:
            camera_index: Camera index (0 for default camera)
            fps: Frame rate for continuous capture
            cleanup_threshold: Number of frames before cleanup starts deleting old frames
            image_height: Target height for resized images
            image_width: Target width for resized images
        """
        self.camera_index = camera_index
        self.fps = fps
        self.cleanup_threshold = cleanup_threshold
        self.image_height = image_height
        self.image_width = image_width
        self.frame_interval = 1.0 / fps

        # Frame buffer using list for manual cleanup
        self.frame_buffer = []
        self.capture_thread = None
        self.cleanup_thread = None
        self.capture_active = False
        self.cap = None
        self._lock = threading.Lock()


    def start_continuous_capture(self):
        """
        Start continuous frame capture in a background thread.
        """
        if self.capture_active:
            return

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_index}")

        # Allow camera to warm up
        time.sleep(1)

        self.capture_active = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def stop_continuous_capture(self):
        """
        Stop continuous frame capture.
        """
        if not self.capture_active:
            return

        self.capture_active = False
        if self.capture_thread:
            self.capture_thread.join(timeout=4.0)
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=4.0)

        if self.cap:
            self.cap.release()
            self.cap = None

    def get_frames(self, num_frames: int = 15) -> list[np.ndarray]:
        """
        Get the most recent frames from the buffer.

        Args:
            num_frames: Number of frames to return (default 15)

        Returns:
            List of numpy array frames in (C, H, W) format (empty if not enough frames available)
        """
        with self._lock:
            if len(self.frame_buffer) < num_frames:
                return []

            # Return the last num_frames frames
            return self.frame_buffer[-num_frames:]



    def load_and_encode_image(self, image_path: str) -> str:
        """
        Load an image from file and encode it as base64.

        Args:
            image_path: Path to the image file

        Returns:
            Base64-encoded image string
        """
        try:
            pil_image = Image.open(image_path)
            # Convert to RGB if not already
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')

            return self._encode_image_to_base64(pil_image)

        except Exception as e:
            raise RuntimeError(f"Failed to load image {image_path}: {e}")

    def _capture_loop(self):
        """
        Background thread loop for continuous frame capture.
        """
        frame_count = 0
        last_capture_time = time.time()

        # Create outputs directory if it doesn't exist
        os.makedirs("./outputs", exist_ok=True)

        while self.capture_active:
            current_time = time.time()

            # Check if it's time to capture next frame
            if current_time - last_capture_time >= self.frame_interval:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to capture frame")
                    continue

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Apply openpi-client transformations and convert to (C, H, W)
                img_array = convert_to_uint8(frame_rgb)
                img_array = resize_with_pad(img_array, self.image_height, self.image_width)
                processed_frame = np.transpose(img_array, (2, 0, 1)).astype(np.uint8)

                with self._lock:
                    self.frame_buffer.append(processed_frame)

                frame_count += 1
                last_capture_time = current_time
            else:
                # Sleep for a short time to avoid busy waiting
                time.sleep(0.01)

    def _cleanup_loop(self):
        """
        Background thread loop for cleaning up old frames.
        """
        while self.capture_active:
            time.sleep(2.0)

            with self._lock:
                current_count = len(self.frame_buffer)
                if current_count > self.cleanup_threshold:
                    frames_to_delete = current_count - self.cleanup_threshold
                    self.frame_buffer = self.frame_buffer[frames_to_delete:]

    def _encode_image_to_base64(self, pil_image: Image.Image) -> str:
        """
        Encode a PIL Image to base64 string using openpi-client image tools.

        Args:
            pil_image: PIL Image object

        Returns:
            Base64-encoded image string
        """
        import io

        # Convert PIL image to numpy array
        img_array = np.array(pil_image)

        # Apply openpi-client image transformations
        img_array = convert_to_uint8(img_array)

        # Resize with padding to target dimensions
        img_array = resize_with_pad(img_array, self.image_height, self.image_width)

        # Convert back to PIL Image
        processed_image = Image.fromarray(img_array)

        # Save image to bytes buffer as JPEG
        buffer = io.BytesIO()
        processed_image.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)

        # Encode to base64
        image_bytes = buffer.getvalue()
        base64_string = base64.b64encode(image_bytes).decode('utf-8')

        return base64_string



    def __del__(self):
        """
        Cleanup when object is destroyed.
        """
        self.stop_continuous_capture()