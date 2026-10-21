"""Smoke test: run the real CoffeeApp event loop for a few frames, then exit.

Drives the same code paths as `python main.py` (input events, camera frame,
hand/face tracking, gesture engine, drawing, kitchen queue, sounds) without
waiting for the user to close the window. Development only - not a unit test.
"""
import sys
from pathlib import Path

# When run as `python tools/smoke_run.py`, Python puts tools/ (not the project
# root) on sys.path - add the project root so `import main` and `import src` work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

import main as main_module

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 30

app = main_module.CoffeeApp()
print("constructed | camera:", app.camera.is_connected,
      "| menu:", len(app.menu.products),
      "| db:", app.order_manager.is_available)

frame_read_ok = False
try:
    for i in range(FRAMES):
        events = app.read_input_events() + app.read_vision_events()
        if app.frame is not None:
            frame_read_ok = True
        app.update_pointer()
        app.update_hover_context()
        for event in events:
            handled = app.controller.handle_event(event)
            if handled is False:
                app.engine.rearm()
        app.kitchen.update()
        app.handle_kitchen_events()
        app.controller.update()
        app.draw()
        # simulate one frame so audio scheduling runs too
        started = app.audio.update()
        if started:
            print("scheduled sounds started:", started)
        app.clock.tick(120)   # no need for the real FPS in a smoke run
    print("ran", FRAMES, "frames | camera frame read:", frame_read_ok,
          "| last screen:", app.controller.screen,
          "| hand seen:", app.hand_landmarks is not None)
finally:
    app.close()
    print("closed cleanly")
