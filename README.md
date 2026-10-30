# Smart Coffee Ordering

## 1. Project Introduction

A **touch-free coffee ordering kiosk**. Instead of a mouse or a touchscreen, the
customer orders with **hand and face gestures** in front of a webcam.

```
Camera -> Hand / Face Tracking -> Gesture Recognition -> Interaction Controller
       -> Coffee Menu -> Cart -> Order Confirmation -> Order Manager (SQLite)
       -> Kitchen Queue -> Order Complete
```

The project demonstrates Computer Vision, Gesture Recognition and
Human-Computer Interaction with a modern, warm coffee-shop interface.

## 2. Features

- Beautiful modern kiosk UI: navbar with logo, step rail, coffee cards with
  your **12 real coffee images**, toasts, compact camera panel
- Full flow: Welcome > Menu > Select > Quantity > Discount > Confirm > Summary > Done
- Hand gestures: open palm, pointing, swipe left/right, two fingers, thumbs up, fist
- Face gestures: **smile = 10% discount** (once per order), deliberate blink = back
- Debounce + hold time + cooldown: one gesture = one action, never repeats
- 12-product menu loaded from `data/menu.json`, 6 cards per page (3 x 2)
- Cart with quantities, subtotal, discount and total
- Orders saved to SQLite (`data/orders.db`), kitchen queue (Preparing > Completed)
- Coffee-shop style sound feedback for every step: welcome, select, add-to-cart,
  quantity ticks, swipe whooshes, smile discount, order success, brewing
  (volume in `SOUND_VOLUME`, press `M` to mute)
- **Keyboard + mouse fallback**: the whole app works without a camera
- `DEBUG_MODE` hides all technical values until you need them

## 3. Technology

| Tool | Used for |
|---|---|
| Python 3.11 / 3.12 | main language |
| OpenCV | webcam capture + image handling |
| MediaPipe 0.10.21 | hand and face landmark tracking |
| Pygame CE | all drawing (UI, camera preview, sounds) |
| SQLite (built-in) | saving orders in `data/orders.db` |
| pytest | automated tests |

> MediaPipe 0.10.21 does not support Python 3.13 yet - use Python 3.11 or 3.12.

## 4. Project Structure

```
smart-coffee-ordering/
├── main.py                     <- entry point: bootstraps everything, main loop
├── requirements.txt
├── README.md
├── tools/
│   ├── generate_sounds.py      <- regenerates the legacy UI sounds (stdlib only)
│   ├── inspect_db.py           <- read-only peek into data/orders.db
│   └── smoke_run.py            <- runs the real app loop for N frames, then exits
├── src/
│   ├── config.py               <- settings: window, colors, DEBUG_MODE, timing
│   ├── camera.py               <- webcam (OpenCV)
│   ├── hand_tracker.py         <- hand + face landmark tracking (MediaPipe)
│   ├── gesture_engine.py       <- pose/swipe/smile/blink recognition + debounce
│   ├── interaction_controller.py <- gestures -> application actions
│   ├── menu_manager.py         <- loads data/menu.json, paging, selection
│   ├── product.py              <- Product model
│   ├── cart.py                 <- quantities, subtotal, 10% discount, total
│   ├── order_manager.py        <- save/read orders (SQLite, parameterized SQL)
│   ├── kitchen_queue.py        <- Preparing -> Completed
│   ├── audio_manager.py        <- coffee-shop sounds (volume, cooldowns, scheduling)
│   └── renderer.py             <- all Pygame drawing (the whole UI)
├── data/
│   ├── menu.json               <- the 12 coffees (source of truth)
│   └── orders.db               <- created automatically on first order
├── assets/
│   ├── products/               <- your 12 coffee images
│   ├── icons/logo.png          <- shop logo
│   ├── sounds/                 <- 26 short WAV sounds (real recordings, see sounds/CREDITS.md)
│   └── fonts/                  <- optional custom fonts
├── tests/
│   ├── test_audio.py
│   ├── test_gesture.py
│   ├── test_cart.py
│   ├── test_menu.py
│   ├── test_order.py
│   └── test_controller.py      <- protects against duplicate order confirmation
└── docs/
```

## 5. Installation

Open a terminal in the project folder, then:

```
python -m venv .venv
```

Activate it:

- Windows: `.venv\Scripts\activate`
- macOS / Linux: `source .venv/bin/activate`

Install the packages:

```
python -m pip install -r requirements.txt
```

## 6. How to Run

```
python main.py
```

Press **Q** to quit, **ESC** to go back (it quits from Welcome / Done).
Allow camera access if your system asks. If no camera is found the app still
starts and you can use the keyboard and mouse.

## 7. Gesture Controls

| Gesture | What it does | Keyboard |
|---|---|---|
| OPEN PALM | Open the menu / start a new order / add another coffee | `O` |
| POINTING (hold ~1 s) | Select the coffee card under your finger | `P`, mouse click, `Enter` on the menu |
| SWIPE RIGHT / LEFT | Next / previous page on the menu, +1 / -1 on quantity, otherwise next / previous screen | `→` / `←` |
| TWO FINGERS | Quantity +1 (keep holding to keep counting) | `2` |
| THUMBS UP | Continue / confirm | `T` or `Enter` |
| FIST | Cancel the current choice or clear the order | `F` |
| SMILE | 10% discount (Discount / Confirm screen, once per order) | `G` |
| BLINK (eyes closed ~0.5 s) | Go back one screen | `B` |

Tips:
- Hold a gesture for about a second - the **Hold gesture** bar in the camera
  panel shows the progress.
- A **BLINK** means closing your eyes for about half a second; normal quick
  blinks are ignored on purpose.
- For a swipe, move your **open palm** sideways quickly.
- Good light and a plain background help a lot.

## 8. Keyboard & Mouse Controls

| Key | Action |
|---|---|
| `←` / `→` | navigation (page / quantity / screens) |
| `Enter` | select (on the menu) / confirm (everywhere else) |
| `Esc` | back (quits from Welcome / Done) |
| `C` | clear the cart |
| `S` | jump to the order summary |
| `Q` | quit the app |
| `F1`-`F8` | jump to Welcome, Menu, Select, Quantity, Discount, Confirm, Summary, Done |
| `F11` | toggle fullscreen |
| `M` | mute / unmute the sounds |
| Mouse | click cards, buttons, page arrows, quantity +/-, step rail |

## 9. Menu Information

- The menu lives in **`data/menu.json`** - the only place coffee data is stored.
- Each product has `id`, `name`, `price`, `image` and `description`.
- All **12 coffee images** are in `assets/products/` and are shown on
  2 pages of 6 cards (3 columns x 2 rows).
- To change a price or add a coffee, edit `data/menu.json` - no Python change
  needed. If an image file is missing the card shows a cup placeholder
  (a different coffee's image is never used as a replacement).

## 10. Database Information

- SQLite file: **`data/orders.db`** (created automatically).
- Table `orders`: `id`, `created_at`, `subtotal`, `discount`, `total`, `status`
- Table `order_items`: `id`, `order_id`, `product_id`, `product_name`, `quantity`, `price`
- All queries are parameterized (no string-built SQL).
- Status flow: `Confirmed` -> `Preparing` (kitchen queue) -> `Completed`.
- Delete `data/orders.db` any time to start fresh - it is rebuilt on the next run.

## 11. Testing

From the project folder:

```
pytest
```

or:

```
python -m pytest -v
```

Covered: gesture recognition + debounce/cooldown (with synthetic hand data),
cart math including the 10% discount, menu loading/paging/selection, order
saving to SQLite and the kitchen queue, the sound system (files, cooldowns,
volume, event mapping), and controller guards such as the
**duplicate-order-on-double-confirm** protection. **No camera is needed for
any test.** A live smoke check of the real app loop (camera + tracking +
drawing) is available separately:

```
python tools/smoke_run.py 40
```

## 12. Troubleshooting

| Problem | Solution |
|---|---|
| `Could not find a usable camera` | Close other apps using the webcam; the app keeps working with keyboard/mouse |
| Hand not detected | Improve lighting, use a plain background, keep the whole hand inside the preview |
| Gestures fire too early/late | Tune `GESTURE_HOLD_SECONDS` and `GESTURE_COOLDOWN` in `src/config.py` |
| Smile never triggers | Set `DEBUG_MODE = True` in `src/config.py`, watch the *Smile w/thr* row, adjust `SMILE_WIDTH_THRESHOLD` / `SMILE_WIDTH_MARGIN` / `SMILE_LIFT_DROP_RATIO` |
| No sound | Press `M` (must be on), check `SOUND_ENABLED` and `SOUND_VOLUME` in `src/config.py` and the WAV files in `assets/sounds/` - missing sounds never crash the app |
| Menu empty | Look at the console message and validate `data/menu.json` (JSON syntax) |
| MediaPipe install error | Use Python 3.11/3.12 and `python -m pip install -r requirements.txt` |
| Technical detail needed | Set `DEBUG_MODE = True` in `src/config.py` to show landmarks, ratios and raw values |
