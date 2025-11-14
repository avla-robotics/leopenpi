import time
import cv2
import numpy as np
import os
from openpi_client.image_tools import convert_to_uint8, resize_with_pad

from .configurations import Camera


class VideoHandler:
    """
    Handles video capture operations for a robot environment.
    """

    def __init__(self, camera: Camera, image_height: int = 224, image_width: int = 224, debug: bool = False):
        """
        Initialize VideoHandler.

        Args:
            camera: Camera configuration object
            image_height: Target height for resized images
            image_width: Target width for resized images
            debug: Whether to save debug images
        """
        self.camera_index = camera.index
        self.image_height = image_height
        self.image_width = image_width
        self.flipped = camera.flipped

        self.crop_enabled = all(coord is not None for coord in [camera.minX, camera.maxX, camera.minY, camera.maxY])
        self.minX = camera.minX if self.crop_enabled else None
        self.maxX = camera.maxX if self.crop_enabled else None
        self.minY = camera.minY if self.crop_enabled else None
        self.maxY = camera.maxY if self.crop_enabled else None

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_index}")
        time.sleep(0.5)
        # Capture and discard a few frames to ensure camera is ready
        for _ in range(3):
            self.cap.read()

        self.debug = debug
        if self.debug:
            os.makedirs("debug", exist_ok=True)

    def capture_frame(self) -> np.ndarray:
        """
        Capture a single frame on demand.

        Returns:
            Single numpy array frame in (C, H, W) format
        """
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to capture frame for camera " + str(self.camera_index))

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self.flipped:
            frame_rgb = cv2.flip(frame_rgb, 1)

        if self.crop_enabled:
            frame_rgb = frame_rgb[self.minY:self.maxY, self.minX:self.maxX]

        # Apply openpi-client transformations and convert to (C, H, W)
        img_array = convert_to_uint8(frame_rgb)
        img_array = resize_with_pad(img_array, self.image_height, self.image_width)
        processed_frame = np.transpose(img_array, (2, 0, 1)).astype(np.uint8)

        if self.debug:
            debug_path = f"debug/{self.camera_index}.jpg"
            debug_img = np.transpose(processed_frame, (1, 2, 0))
            debug_img = cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR)
            cv2.imwrite(debug_path, debug_img)

        return processed_frame
