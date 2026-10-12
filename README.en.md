# VideoRockola

[Español](README.md) | **English**

A jukebox-style music video player built with **Python**, **PyQt6** and **VLC**. It shows a logo and a preview at the top and the song list below, plays videos in full screen, and lets you **add videos to a queue** without leaving full screen.

## Interface layout

```
┌───────────────────────┬──────────┐
│         LOGO          │  VIDEO   │
├───────────────────────┴──────────┤
│            SONG LIST             │
└──────────────────────────────────┘
```

- **Logo** (top left): read from `logo.png` in the application folder. A default one is generated if it does not exist.
- **Video** (top right): preview of the selected video.
- **Song list** (bottom): main list with a large, readable font.

## Features

- **Settings with the `P` key**: manage several video directories, supported formats, the logo and volume normalization. Saved to `config.json`.
- Loads videos from **several directories** at once; every video found is shown in a single list sorted in ascending order by title.
- **Automatic focus on the list**: on startup (if there is at least one video), when a video ends with nothing left in the queue, and when leaving full screen with `Esc`.
- Selectable **formats** with checkboxes, from those known to VLC.
- **Automatic preview**: once you stop navigating the list for about 1.2 seconds, the selected video plays from its midpoint for 5 seconds and then pauses. While you navigate (for example, holding `↑` or `↓`) no video is loaded, so the list stays responsive. The delay is set by the `PREVIEW_DELAY_MS` constant.
- **Full screen** with `Enter`: hides the logo and list and plays the video from the start.
- **Playback queue** in full screen, with a bottom panel and automatic playback of the next video.
- **Volume normalization** (VLC `normvol` filter) to even out volume between videos, in both the preview and full screen.
- Pause/resume with the space bar.
- Works on Windows, Linux and macOS.

## Requirements

- Python 3.9 or later
- [VLC media player](https://www.videolan.org/vlc/) installed on the system (VLC's architecture must match Python's)
- Python libraries: `PyQt6` and `python-vlc`

```bash
pip install PyQt6 python-vlc
```

## Usage

```bash
python videorockola.py
```

1. On the first run the settings dialog opens. Add one or more directories with videos and save.
2. Browse the list: after you pause for about 1.2 s, a 5-second preview starts from the middle of the video.
3. Press **Enter** to watch it in full screen from the beginning.
4. In full screen, press **↑** or **↓** to open the queue panel and add videos (double-click or `Enter`).
5. Press **Esc** to skip to the next queued video or, if the queue is empty, leave full screen.

## Controls

| Action | Control |
|---|---|
| Open settings (outside full screen) | `P` |
| Preview | Pause for about 1.2 s on a video in the list |
| Full screen | `Enter` |
| Pause / Resume | `Space` |
| Open queue panel (full screen only) | `↑` / `↓` |
| Add a video to the queue | Double-click or `Enter` in the queue panel |
| Close queue panel | `Esc` (or automatically after 5 s without interaction) |
| Next queued video | `Esc` in full screen (if the queue has videos) |
| Leave full screen | `Esc` (if the queue is empty) |

## Settings dialog (`P`)

- **Music video directories**: list with buttons to add and remove. There can be more than one.
- **Supported video formats**: checkable list with `.mp4`, `.m4v`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.f4v`, `.webm`, `.mpg`, `.mpeg`, `.ts`, `.m2ts`, `.mts`, `.3gp`, `.ogv`, `.vob`, `.divx`, `.asf`, `.rm`, `.rmvb`. `.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv`, `.flv` and `.webm` are checked by default.
- **Logo**: preview and a "Change logo…" button. The chosen image is saved as `logo.png` in the application folder.
- **Normalize volume**: turns normalization on or off. This change takes effect after restarting the application.

When you save, the song list is reloaded with the new directories and formats (and the queue is cleared).

## Volume normalization

It uses VLC's `normvol` audio filter, which adjusts the volume dynamically so louder videos do not stand out. The same player is used for the preview and for full screen, so it applies to both. The parameters (`--norm-buff-size` and `--norm-max-level`) can be tuned in the code for a stronger or weaker effect.

## Playback queue

- Borderless panel, always on top, as wide as the screen and covering the bottom 18% of its height.
- It only opens in full screen while a video is playing.
- It hides after **5 seconds** without interaction; the timer pauses while you navigate with the arrow keys.
- Queued videos appear in the list with the `En cola:` prefix (the interface text is in Spanish).
- When a video ends (or `Esc` is pressed), the first video in the queue plays.
- If the queue is empty when a video ends, the player leaves full screen and focus returns to the list.

## Window icon

The application looks for the icon in this order: `icon.ico`, `icon.png` and, if neither exists, `logo.png`, first next to the program and then inside the executable. On Windows it also registers its own application ID so the taskbar shows this icon instead of Python's. To use a different icon, just replace `icon.ico` (ideally with several sizes: 16, 32, 48, 64, 128 and 256 px).



## Project files

```
videorockola.py       # The whole application
icon.ico / icon.png   # Window and executable icon
logo.png              # Logo (a default one is created if missing)
config.json           # Settings (created on save)
requirements.txt      # Dependencies
README.md             # Documentation (Spanish)
README.en.md          # Documentation (English)
```

## Notes

- If VLC cannot be initialized, the application shows an error and exits.
- If no videos are loaded, the list tells you to press `P` to configure the directories.
- The end of a video is received on VLC's thread and forwarded to Qt's thread through a signal, to avoid unexpected crashes.
