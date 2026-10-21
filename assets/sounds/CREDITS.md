# Sound Credits — Smart Coffee Ordering

Every sound effect in this folder is a **genuine recorded or
artist-created sound** downloaded from a reputable free library.
No empty files, no renamed files, no generated beeps.

| File | Duration | Source | Author | License | Source URL |
|---|---|---|---|---|---|
| `coffee_brewing.wav` | 4.5 s | SoundBible — "Making Espresso" (espresso machine foaming & bubbling) | BlastwaveFx.com | CC BY 3.0 (Attribution) | https://www.soundbible.com/548-Making-Espresso.html |
| `coffee_pouring.wav` | 7.8 s | SoundBible — "Pouring Hot Tea" (hot water poured for tea/coffee) | Cori Samuel | **Public Domain** | https://www.soundbible.com/1244-Pouring-Hot-Tea.html |
| `cup_place.wav` | 1.0 s | Mixkit — "Set down jelly jar" (glass jar placed on a surface) | Mixkit | Mixkit Sound Effects Free License (commercial use, no attribution required) | https://mixkit.co/free-sound-effects/kitchen/ (ID 1809) |
| `gesture_detected.wav` | 2.2 s | Mixkit — "Game user interface tone" | Mixkit | Mixkit Sound Effects Free License | https://mixkit.co/free-sound-effects/interface/ (ID 1108) |
| `add_to_cart.wav` | 1.7 s | Mixkit — "Game interface sound" | Mixkit | Mixkit Sound Effects Free License | https://mixkit.co/free-sound-effects/interface/ (ID 1106) |
| `order_success.wav` | 1.5 s | Mixkit — "Page turn chime" | Mixkit | Mixkit Sound Effects Free License | https://mixkit.co/free-sound-effects/interface/ (ID 2570) |
| `cancel.wav` | 2.5 s | Mixkit — "Squeak notification" (trimmed) | Mixkit | Mixkit Sound Effects Free License | https://mixkit.co/free-sound-effects/ding/ (ID 929) |
| `discount.wav` | 1.8 s | Mixkit — "Fluttering coin" (money saved!) | Mixkit | Mixkit Sound Effects Free License | https://mixkit.co/free-sound-effects/coins/ (ID 3183) |
| `cafe_ambience.wav` | 20.0 s | Mixkit — "Hotel restaurant ambience and footsteps" (trimmed + fades) | Mixkit | Mixkit Sound Effects Free License | https://mixkit.co/free-sound-effects/restaurant/ (ID 454) |
| `coffee_beans.wav` | 2.5 s (trimmed) | Wikimedia Commons — "Coffee beans sucked to the silo" | Work With Sounds | CC BY 4.0 | https://commons.wikimedia.org/wiki/File:WWS_Coffeebeanssuckedtothesilo.ogg |

## Note on `coffee_beans.wav`

The recording was downloaded from Wikimedia Commons (CC BY 4.0 by
Work With Sounds), converted from OGG to 44.1 kHz / 16-bit stereo WAV
and trimmed to 2.5 s with short fade-in/out so it stays soft.

## Attribution requirements

- `coffee_brewing.wav` (CC BY 3.0): attribution to **BlastwaveFx.com** —
  this table satisfies that requirement; keep it with your project.
- `coffee_pouring.wav` (Public Domain): no attribution required.
- `coffee_beans.wav` (CC BY 4.0): attribution to **Work With Sounds** via
  Wikimedia Commons — this table satisfies that requirement.
- Mixkit files: free for commercial and non-commercial use without
  attribution (Mixkit Sound Effects Free License,
  https://mixkit.co/license/#sfxFree).

All MP3 sources were converted to 44.1 kHz / 16-bit stereo WAV with
ffmpeg; two files were trimmed (cancel 8 s → 2.5 s, ambience 28 s → 20 s
with fade-in/out for smoother looping).

## Legacy files in this folder

The older, previously generated placeholder sounds (`select.wav`,
`gesture.wav`, `swipe.wav`, `back.wav`, `qty_up.wav`, `qty_down.wav`,
`empty.wav`, `error.wav`, `welcome.wav`, `brew.wav`, `confirm.wav`,
`sent.wav`, `success.wav`, `smile.wav`, `add_cart.wav`) are kept for
backwards compatibility but are no longer used by the audio mapping in
`src/audio_manager.py` (except the small UI ticks: swipe, back, qty_up,
qty_down, empty, error, welcome).
