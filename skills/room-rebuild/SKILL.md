---
name: room-rebuild
description: Model the rooms of an approved floorplan as they are today, matched to walkthrough-video stills at a chosen detail level (bare, shelves cleared, decluttered, as-is), then produce high-quality lit renders per room and of the whole level in Blender. Use after scan-to-floorplan, or when the user wants their rooms or furniture recreated in 3D or rendered (also the starting point for renovation concepts). Part of the home-project suite.
---

# Room rebuild

From an approved floorplan to approved, lit models of each room as it is today. Each room ends at
the user's approval.

**Before you start:** `project.py -- status` must show the level `approved` (otherwise run
scan-to-floorplan). Read `../home-project/reference/lessons.md`: the principles there override
habits, especially aim, asking and detail level. Technical traps: `../home-project/reference/gotchas.md`;
texture recipes: `reference/materials.md`. Commands run from the project folder.

## 1. Detail level + item list

Usually the detail level was already asked with the floorplan approval (scan-to-floorplan step 5).
If not, ask once with AskUserQuestion (lessons 9-12). The user can override it per room:
- **bare**: shell, structure and fixed installations only.
- **shelves cleared**: plus furniture, shelving and desks, all empty.
- **decluttered** (default, recommended): plus the things that belong on them (computers,
  appliances, books, plants, lamps); no mess; tidy and rearrange rather than delete.
- **as-is**: everything, simplified (piles as piles, loose papers stacked).

Then per room, a short list of the main items with approximate sizes (metric and imperial). Group
small things ("books on the bookshelf", "tools on the pegboard"). Don't hold up the work for it:
send the list **with the first renders** and ask "add or remove anything?" there. Don't ask about
individual items' brand, finish or variant: build your best guess and let the renders draw
corrections (lesson 6). Record `detail` and `items` per room in `project.json`.

## 2. Room by room, or parallel first pass?

Don't ask; decide. With more than three rooms, or when the user wants few questions, go
**parallel**: one background agent per room (or a separate session, where your app can start
them), each with `reference/room-agent-brief.md` filled in (headless only, own files only). Then
review, assemble with `house.py`, and run the approval loop here. With three rooms or fewer, go
**room by room** here: the full loop per room. Only one session drives the live Blender.

**Decide shared things before the agents start**, and put them in each brief:
- **Shared walls:** every room calls `rk.shell(..., shared=True, perimeter=pj.perimeter())`. Each
  room builds its half of a shared wall, so two paint colours don't z-fight.
- **Door leaves:** each leaf is built by one room only: the room it swings into. A closet's doors
  belong to the room the closet opens from. Use `rk.door_leaf`, `rk.bypass_doors` and
  `rk.closet_fit`.
- **Shared materials** (floor, trim, door stain) go in one module that every room imports, e.g.
  `scripts/rooms/_common.py`. Files starting with `_` are not rooms.
- **Closets** (`part_of`) are built by their parent room's module.

## 3. Model each room → approval gate per room

`scripts/rooms/<room>.py` on `roomkit.py`: geometry from `pj.geometry(ROOM)` (never copied
numbers), `rk.Frame` per wall, `build_asis()` (current scene only), and `CAMERAS` that each reproduce
a named still, plus `overhead`. Examples: `reference/example_room_living.py` (furniture, a room-local
helper, books as blocks, rough/test/final modes) and `reference/example_room_kitchen.py` (cabinet
runs, appliances, dining set). In `__main__`, build the neighbours (`_neighbours.build(ROOM)`) so
doorways show the real next room. Record `module`, then status `modelled` once it renders.

- **Build at the chosen detail level** (lessons 1-2, 9-12). Place items straight from the stills
  and match colours to them. Simplify small things: piles, stacks and rows of blocks.
- Assets: roomkit primitives first, then Poly Haven models, then other libraries. `generate_3d`
  costs the user credits: ask first. Rescale every import to the measured size.
- **Before every review, the plausibility check** (lesson 13): render `overhead` and look for
  anything floating, passing through a wall or another object, or blocking a doorway.
- Cameras that reproduce a still render at the still's aspect: phone walkthroughs are usually
  portrait (`frames/videos.txt` says), e.g. 900×1200.
- Rough renders (Cycles 64 samples), then a still-beside-render image per camera:
  `blender -b -P scripts/compare.py -- frames/<room>/<n>.jpg renders/<room>/asis_<cam>.jpg renders/<room>/cmp_<cam>.jpg`.
  Send those with what changed and what's assumed. In live Blender, also load the room so the user
  can orbit it.
- **On a placement correction, get dense frames first** (lesson 16):
  `blender -b -P scripts/extract_range.py -- <video> frames/<room>_more <first> <last> 20`,
  contact-sheet them, read them, then edit. If the fix moves a wall or opening, change
  `project.json` (and re-render the floorplan), not the room module.
- As-is only: no remodel ideas until the user approves the room. On approval: status `approved`.

## 4. Final renders per approved room

`rk.use_cycles(256, exposure)` (best GPU backend found, else CPU; denoised). Light from the room's
real fixtures at real wattage and colour temperature. Daylight only through real openings
(`rk.daylight` + `rk.window_glow` portals). Basements and garages are mostly warm artificial light.
**Run a `test` pass first** (`-- final test`: 2 cameras, 800×500, 64 samples) and fix exposure and
lamp power. **One exposure target for the whole level:** put every room's test renders on one
sheet (copy them into a folder, then `contact_sheet.py`) and even out the rooms against each other,
not each room on its own. Dim evening video pulls a room dark, and a level of rooms tuned one by
one ends up anywhere from -0.6 to +2.3. Then the finals, headless in the background (`-- final`):
`renders/<room>/final_<cam>.jpg` at 2400×1500. Status `final`. When all rooms are done, run
`blender -b -P scripts/house.py` for the whole-level plan and 3/4 views.

Detail pass (when the user asks): real PBR materials (`reference/materials.md`), shape detail on the
items the eye goes to first, the test pass again, then the finals again.
