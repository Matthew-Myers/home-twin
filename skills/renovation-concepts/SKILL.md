---
name: renovation-concepts
description: Design 2-3 remodel options for rooms already modelled as they are today, as changes on top of the as-is model (finishes, fixtures, furniture, cabinets, or moved walls and openings), checked against clearance rules, and render each from the same cameras as the room so before and after compare directly, on labelled comparison boards. Use when the user wants renovation ideas, a remodel concept, "what would it look like with...", new cabinets, paint, flooring, lighting or layout options for a room they have scanned and rebuilt. Part of the home-project suite; runs after room-rebuild.
---

# Renovation concepts

From an approved room to a chosen concept, shown as before/after from the same cameras.

**Before you start:** each room you design for must be `approved` or `final` in
`project.py -- status` (otherwise run room-rebuild first: the as-is model is the baseline, and a
wrong baseline makes every concept wrong). Read `../home-project/reference/lessons.md` (its
principles apply here too) and `reference/design-rules.md`. Commands run from the project folder.

**The rule that makes this work:** a concept is a *change list* applied to the room module, never a
copy of it. `scripts/concepts/<room>_<id>.py` loads the room module, builds it as it is, removes,
repaints and adds, then renders through the room's own `CAMERAS`, lighting and exposure
(`scripts/conceptkit.py`). The room module and the geometry in `project.json` stay as-is. The
same command with `before` renders the unchanged room at the same settings, so only the concept
differs between the two images.

## 1. Design brief (once per project; per room only if it differs)

Ask with one AskUserQuestion round:
- **Scope.** **Refresh**: paint, hardware, lighting, furniture and decor. **Update**: also cabinet
  fronts, counters, flooring, fixtures. **Rework**: walls, openings, layout and plumbing can move.
  **Show me a range**: one concept at each level.
- **Style**: three directions that suit the house as filmed, plus "surprise me".

Then one plain message asking for whatever helps and isn't visible in the videos: who uses the room
and how, what bothers them about it, what must stay, a budget band, inspiration photos or links.
Don't ask more; infer the rest from the stills. Record the answers in `project.json` `brief`
(`scope`, `style`, `budget`, `goals`, `keep`, `notes`). Things the user fixes in place are hard
constraints; everything else is open.

## 2. Propose before building

For each room, 2-3 concepts in writing:
- a short title;
- the scope;
- the idea in one line;
- what changes and what stays;
- **the numbers**: clearances, aisle widths and counter run lengths, taken from the model
  (`ck.extent` / `ck.clearance`) or from the outline, against `reference/design-rules.md`.

Make the concepts genuinely different: span the scope range, or answer a disagreement in the
household ("one with the island, one without"). Say which numbers are code, which are guidelines
and which are taste. When a concept needs a wall to move, say so: it may be load-bearing and need a
beam, permits and a pro. Ask the user to name any must-have product (fixture, appliance, furniture)
and give a link or dimensions *now*, because a guessed size costs rounds later. Then build all of
them unless the user trims the list.

## 3. Build each concept

Copy `reference/example_concept_kitchen_bright.py` (a refresh: `swap_material`) or
`reference/example_concept_kitchen_nook.py` (an update: remove by name and box, add on the room's
wall frames, a ceiling fixture, a clearance check). Fill in `INFO`: it is written to
`rooms.<room>.concepts.<id>` on every run.

- **Find the names first:**
  `blender -b -P scripts/conceptkit.py -- list <room> [pattern]` lists every object with its centre
  and materials. Room modules reuse names along every wall, so target with a name pattern **plus a
  `box`**. A pattern that matches nothing stops the script, so a stale name can't leave the old
  item in the render.
- **Finishes:** `ck.swap_material(old, new)` repaints everything that shares a material (all
  cabinets, the floor) in one line. Use `ck.recolor` for single items. Use real PBR materials
  from `../room-rebuild/reference/materials.md` for anything the eye lands on.
- **New pieces:** build with roomkit on the room's own frames (`room.F_S`, ...). Wrap the call in
  `ck.add("<room>_", ...)`. Use the prefix `"ceiling_"` for ceiling fixtures and beams, so they hide
  in overhead views. Model real products from their listed dimensions, and label real sizes in the
  write-up.
- **Walls and openings (rework):** remove the room's `<room>_wall<edge>_*` pieces in a box and
  rebuild the new run with `Frame.box`. Add `rk.beam` where a wall carried load. When a concept
  opens into the next room, give it `extra_cameras` that look through the new opening. Don't
  change `project.json` geometry: that records the house as it is.
- **Light level:** when a concept swaps fixtures, keep the room's total light comparable (an open
  flush mount lights far more than a shaded pendant at the same wattage). Otherwise "after" just
  looks over-exposed. Raise it only when more light is the point of the concept.
- **Plausibility check** before every review: run `-- overhead` and look for anything floating,
  intersecting, or blocking a door swing or walkway.

## 4. Review: boards, then pick

- Render the room once with `blender -b -P scripts/concepts/<room>_<id>.py -- test before`.
  This gives `renders/<room>/concepts/before/`.
- Render each concept with `-- test`.
- Build the boards with `blender -b -P scripts/board.py -- <room> test`. This writes
  `board_test_<cam>.jpg`: before plus every concept that isn't rejected, labelled, one board per camera.

Send the boards with, for each concept, a bullet list: what changed, the clearances, and what's
assumed. Number or name things so the user can answer in a word ("leaning nook, with bright's
floor"). Mixing is normal: build the mix as a new concept that copies the two change functions.
Record the outcome with `pj.set_concept(room, id, status="shortlisted"|"rejected")`.

**Refine in small rounds:** once a direction is chosen, iterate one element at a time. Make 2-3
variants of that element (`<id>_shelf_black`, `<id>_shelf_brass`, ...), put them on one board, and
end with one question. Short answers are normal, and silence on an open point means it's fine.
If the user asks for contrast, offer contrast: several small elements often beat one big one.

In live Blender, open `renders/<room>/concepts/<id>/<room>_<id>.blend` so the user can orbit it.
Write any live tweak back into the concept module, because the next run overwrites the scene.

## 5. Finals for the chosen concept

- Set `pj.set_concept(room, id, status="chosen")`.
- Render the concept with `-- final` and the room with `-- final before`. These use the same
  cameras and settings, at 256 samples and 2400×1500.
- Build the before/after pair with `board.py -- <room> final <id>`.
- If the user wants an evening variant, pass `lighting=` to `ck.run` with a dimmer sky and the
  lamps on.

Then offer the next steps:
- Quantities and a rough cost range: label it as an estimate with contingency, not a quote.
- Dimensioned plans and wall views for a contractor: these come in the planned renovation-docs
  skill. Until then, give the key dimensions in text.
- Product-fit: swap in real products as the user buys them, and update the renders to match.
