#!/usr/bin/env python3
"""
Camera Crop Calibration Script

This script allows users to calibrate camera crop regions by drawing bounding boxes
on camera images and saving the crop coordinates to the configuration file.

Usage:
    python crop_camera.py --config config.yaml
    python crop_camera.py --config config.json
    crop_camera --config config.yaml  # If installed as package

The script will:
1. Open each camera from the config
2. Display a frame from the camera
3. Allow the user to draw a bounding box
4. Save the minX and maxY coordinates to the config
"""
import argparse
import sys
import yaml
import json
import cv2
import logging

from draccus import parse

from leopenpi import EnvironmentConfiguration

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


class CameraCropCalibrator:
    """
    Interactive camera crop calibration tool.

    Displays camera frames and allows users to draw bounding boxes to define crop regions.
    """

    def __init__(self, config: EnvironmentConfiguration):
        self.config = config
        self.bbox_start = None
        self.bbox_end = None
        self.drawing = False
        self.current_frame = None
        self.display_frame = None

    def mouse_callback(self, event, x, y, flags, param):
        """Mouse callback for drawing bounding box."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.bbox_start = (x, y)
            self.bbox_end = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.bbox_end = (x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.bbox_end = (x, y)

    def update_display(self):
        """Update the display with the current bounding box."""
        if self.current_frame is None:
            return

        self.display_frame = self.current_frame.copy()

        if self.bbox_start and self.bbox_end:
            cv2.rectangle(
                self.display_frame,
                self.bbox_start,
                self.bbox_end,
                (0, 255, 0),
                2
            )

            # Display coordinates
            minX = min(self.bbox_start[0], self.bbox_end[0])
            maxX = max(self.bbox_start[0], self.bbox_end[0])
            minY = min(self.bbox_start[1], self.bbox_end[1])
            maxY = max(self.bbox_start[1], self.bbox_end[1])

            text = f"minX: {minX}, maxX: {maxX}, minY: {minY}, maxY: {maxY}"
            cv2.putText(
                self.display_frame,
                text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    def show_cropped_preview(self, camera_config, minX, maxX, minY, maxY):
        """Show a preview of the cropped image and ask for confirmation."""
        # Open camera again
        cap = cv2.VideoCapture(camera_config.index)
        if not cap.isOpened():
            logger.error(f"Failed to open camera {camera_config.index}")
            return False

        # Capture a frame
        ret, frame = cap.read()
        cap.release()

        if not ret:
            logger.error(f"Failed to capture frame from camera {camera_config.index}")
            return False

        # Convert to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Apply the crop using all 4 coordinates
        cropped = frame_rgb[minY:maxY, minX:maxX]

        # Convert back to BGR for display
        cropped_bgr = cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR)

        # Create preview window
        preview_window = f"Cropped Preview - {camera_config.name}"
        cv2.namedWindow(preview_window)

        print(f"\nCropped Preview for {camera_config.name}")
        print("Instructions:")
        print("  - Press 's' to SAVE this crop")
        print("  - Press 'r' to RE-CROP (go back to drawing)")
        print("  - Press 'q' to SKIP this camera (don't save)")

        while True:
            cv2.imshow(preview_window, cropped_bgr)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('s'):
                # Confirm save
                cv2.destroyWindow(preview_window)
                return 'save'
            elif key == ord('r'):
                # Re-crop
                cv2.destroyWindow(preview_window)
                return 'recrop'
            elif key == ord('q'):
                # Skip
                cv2.destroyWindow(preview_window)
                return 'skip'

    def calibrate_camera(self, camera_config):
        """Calibrate crop region for a single camera."""
        logger.info(f"Calibrating camera: {camera_config.name} (index: {camera_config.index})")

        while True:  # Loop to allow re-cropping
            # Open camera
            cap = cv2.VideoCapture(camera_config.index)
            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_config.index}")
                return False

            # Capture a frame
            ret, frame = cap.read()
            if not ret:
                logger.error(f"Failed to capture frame from camera {camera_config.index}")
                cap.release()
                return False

            # Convert to RGB for display
            self.current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.current_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_RGB2BGR)
            self.display_frame = self.current_frame.copy()

            # Reset bounding box
            self.bbox_start = None
            self.bbox_end = None
            self.drawing = False

            # Create window and set mouse callback
            window_name = f"Crop Calibration - {camera_config.name}"
            cv2.namedWindow(window_name)
            cv2.setMouseCallback(window_name, self.mouse_callback)

            print(f"\nCamera: {camera_config.name}")
            print("Instructions:")
            print("  - Draw a bounding box by clicking and dragging")
            print("  - Press 'ENTER' to preview the crop")
            print("  - Press 'r' to reset the bounding box")
            print("  - Press 'q' to skip this camera")

            crop_drawn = False

            while True:
                self.update_display()
                cv2.imshow(window_name, self.display_frame)

                key = cv2.waitKey(1) & 0xFF

                if key == 13:  # Enter key
                    # Preview crop
                    if self.bbox_start and self.bbox_end:
                        minX = min(self.bbox_start[0], self.bbox_end[0])
                        maxX = max(self.bbox_start[0], self.bbox_end[0])
                        minY = min(self.bbox_start[1], self.bbox_end[1])
                        maxY = max(self.bbox_start[1], self.bbox_end[1])

                        # Close current window
                        cap.release()
                        cv2.destroyWindow(window_name)

                        # Show preview and get user decision
                        decision = self.show_cropped_preview(camera_config, minX, maxX, minY, maxY)

                        if decision == 'save':
                            # Store all 4 crop coordinates
                            camera_config.minX = minX
                            camera_config.maxX = maxX
                            camera_config.minY = minY
                            camera_config.maxY = maxY
                            logger.info(f"Saved crop region: minX={minX}, maxX={maxX}, minY={minY}, maxY={maxY}")
                            return True
                        elif decision == 'recrop':
                            # Break inner loop to re-crop
                            crop_drawn = False
                            break
                        elif decision == 'skip':
                            logger.info("Skipped camera")
                            return True
                    else:
                        logger.warning("No bounding box drawn. Draw a box first.")

                elif key == ord('r'):
                    # Reset bounding box
                    self.bbox_start = None
                    self.bbox_end = None
                    self.drawing = False
                    logger.info("Reset bounding box")

                elif key == ord('q'):
                    logger.info("Skipped camera")
                    cap.release()
                    cv2.destroyWindow(window_name)
                    return True

            # If we broke out of inner loop due to recrop, continue outer loop
            if not crop_drawn:
                continue

    def run_calibration(self):
        """Run calibration for all cameras."""
        print("=" * 60)
        print("CAMERA CROP CALIBRATION")
        print("=" * 60)

        if not self.config.cameras:
            logger.error("No cameras found in configuration")
            return False

        for camera in self.config.cameras:
            if not self.calibrate_camera(camera):
                logger.warning(f"Failed to calibrate camera: {camera.name}")
                continue

        cv2.destroyAllWindows()

        print("\n" + "=" * 60)
        print("CALIBRATION COMPLETE!")
        print("=" * 60)

        return True

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
        """Save the updated configuration to a file."""
        # Convert config to dict for serialization
        config_dict = self._config_to_dict(self.config)

        # Reorder keys to put 'cameras' and 'robot' at the bottom
        ordered_dict = {}

        # Add all keys except 'cameras' and 'robot' first
        for key in config_dict:
            if key not in ['cameras', 'robot']:
                ordered_dict[key] = config_dict[key]

        # Add robot section if it exists (second to last)
        if 'robot' in config_dict:
            robot_dict = config_dict['robot']
            # Remove computed properties
            if 'all_joints' in robot_dict:
                del robot_dict['all_joints']
            ordered_dict['robot'] = robot_dict

        # Add cameras section last
        if 'cameras' in config_dict:
            ordered_dict['cameras'] = config_dict['cameras']

        with open(path, 'w') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                yaml.dump(ordered_dict, f, default_flow_style=False, sort_keys=False)
            elif path.endswith('.json'):
                json.dump(ordered_dict, f, indent=2)
            else:
                raise ValueError("Config file must be YAML or JSON.")
            logger.info(f"Updated configuration saved to: {path}")


def main():
    config = parse(EnvironmentConfiguration)
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config_path", help="Path to save the updated config file")
    args = argparser.parse_args()

    try:
        calibrator = CameraCropCalibrator(config)

        if not calibrator.run_calibration():
            logger.error("Calibration failed")
            sys.exit(1)

        # Print camera crop settings
        print("\nCamera Crop Settings:")
        print("-" * 40)
        for camera in config.cameras:
            if all(hasattr(camera, attr) for attr in ['minX', 'maxX', 'minY', 'maxY']):
                print(f"{camera.name}: minX={camera.minX}, maxX={camera.maxX}, minY={camera.minY}, maxY={camera.maxY}")
            else:
                print(f"{camera.name}: No crop region set")

        if args.config_path:
            calibrator.save_config(args.config_path)
        else:
            logger.warning("No config_path provided. Changes not saved.")
            print("\nTo save changes, run with: --config_path <path>")

        print("\nCalibration completed successfully!")

    except KeyboardInterrupt:
        print("\nCalibration interrupted by user")
        cv2.destroyAllWindows()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        cv2.destroyAllWindows()
        sys.exit(1)


if __name__ == "__main__":
    main()