import os
p = os.path.expanduser("~/mnt/HackMIT/PRESENTATION-HANDOFF.md")
x = open(p, encoding="utf-8").read()
old = ('| Muse Image in the build | Listed by Meta as available. This project does not use it. |\n')
if old in x:
    x = x.replace(old, "")
row = ("| Meta keepsake images | `muse-image-1.0` via `https://api.meta.ai/v1/images/generations`, "
       "endpoint `/moments/keepsake`, UI in `app/components/moment/Keepsake.tsx` | "
       "`hardware-demo/eegdemo/imagery.py` |\n")
anchor = "\n### Not true. Do not put these on a slide."
x = x.replace(anchor, row + anchor, 1)
x = x.replace("| 7 | **Healthcare 1**, everyday reflection and children | New. Carries a WHAT WE DO NOT CLAIM strip |",
              "| 7 | **\"Mental health reflection.\"** Everyday reflection and children | New. Office and child figures top right; WHAT WE DO NOT CLAIM strip |")
x = x.replace("| 8 | **Healthcare 2**, dementia and a trusted clinician | New. Carries the honest-limits card |",
              "| 8 | **Healthcare 2**, dementia and a trusted clinician | New. Elder figure top right; honest-limits card |")
x = x.replace("| 17 | Meta | Six verticals with status pills |",
              "| 17 | Meta | Six surfaces. Muse Image keepsakes now LIVE; SEE and GROUND merged into one card |")
open(p, "w", encoding="utf-8").write(x)
print("ok", len(x))
