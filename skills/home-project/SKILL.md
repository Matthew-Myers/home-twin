---
name: home-project
description: Start, resume or check a home 3D project (one level of a house from a room scan and walkthrough videos) and route to the right skill of the suite (scan-capture, scan-to-floorplan, room-rebuild). Owns project.json, the shared geometry and progress file, the shared Blender toolkit (roomkit) and the principles every phase follows. Use when the user starts a home scan / floorplan / room-model / renovation project, asks "where are we" on one, or another suite skill needs the project set up.
---

# Home project

One project = one level of a home (a floor, a basement). Everything for it lives in one folder,
and `project.json` in that folder holds the geometry and how far each room has got. Every skill of
the suite reads and writes it, so work can stop and resume in a later session.

## The suite

| Skill | Does | Needs |
|---|---|---|
| **scan-capture** | How to scan and film the space (before anything else) | nothing |
| **scan-to-floorplan** | Scan + videos → rooms, openings, floorplan render, approved | a scan |
| **room-rebuild** | Approved floorplan → room models at a detail level → lit renders | level approved |
| **blender-mcp-setup** | Live Blender window for any of the above (optional) | Blender |

## Start or resume

1. **Find or make the project folder.** Ask where it should live if the user hasn't said. Never
   work from Downloads: copy the user's files into it.
2. **New project:**
   `blender -b -P <this skill>/scripts/project.py -- init <project dir> <level name>`
   creates the folders (`source/scan`, `source/video`, `frames`, `scripts/rooms`, `renders`,
   `assets`), a blank `project.json`, and copies the suite's scripts into `<project>/scripts/`.
   (Any Python 3.8+ works too: `python <this skill>/scripts/project.py init ...`.)
3. **Existing project:** `... project.py -- status <project dir>` prints the level and each room's
   state, the checks (outline orientation, openings inside their walls) and the next skill to use.
   After a suite update, `... project.py -- sync <project dir>` re-copies the suite scripts. It never
   touches `level.py` or room modules.
4. Hand over to the skill `status` names, or to the one the user asked for.

## project.json

Format and fields: `reference/project-format.md`; a filled example: `reference/example-project.json`.
The essentials:

- **Coordinates:** plan metres from the level's south-west corner, x east, y north, z = 0 at the
  floor. Every script and room uses them, so rooms stack into one scene.
- **Rooms:** counter-clockwise interior `outline`, `openings` per edge as `[start, end, bottom, top]`
  measured along the edge from its first corner, `ceiling`, `detail`, `items`, `module`, `status`.
- **Status:** level `draft → approved`; room `planned → modelled → approved → final`. Only the user's
  approval moves a level or room to `approved`. Skills check status before starting
  (`pj.require("kitchen", "approved")`).
- Blender scripts read geometry with `pj.geometry(room)`; never copy outline numbers into a script.

## Shared toolkit and principles

- `scripts/roomkit.py`: building blocks (walls, openings, cabinets, appliances, furniture, lights,
  cameras, Cycles setup). `scripts/project.py`: the project file. Image and video helpers:
  `extract_one.py`, `extract_range.py`, `contact_sheet.py`, `compare.py`. Assets:
  `fetch_polyhaven.py`. All run inside Blender (`blender -b -P scripts/<x>.py -- args`).
- `reference/lessons.md`: the principles every phase follows. Read it before working on a project.
- `reference/gotchas.md`: technical facts (USDZ import, video, platforms, Blender).

## Learning loop (all suite skills)

After a user correction, ask whether the same mistake would happen in a *different* home. Most
corrections are this project's details: fix them and move on. If it would recur, follow "How to add
a lesson" in `reference/lessons.md`. Never turn a correction into a new question for the user;
prefer a better default or a code fix. Generic code fixes go into the suite's `scripts/` (no room
coordinates or product names), then `project.py sync`.
