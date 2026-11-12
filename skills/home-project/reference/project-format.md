# project.json, format 1

One file per project (one level of a home), at `<project>/project.json`. Written by the suite's
skills through `scripts/project.py`; safe to read and edit by hand. Example: `example-project.json`.

```jsonc
{
  "format": 1,
  "name": "basement",                       // the level
  "coords": "metres from the level's south-west corner; x east, y north, z = 0 at the floor",
  "scan": {
    "file": "source/scan/basement.usdz",    // relative to the project folder
    "k": 10,                                // import scale: Blender units x k = metres (scan_io)
    "footprint_m": [7.44, 17.68]            // as confirmed by the user
  },
  "videos": [{"file": "source/video/walk-1.mp4", "rooms": ["garage"]}],
  "level": {
    "ceiling": 2.13,                        // typical ceiling, m
    "script": "scripts/level.py",
    "status": "draft"                       // draft | approved (only the user approves)
  },
  "rooms": {
    "garage": {
      "outline": [[0.28, 0.28], [7.19, 0.28], ...],  // interior wall faces, COUNTER-CLOCKWISE
      "ceiling": 2.13,
      "openings": {                         // per outline edge i (corner i -> corner i+1)
        "0": [[0.32, 2.97, 0.0, 2.04]]      // [start, end, bottom, top]; start/end along the edge
      },                                    // bottom > 0 = window, bottom = 0 = door / opening
      "frames": "frames/garage",            // stills for this room
      "detail": "decluttered",              // bare | shelves cleared | decluttered | as-is
      "items": ["steel shelving x3 (48 in)", "tool chest"],   // the approved item list
      "module": "scripts/rooms/garage.py",  // build_asis() + CAMERAS
      "status": "planned",                  // planned | modelled | approved | final
      "notes": "free text: what's assumed, what the user corrected"
    }
  },
  "history": [{"date": "2026-11-12", "skill": "scan-to-floorplan", "event": "level -> approved"}]
}
```

## Rules

- Geometry lives here only. `level.py` and room modules call `pj.geometry(room)`; a correction to a
  wall or opening is made here once and every script picks it up.
- Walls are built outward 0.12 m from the interior faces (`rk.shell`), so two rooms sharing a wall
  have outlines 0.12 m apart.
- `status` moves forward only when its condition is met: `modelled` when the module renders,
  `approved` on the user's word, `final` when the final renders exist. Going back (the user reopens
  a room) is fine: set it and log why.
- `history` is append-only; `project.py` adds entries on status changes.
- Later suite skills add their own keys (e.g. `rooms.<room>.concepts`) without changing these.
