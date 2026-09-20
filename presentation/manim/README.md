# Explanatory animations for the pitch deck

Three Manim scenes, rendered into the deck as short silent clips. Every number in them
comes from this repository — the header of `scenes.py` says which file each one is from.

| Scene | Answers | Length |
|---|---|---|
| `DataIn` | Where the numbers come from, and what is frozen before modelling. Peak-to-peak appears here and only here, as the ±150 µV artifact-rejection threshold. | 18 s |
| `WhyCalibrate` | Why the baseline has to be yours: identical amplitude scores z = +4.1 on one wearer and +0.8 on another. | 23 s |
| `Persistence` | Four consecutive windows, and why overlapping windows cost an order of magnitude in false alarms. | 19 s |

## Rendering

Needs `libcairo2-dev libpango1.0-dev dvisvgm texlive ffmpeg` plus `pip install manim`,
and the repo's own fonts on the font path so the animations match the app:

```bash
cp ../../video/memory-palace/fonts/*.ttf ~/.local/share/fonts/ && fc-cache -f
python -m manim --resolution 1920,1080 --fps 30 scenes.py DataIn
python -m manim --resolution 1920,1080 --fps 30 scenes.py WhyCalibrate
python -m manim --resolution 1920,1080 --fps 30 scenes.py Persistence
```

Then compress for the deck (the originals are larger than they need to be):

```bash
ffmpeg -i <scene>.mp4 -c:v libx264 -crf 24 -preset slow -pix_fmt yuv420p \
       -movflags +faststart -an m-<scene>.mp4
```

## If you change a number in the code

Change it here too. `scenes.py` hard-codes the values so the animation and the repository
can drift, which is the one failure mode worth guarding against. The header comment lists
every source file.
