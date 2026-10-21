# Smart Coffee Ordering — Project Documentation

## 1. Project Overview

Smart Coffee Ordering is a Python-based touch-free coffee ordering application. Customers can interact with the application using supported hand and face gestures in front of a webcam, with keyboard and mouse controls available as alternatives.

The project demonstrates computer vision, gesture recognition, and human-computer interaction through a coffee-shop-style user interface.

## 2. Project Objectives

- Develop a touch-free coffee ordering application.
- Use a camera to capture input for gesture interaction.
- Detect hand and face landmarks and recognize supported gestures.
- Let customers browse coffee products, select items, and manage quantities.
- Allow customers to review and confirm an order.
- Store confirmed order information in a local SQLite database.
- Provide clear visual and audio feedback during interactions.

## 3. Main Features

The README describes the following intended application features:

- A coffee-shop interface with a menu and 12 coffee product images.
- A coffee menu loaded from `data/menu.json`.
- Gesture-based navigation and selection.
- A shopping cart with quantities, subtotal, discount, and total.
- Order management and a kitchen queue.
- SQLite storage in `data/orders.db`.
- Sound feedback for supported interactions.
- Keyboard and mouse controls as a fallback.
- Automated tests for core modules.

**Status note:** Mark each feature as completed only after it has been run and tested successfully. If a feature is not yet working, record it as in progress or not yet verified.

## 4. Technologies Used

| Technology | Purpose in the project |
|---|---|
| Python | Main programming language |
| OpenCV | Webcam capture and image handling |
| MediaPipe | Hand and face landmark tracking, as described in the README |
| Pygame CE | Drawing the interface and playing sounds |
| SQLite | Local storage for orders |
| pytest | Automated testing |
| Git and GitHub | Version control and team collaboration |

The current README recommends Python 3.11 or 3.12 for compatibility with the specified MediaPipe version. Check the project's actual `requirements.txt` before installing dependencies.

## 5. System Workflow

The high-level workflow described in the README is:

1. Start the application.
2. Capture video from the camera, if available.
3. Track hand or face landmarks.
4. Recognize a supported gesture or receive keyboard/mouse input.
5. Pass the input to the interaction controller.
6. Browse the coffee menu and select a product.
7. Set quantity and review the cart.
8. Apply a discount if the feature is available and enabled.
9. Confirm the order.
10. Save order information in SQLite and show the order summary.
11. Update the kitchen queue, if implemented.

The exact behavior should match the current source code. The keyboard and mouse fallback can be used to test the ordering flow without a camera.

## 6. Main Components

| File or folder | Responsibility described in the README |
|---|---|
| `main.py` | Application entry point and main loop |
| `src/config.py` | Window, color, debug, and timing settings |
| `src/camera.py` | Webcam capture |
| `src/hand_tracker.py` | Hand and face landmark tracking |
| `src/gesture_engine.py` | Gesture recognition, including debounce/cooldown |
| `src/interaction_controller.py` | Connects recognized inputs to application actions |
| `src/menu_manager.py` | Loads menu data, paging, and selection |
| `src/product.py` | Product model |
| `src/cart.py` | Cart quantities and price calculations |
| `src/order_manager.py` | Saves and reads orders in SQLite |
| `src/kitchen_queue.py` | Kitchen order status/queue |
| `src/audio_manager.py` | Sound playback and sound settings |
| `src/renderer.py` | Draws the Pygame user interface |
| `data/menu.json` | Coffee menu data |
| `data/orders.db` | Local order database, created by the application |
| `assets/products/` | Coffee product images |
| `assets/sounds/` | Sound files |
| `tests/` | Automated tests |

## 7. Data and Order Management

According to the README, the application uses SQLite at `data/orders.db` to store order information. The documented tables are:

- `orders`: order ID, creation time, subtotal, discount, total, and status.
- `order_items`: item ID, order ID, product ID, product name, quantity, and price.

The README describes a status flow from confirmation to preparation and completion. Verify the actual database schema and status transitions in the code before presenting them as tested behavior.

## 8. Installation and Setup

### Prerequisites

- Python version supported by the project's dependencies; the README recommends Python 3.11 or 3.12.
- A webcam for camera-based interaction. Keyboard and mouse fallback may be used when a camera is unavailable.
- The project files and `requirements.txt`.

### Setup steps

1. Open the project folder in VS Code.
2. Open a terminal in the project folder.
3. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

4. Activate it on Windows:

   ```powershell
   .venv\Scripts\activate
   ```

   In Git Bash, use:

   ```bash
   source .venv/Scripts/activate
   ```

   On macOS or Linux, use:

   ```bash
   source .venv/bin/activate
   ```

5. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

6. Run the application:

   ```bash
   python main.py
   ```

Use the exact Python version and package versions listed in the current `requirements.txt` if they differ from this guide.

## 9. User Controls

The README documents gesture controls such as open palm, pointing, swiping, two fingers, thumbs up, fist, smile, and blink. It also documents keyboard and mouse alternatives.

The precise mapping of each gesture to an action may depend on the current implementation. Refer to the **Gesture Controls** and **Keyboard & Mouse Controls** tables in `README.md` for the full mappings.

## 10. Testing Plan

Test each component separately before testing the complete application.

| Area | What to check | Result |
|---|---|---|
| Startup | `python main.py` starts without an unhandled error | To be tested |
| Camera | Camera opens when available; fallback works if not | To be tested |
| Hand/face tracking | Landmarks are detected under suitable lighting | To be tested |
| Gesture recognition | Supported gestures trigger the intended action once | To be tested |
| Menu | Menu data loads and products can be selected | To be tested |
| Cart | Quantities, subtotal, discount, and total are calculated correctly | To be tested |
| Orders | Confirmed orders are saved and can be read | To be tested |
| Kitchen queue | Status changes follow the implemented flow | To be tested |
| Audio | Available sound files play without crashing the app | To be tested |
| Automated tests | Run `python -m pytest -v` and review failures | To be tested |

Update the Result column with **Pass**, **Fail**, or **Not implemented** only after testing. Add a short note describing any errors that need to be fixed.

## 11. Limitations and Current Status

The application is under development. Camera conditions, gesture stability, dependency compatibility, and integration between modules may affect its behavior.

Before the final demonstration, the team should:
- Run the application from `main.py`.
- Test the main coffee ordering flow from menu selection to order confirmation.
- Check that stored order information is correct.
- Run the automated tests and fix or document failures.
- Update this document and `README.md` to reflect the actual implementation.

Do not claim that a feature is complete until it has been verified.

## 12. Team Collaboration

The team uses Git and GitHub to manage code changes. Members should work on their assigned branches, test their changes, and submit them for review before merging into the main branch.

## 13. References Within the Project

- `README.md` — installation, run instructions, controls, menu, database, tests, and troubleshooting.
- `requirements.txt` — Python package dependencies and versions.
- `docs/project-requirements.docx` — teacher-provided requirements, if present in the project folder.
