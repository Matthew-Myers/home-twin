---
name: scan-capture
description: Coach the user through capturing a home for 3D rebuilding: a room scan with an iPhone/iPad LiDAR app (RoomPlan-based apps, Polycam, or similar) plus walkthrough videos, and the few tape measurements worth taking. Use before scan-to-floorplan when the user hasn't scanned yet, asks how to scan or film their space, or their scan/videos turned out incomplete. Part of the home-project suite.
---

# Scan capture

Help the user gather everything in one visit, so nothing has to be re-shot later. Keep it short:
give the checklist, answer questions, then check what they bring back.

## What to bring back (per level of the home)

1. **One scan of the whole level** as `.usdz`, from a LiDAR iPhone/iPad (Pro models) with a
   RoomPlan-based app or Polycam's room mode. Other formats work if they open in Blender (`.obj`,
   `.glb`), but USDZ room scans give labelled walls, doors and windows.
2. **One walkthrough video per room or area**, landscape or portrait, 1080p is plenty.
3. **A few tape measurements** (optional, they beat any scan): ceiling height, one long wall per
   room, and anything the user cares about getting exact (a cabinet run, a window).

## Scanning tips to pass on

- Lights on, blinds open, doors open. Move slowly, about one step per second.
- Walk the perimeter, pointing at the walls at chest height. Sweep floor-to-ceiling at corners,
  doorways and windows.
- Scan every room of the level in one session if the app allows it (rooms stay aligned).
- Mirrors, glass and black surfaces confuse LiDAR. Note them rather than fighting them.
- Stairs and odd built-ins often come out wrong. The videos cover them.

## Filming checklist (per room)

- Start in the doorway, then a slow 360° turn from the middle of the room.
- Walk each wall in order, keeping the camera level at about chest height and pausing on each
  piece of furniture, built-in and fixture.
- Point up once (ceiling, lights, beams) and down once (floor finish, rugs).
- Film through each doorway into the next room, so the rooms can be connected.
- Name the files by room if convenient (`kitchen.mp4`); otherwise the order is worked out later.
- Nothing needs tidying: the rebuild has detail presets (bare / shelves cleared / decluttered / as-is).

## When the files arrive

Hand over to **home-project** (set up or resume the project, files into `source/scan` and
`source/video`), then **scan-to-floorplan**. If, while reading them, a room turns out to be
missing from both scan and video, ask for just that room, with its checklist above.

## Privacy

Scans and videos show the inside of someone's home. Keep them in the project folder, never upload
them anywhere, and never commit them to a public repository (the suite's `.gitignore` excludes them).
