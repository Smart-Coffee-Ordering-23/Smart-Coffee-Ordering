"""Webcam module (Member 2).

Other files only need three things from this class:
    camera.is_connected   -> True/False
    camera.read_frame()   -> a mirrored frame (BGR image) or None
    camera.release()      -> close the webcam

A background thread keeps reading from the webcam, so:
  * a slow or glitchy camera never freezes the UI,
  * the app always sees the FRESH frame (no old buffer backlog),
  * a dropped connection is retried automatically.
read_frame() returns None when no fresh frame exists (stale > 1 s).
"""
import sys
import threading
import time

import cv2

from src import config

MAX_FAILED_READS = 30 
class Camera:
    def __init__(self, camera_index=0, width=config.CAMERA_WIDTH, height=config.CAMERA_HEIGHT):
        self.capture = None
        self.error_message = ""
        self.failed_reads = 0
        self.width = width
        self.height = height
        self._camera_index = camera_index
        self._lock = threading.Lock()        
        self._capture_lock = threading.RLock() 
        self._latest = None            
        self._running = False
        self._thread = None
        self._reconnect_at = 0.0
        self._open(camera_index, width, height)
        self._start_thread()

    def _open(self, camera_index, width, height):
        with self._capture_lock:
            backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
            try:
                capture = cv2.VideoCapture(camera_index, backend)
            except Exception as error: 
                self._set_error(f"Could not start the camera: {error}")
                return

            if not capture.isOpened():
                capture.release()
                self._set_error("Camera not found. Check that a webcam is connected "
                                "and not used by another program.")
                return

            capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, config.CAMERA_BUFFER_FRAMES)  
            self.capture = capture
            self.failed_reads = 0
            self.error_message = ""

    def _set_error(self, message):
        if message != self.error_message:      
            print(f"[Camera] {message}")
        self.error_message = message

    def _start_thread(self):
        if self._thread is not None and self._thread.is_alive():
            return                           
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop,
                                        name="camera-capture", daemon=True)
        self._thread.start()

    def _capture_loop(self):
        """Grab frames continuously; reconnect automatically after a dropout."""
        while self._running:
            if self.capture is None:
                if time.monotonic() >= self._reconnect_at:
                    self._open(self._camera_index, self.width, self.height)
                    if self.capture is None:
                        self._reconnect_at = time.monotonic() + config.CAMERA_RECONNECT_SECONDS
                        time.sleep(0.2)
                    else:
                        print("[Camera] Reconnected.")
                else:
                    time.sleep(0.2)
                continue

            success, frame = self.capture.read()
            if not success or frame is None:
                self.failed_reads += 1
                if self.failed_reads >= MAX_FAILED_READS:
                    self._set_error("Camera connection lost - retrying...")
                    self._close_capture()
                    self._reconnect_at = time.monotonic() + config.CAMERA_RECONNECT_SECONDS
                else:
                    time.sleep(0.01)
                continue

            self.failed_reads = 0
            frame = cv2.flip(frame, 1)          
            with self._lock:
                self._latest = (frame, time.monotonic())

    def _close_capture(self):
        with self._capture_lock:
            if self.capture is not None:
                self.capture.release()
                self.capture = None
            with self._lock:
                self._latest = None
    @property
    def is_connected(self):
        return self.capture is not None

    def read_frame(self):
        """Return the newest mirrored frame, or None when none is fresh."""
        with self._lock:
            latest = self._latest
        if latest is None:
            return None
        frame, taken_at = latest
        if time.monotonic() - taken_at > config.CAMERA_FRAME_STALE_SECONDS:
            return None                    
        return frame

    def release(self):
        self._running = False
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)        
        self._thread = None
        self._close_capture()