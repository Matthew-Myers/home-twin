---
name: scan-to-blender
description: Turn an iPhone RoomPlan/Polycam USDZ scan plus walkthrough videos of a home into a Blender floorplan render, then room models matched to the video at a chosen detail level (bare, shelves cleared, decluttered, as-is), then high-quality lit renders, driving the user's live Blender over blender-mcp. Use when the user hands over a .usdz scan and/or room videos and wants a floorplan, a 3D model of their rooms, furniture recreated, or renders of their space (also the starting point for remodel concepts).
---

# Scan to Blender

A level of a home (floor, basement), from scan and video to approved, lit, as-is room models. Each
phase ends at a user approval gate. Read `reference/lessons.md` first: the principles there
override habits. `reference/gotchas.md` has the technical traps; `reference/materials.md` the
texture recipes.

## Requirements

- Blender 4.2 or newer (developed on 5.2). `blender` below means its executable: Windows
  `C:\Program Files\Blender Foundation\Blender <ver>\blender.exe`, macOS
  `/Applications/Blender.app/Contents/MacOS/Blender`, Linux `blender` on PATH. Find it once and
  reuse the full path. Every script runs in Blender's own Python: no system Python, PIL or ffmpeg.
- Optional: the blender MCP server for live editing (Phase 0). Without it, everything runs headless.
- A GPU helps for Cycles but isn't required (`RENDER_DEVICE=CPU` forces the CPU).

## Project layout (one project per level)

```
<project>/
  source/scan/<level>.usdz          the scan (exactly one; scripts find it)
  source/video/*.mp4|.MOV           walkthroughs (any names)
  frames/<room>/00.jpg ...           stills per room; frames/<room>_more/f<frame>.jpg for dense pulls
  scripts/                           copy of this skill's scripts/ (incl. rooms/_neighbours.py)
  scripts/level.py                   level shell (floorplan stage)
  scripts/rooms/<room>.py            build_asis() + CAMERAS per room
  assets/polyhaven/<id>/             CC0 textures/HDRIs/models (fetch_polyhaven.py)
  renders/<room>/                    asis_*.jpg, cmp_*.jpg, test_*.jpg, final_*.jpg, *.blend
  renders/house/                     whole-level views (house.py)
  furniture.md                       the approved item lists
```

Copy `scripts/*` from this skill into `<project>/scripts/`, and the user's files into `source/`
(never work from Downloads). Coordinates everywhere: **plan metres from the level's south-west
corner, x east, y north, z = 0 at the floor**, so all rooms stack into one scene.

## Phase 0: live Blender

Invoke the **blender-mcp-setup** skill: it checks or installs Blender, the MCP server and the
add-on, and proves the live link with a visible change. If it falls back to headless, carry on
headless. Use live MCP for edits the user can watch; render long Cycles jobs headless in the
background. Room scripts must run both ways (`rk.reset()` handles it).

## Phase 1: read the scan and the videos

```
blender -b -P scripts/inspect_scan.py      object list, bounds, overview PNGs
blender -b -P scripts/catalogue.py         every scanned object: kind, size, plan position
blender -b -P scripts/room_survey.py -- x0 y0 x1 y1     walls, openings, items in a plan box
blender -b -P scripts/extract_one.py -- <video> frames/<name> 30
blender -b -P scripts/contact_sheet.py -- frames/<name> frames/sheet-<name>.jpg
```

- Check the scale line (`scan_io: ... -> K = 10`) and confirm the footprint with the user.
- Read a contact sheet per video. Work out which room each video shows, rename the frames folders
  by room, and note per room what's on each wall, in video order, with frame numbers.
- **Inventory from the stills, not the scan** (lessons 3-4): note what shapes the space but is
  missing from the scan or wrong in it (structure, stairs, built-ins, open storage, openings).
  List nothing that isn't in a still.

## Phase 2: floorplan → approval gate

`scripts/level.py`: clean walls with `rk.shell()` per room from the survey (not the zero-thickness
scan panels), openings, stairs rebuilt procedurally, everything from the Phase 1 inventory that
shapes the space (structure, big storage), scanned items as labelled blocks. Render `plan`
(orthographic, north up, room names and sizes in m and ft-in) and `cutaway` (3/4 view, walls cut at
~1.5 m, structure exempt from the cut). Example: `reference/example_level.py` (a small two-room
level: shells, openings, windows, built-ins and scanned items as labelled blocks).

Show both, with at most a short batch of layout questions (stair direction, an opening or wall
you can't read), each with its still. **Stop: "Does the floorplan look right?"** Fix until
approved.

## Phase 3: detail level + item list → approval gate

Ask once, with AskUserQuestion, which detail preset to use (lessons 9-12). The user can override
it per room:
- **bare**: shell, structure and fixed installations only.
- **shelves cleared**: plus furniture, shelving and desks, all empty.
- **decluttered** (default, recommended): plus the things that belong on them (computers,
  appliances, books, plants, lamps); no mess; tidy and rearrange rather than delete.
- **as-is**: everything, simplified (piles as piles, loose papers stacked).

Then write `furniture.md`: per room, a short list of the main items, each with its approximate
size (metric and imperial). Group small things ("books on the bookshelf", "tools on the
pegboard"). Show it once and ask: "Add or remove anything?" Keep working while you wait. Don't
ask about individual items' brand, finish or variant: build your best guess and let the renders
draw corrections (lesson 6).

## Phase 4: room by room, or parallel first pass?

Ask once. **Room by room here**: the full loop per room. **Parallel**: one background agent (or
separate session, where your app can start them) per room, with `reference/room-agent-brief.md`
filled in (headless only, own files only).
Then review, assemble with `house.py`, and run the approval loop here. Only one session drives the
live Blender.

## Phase 5: model each room (as-is) → approval gate per room

`scripts/rooms/<room>.py` on `roomkit.py`: `OUTLINE` (counter-clockwise), `OPENINGS`,
`rk.Frame` per wall, `build_asis()` (current scene only), and `CAMERAS` that each reproduce a
named still, plus `overhead`. Examples: `reference/example_room_living.py` (furniture, a
room-local helper, books as blocks, rough/test/final modes) and `reference/example_room_kitchen.py`
(cabinet runs, appliances, dining set). In `__main__`, build the
neighbours (`_neighbours.build("<room>")`) so doorways show the real next room.

- **Build at the chosen detail level** (lessons 1-2, 9-12). Place items straight from the
  stills and match colours to them. Simplify small things: piles, stacks and rows of blocks
  instead of individual objects.
- Assets: roomkit primitives first (`box`, `obox`, `tube`, `cyl`, `half_disc`, shelving,
  cabinetry, appliances, furniture), then Poly Haven models, then other libraries. `generate_3d`
  costs the user credits: ask first. Rescale every import to the measured size.
- **Before every review, the plausibility check** (lesson 13): render `overhead` and look for
  anything floating, passing through a wall or another object, or blocking a doorway.
- Rough renders (Cycles 64 samples), then `compare.py` still-beside-render for each camera. Send
  those with what changed and what's assumed. Also load the room into live Blender so the user can
  orbit it.
- **On a placement correction, get dense frames first** (lesson 16):
  `blender -b -P scripts/extract_range.py -- <video> frames/<room>_more <first> <last> 20`,
  contact-sheet them, read them, then edit. Correct the item list and floorplan too if the fix
  touches them.
- As-is only: no remodel ideas until the user approves the room.

## Phase 6: final renders per approved room

`rk.use_cycles(256, exposure)` (best GPU backend found, else CPU; denoised), lights from the room's real fixtures at real
wattage and colour temperature. Daylight only through real openings (`rk.daylight` +
`rk.window_glow` portals). Basements and garages are mostly warm artificial light. **Run a `test`
pass first** (2 cameras, 800×500, 64 samples) and fix exposure and lamp power. Then the finals,
headless in the background: `renders/<room>/final_<cam>.jpg` at 2400×1500. When all rooms are done,
run `house.py` for the whole-level plan and 3/4 views.

Detail pass (when the user asks): real PBR materials (`reference/materials.md`), shape detail on
the items the eye goes to first, the test pass again, then the finals again.

## Learning loop

After a user correction, check whether the same mistake would happen in a *different* house. Most
corrections are this project's details: fix them and move on. If it would recur, follow "How to add
a lesson" at the end of `reference/lessons.md`. Never turn a correction into a new question for
the user (no "ask whether X is painted"); prefer a better default or a code fix. Put fixes in code
where possible: generic helpers go into `scripts/roomkit.py` (no room coordinates or product
names), then copy the improved scripts back into this skill. Live-Blender setup lessons go in the
`blender-mcp-setup` skill.
