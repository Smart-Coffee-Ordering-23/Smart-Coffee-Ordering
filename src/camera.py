"""Webcam module (Member 2).

Other files only need three things from this class:
    camera.is_connected   -> True/False
    camera.read_frame()   -> a mirrored frame (BGR image) or None
    camera.release()      -> close the webcam
"""
import sys

import cv2

MAX_FAILED_READS = 30  # after this many failed reads in a row we treat the camera as lost


class Camera:
    def __init__(self, camera_index=0, width=640, height=480):
        self.capture = None
        self.error_message = ""
        self.failed_reads = 0
        self._open(camera_index, width, height)

    def _open(self, camera_index, width, height):
        # On Windows, the DirectShow backend opens the camera much faster.
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        try:
            capture = cv2.VideoCapture(camera_index, backend)
        except Exception as error:  # OpenCV can raise unexpected errors on some systems
            self.error_message = f"Could not start the camera: {error}"
            print(f"[Camera] {self.error_message}")
            return

        if not capture.isOpened():
            capture.release()
            self.error_message = ("Camera not found. Check that a webcam is connected "
                                  "and not used by another program.")
            print(f"[Camera] {self.error_message}")
            print("[Camera] The app will still run - use the keyboard controls instead.")
            return

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture = capture

    @property
    def is_connected(self):
        return self.capture is not None

    def read_frame(self):
        """Return one mirrored frame, or None if no frame is available."""
        if self.capture is None:
            return None

        success, frame = self.capture.read()
        if not success or frame is None:
            self.failed_reads += 1
            if self.failed_reads >= MAX_FAILED_READS:
                self.error_message = "Camera connection lost."
                print(f"[Camera] {self.error_message}")
                self.release()
            return None

        self.failed_reads = 0
        return cv2.flip(frame, 1)  # flip left-right so it acts like a mirror

    def release(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None
