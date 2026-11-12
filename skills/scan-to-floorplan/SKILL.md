---
name: scan-to-floorplan
description: Turn an iPhone RoomPlan / Polycam USDZ scan plus walkthrough videos of one level of a home into clean room outlines, openings and an approved floorplan render (plan + 3/4 cutaway) in Blender. Use when the user hands over a .usdz scan and/or room videos and wants a floorplan or measured layout, or as the first build step before room-rebuild. Part of the home-project suite.
---

# Scan to floorplan

From the scan and videos to an approved floorplan, with every room's outline and openings saved in
`project.json`. Ends at the user's approval.

**Before you start:** the project must exist (home-project skill: `project.py -- init`). Read
`../home-project/reference/lessons.md` (principles) and `../home-project/reference/gotchas.md`
(USDZ and video traps). For a live Blender window, run the blender-mcp-setup skill first. Without
one, everything works headless. Commands run from the project folder. `blender` means the full path to
the Blender executable.

## 1. Read the scan

```
blender -b -P scripts/inspect_scan.py      object list, bounds, overview PNGs
blender -b -P scripts/catalogue.py         every scanned object: kind, size, plan position
blender -b -P scripts/plan_view.py         top-down plan with a 1 m grid (add "NAME:x:y" labels later)
```

- Check the scale line (`scan_io: ... -> K = 10`) and confirm the footprint with the user, in metres
  and feet. Record `scan.file`, `scan.k`, `scan.footprint_m` in `project.json`.

## 2. Read the videos

```
blender -b -P scripts/extract_one.py -- source/video/<video> frames/<name> 30
blender -b -P scripts/contact_sheet.py -- frames/<name> frames/sheet-<name>.jpg
```

- Read one contact sheet per video. Work out which room each video shows, rename the frames folders
  by room, and record `videos[].rooms` and `rooms.<room>.frames`.
- Per room, note what's on each wall in video order, with frame numbers.
- **Inventory from the stills, not the scan** (lessons 3-4): note what shapes the space but is missing
  from the scan or wrong in it (structure, stairs, built-ins, open storage, openings). List nothing
  that isn't in a still.

## 3. Rooms into project.json

Per room: `blender -b -P scripts/room_survey.py -- x0 y0 x1 y1` lists walls, openings and items in a
plan box. From it, write each room's counter-clockwise interior `outline`, `openings` per edge
(`[start, end, bottom, top]` along the edge from its first corner), and `ceiling` into
`project.json` (format: `../home-project/reference/project-format.md`). Use the survey's walls,
not the scan's zero-thickness panels. Run `project.py -- status` to check orientation and that
openings fit their walls.

## 4. The level script and renders

`scripts/level.py` builds every room from `project.json` with `rk.shell()` (walls built outward
0.12 m from the interior faces), a window in every opening that starts above the floor, stairs
rebuilt procedurally, everything from the step 2 inventory that shapes the space (structure, big
storage), and scanned items as labelled blocks. It renders:

- `renders/level_plan.jpg`: orthographic, north up, room names and sizes in m and ft-in;
- `renders/level_cutaway.jpg`: 3/4 view, walls cut at ~1.5 m, structure exempt from the cut.

Start from `reference/example_level.py` (a two-room demo level). Look at both renders before
showing them.

## 5. Approval gate

Show both renders with at most one short batch of layout questions (stair direction, an opening or
wall you can't read), each with the still that shows it. **Stop: "Does the floorplan look right?"**
Fix `project.json` / `level.py` and re-render until approved. Then
`pj.set_status("level", "approved")` (or edit the file) and set each room to `planned`.

Next: **room-rebuild**.
