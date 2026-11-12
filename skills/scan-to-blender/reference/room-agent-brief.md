# Room agent brief (template — fill the <...> and paste as a parallel agent's prompt)

Goal: a recognisable 3D model of the <ROOM> of the user's <LEVEL> as it is today, at detail level
**<bare | shelves cleared | decluttered | as-is>** (defined in lessons.md, 9-12), built with
this project's Blender toolkit so the whole level can later be assembled into one render. Aim for
"yes, that's my room", not perfection; simplify small things.

Project: `<PROJECT PATH>`
- `scripts/roomkit.py`: the toolkit (READ IT). Do NOT edit it; other agents run in parallel. Put
  new helpers (sofa, toilet, vanity, railing, piano, ...) in your own room module.
- `<finished room module(s), if any>`: examples of a room module at the expected quality. Read them.
- `scripts/room_survey.py -- <x0 y0 x1 y1>`: every scanned element in your room's plan box:
  `"<blender>" -b -P scripts/room_survey.py -- <x0> <y0> <x1> <y1>`
- `frames/<room>/00.jpg ...`: stills from `source/video/<video>`. For dense frames around a spot, run
  `scripts/extract_range.py -- "<video>" frames/<room>_more <first> <last> 20`.
- `<skill>/reference/lessons.md`: the principles every room must meet, including the detail
  presets. Read it.
- `assets/polyhaven/`: CC0 textures/HDRIs/models. Add what you need with a copy of fetch_polyhaven.py.

APPROVED ITEM LIST (build these at the detail level above; use best guesses for type, size and
finish, and note doubts in your report rather than asking):
<list from Phase 3>

Conventions (must match so rooms assemble):
- Plan metres from the level's south-west corner: x east, y north, z = 0 at the floor, ceiling <H>.
- Outline counter-clockwise; `rk.Frame(p0, p1)` puts the room on the left, u along the wall, v into it.
- `rk.shell(outline, CEILING, openings, wall_m, floor_m, ceiling_m, base_m=trim)` builds walls
  OUTWARD 0.12 m from the interior faces. Openings per edge: `(start, end, bottom, top)` from the
  edge's first corner.
- Name the ceiling `ceiling_<room>`; anything else hidden in overhead views starts with `ceiling_`.

Deliverable: `scripts/rooms/<room>.py` with
- `build_asis()`: builds into the CURRENT scene only (no reset, world, camera or render).
- `CAMERAS = {name: (eye, target, lens)}`: 2-3 eye-level views, each reproducing a named still,
  plus `overhead` (cutaway, ceiling hidden).
- `if __name__ == "__main__":` reset, `rk.use_cycles(256, <exposure>)`, world/lights for the space,
  build, render each camera to `renders/<room>/asis_<cam>.jpg`, save `renders/<room>/<room>_asis.blend`.
  Run headless: `"<blender>" -b -P scripts/rooms/<room>.py`

Rules:
- Headless Blender ONLY. Never use the blender MCP tools or the user's open Blender window.
- Only create or edit files for your room: `scripts/rooms/<room>.py`, `renders/<room>/`, `frames/<room>_more/`.
- Follow the detail level exactly. Match colours and materials to the stills. Simplify small
  things: piles, stacks and rows of blocks.
- Render, LOOK at every image (Read tool), compare with the stills (`scripts/compare.py`), fix, and
  repeat until it reads right. Before reporting, render `overhead` and check nothing floats, nothing
  passes through a wall, and nothing blocks a doorway.
- Report back briefly: what you built, which still each camera and placement matches, assumptions,
  and file paths.
