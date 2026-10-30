"""Tiny geometry helpers shared by the hand and face tracking code.

Keeping this in ONE place means the distance formula is never written
twice (hand tracking in gesture_engine.py, face tracking here).
"""
import math

def distance(point_a, point_b):
    """Straight-line distance between two (x, y) points."""
    return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])