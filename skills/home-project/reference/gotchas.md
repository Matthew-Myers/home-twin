# Technical gotchas (facts, not judgement)

## RoomPlan / Polycam USDZ import
- Imports at 1/10 scale → `scan_io.scale_k()` detects K = 10. Confirm the printed footprint with the user.
- Origin at mid-height → re-base so floor z = 0. The scan's floor surface sits ~0.04 m above its lowest geometry.
- Warning floods ("UV attribute primvars:st count inconsistent", "MaterialBindingAPI") are harmless; filter them from logs.
- Object prefixes: `ExternalWalls`, `InnerSide` (walls), `FloorFillerTop` (a ceiling layer: hide it or the plan goes flat grey), `WholeFloor`, `furniture_<model>_`, `appliances_`, `window*`, `door*`, `l_/r_/t_frame` (opening frames), `structure` (stairs).
- `InnerSide` walls have zero thickness and vanish from above. Survey with `room_survey.py` and rebuild clean walls with `rk.shell()` (built outward from the interior faces).
- Scanned custom normals break once walls are cut → flat-shade or rebuild.
- Wall extensions only at convex corners (`rk.shell` does this), otherwise walls cross inside nooks.
- One floor per room, trimmed to its outline, otherwise floors z-fight.
- RoomPlan skips closets and never captures stairs. A 0.5-0.9 m gap between rooms with a door is a closet. Add it as an inferred room.
- Double detections: a window and a door on the same opening. The frame bottom tells them apart (0 is a door, ~0.9 m is a window). A ~0.3 m "door" is usually a mirror.
- `catalogue.py` skips the opening frames. `room_survey.py` is what shows doors and windows.

## Video
- No ffmpeg needed: Blender's sequencer decodes .mp4/.MOV (`extract_one.py`, `extract_range.py`). Movieclip-based extraction was unreliable.
- The sequencer needs absolute paths. A relative path gives a 0×0 strip (the scripts call abspath).
- Videos not named by room → `video_sheets.py` does every video in one Blender launch (UUID names become v1, v2, ...); read one sheet per video.
- Phone walkthroughs are usually portrait. Render the cameras that reproduce a still at the still's aspect (e.g. 900×1200), so the still-beside-render comparison lines up.

## Platform
- No system Python needed anywhere: downloads, contact sheets and comparisons all run in Blender (`blender -b -P scripts/<x>.py -- ...`).
- Windows: Blender can't open `-P` scripts from very long paths (deep temp folders) → keep scripts in the project folder.
- Windows PowerShell 5.1: `Set-Content` mangles UTF-8 → `[IO.File]::WriteAllText(p, t, (New-Object Text.UTF8Encoding $false))`, or the Write/Edit tools.
- Killing Blender may be refused by the OS or the user's permissions → ask the user to close it.

## Blender / roomkit
- `roomkit.reset()` factory-resets only when `bpy.app.background`. In live Blender it clears data so the MCP add-on stays loaded.
- Several rooms in one scene → duplicate names ("floor.001"): name objects per room or rename after each build.
- Neighbouring rooms' outlines sit 0.12 m apart. Full-thickness walls from both rooms are the same box twice, so two paint colours z-fight → `rk.shell(..., shared=True, perimeter=pj.perimeter())`: each room builds its half, outside walls get an exterior skin.
- `rk.shell` makes the outdoor ground only if none exists yet (one per scene). Lower it below a stair flight with `rk.make_ground(..., z=...)`.
- Plank textures run along image x: on walls they come out horizontal. Vertical boards: `rk.pbr(..., rot3=(0, 90, 0))` on walls along x, `rot3=(90, 0, 0)` on walls along y.
- Point lights show as white dots in glossy reflections → `light.visible_glossy = False`.
- Light leaks through cut-away walls → invisible full-height occluders (`visible_camera = False`).
- EEVEE rough passes render mirrors black → Cycles at 64 samples is a few seconds on a modern GPU.
- Name ceiling-hung objects with a prefix in `house.py`'s `HIDE_FROM_ABOVE` (`ceiling_*`, light names). `rk.flush_light` names its globe `ceiling_flush`.
- Things that must show in cutaways despite being above the cut (beams, posts) → exempt them by name prefix (`KEEP_IN_CUTAWAY` in the level script).
- Render JPEG, not PNG, for anything you look at or send (PNGs run to megabytes).
- Long Cycles renders run headless in the background. The GPU is shared if parallel agents render.
- `rk.use_cycles` picks OptiX, CUDA, HIP, Metal or oneAPI, whichever has a device, else the CPU (it prints which). `RENDER_DEVICE=CPU` or `=CUDA` etc. forces one.
- Live-MCP specifics (add-on, connection, viewport framing): see the `blender-mcp-setup` skill.
