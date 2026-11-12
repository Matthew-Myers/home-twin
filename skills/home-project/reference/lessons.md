# Lessons: general principles

Short on purpose. These apply to any home. They are not a checklist of things that went wrong in
one house. Technical facts (file formats, OS, Blender API) are in `gotchas.md`; texture recipes
are in `materials.md`.

## Aim

1. **Recognisable, not perfect.** The goal is a model the user looks at and says "yes, that's
   my room". Big shapes, positions, colours and light matter. Small objects and exact product
   details mostly don't. Stop iterating once it reads right, and spend effort where the eye goes
   first.
2. **Be efficient.** Simplify anything the chosen detail level doesn't need: a pile is one
   shape, loose papers become one stack, a shelf of books is a row of blocks. Reuse helpers and
   assets rather than modelling each thing from scratch.

## Evidence

3. **The stills are the inventory; the scan is the floor plan.** The scan gives good walls and
   room sizes but misses or mangles things it has no category for (structure, built-ins, open
   storage, stairs, small wall jogs). Walk the stills for anything that shapes the space and is
   missing from the model.
4. **Don't invent.** Leave out anything you can't see in a still or the scan, even if the room
   would look more "finished" with it.
5. **Scan for size, stills for what and where, the user's word over both.**

## Asking

6. **Default to your best guess; don't quiz the user about objects.** Estimate type, size and
   finish from the stills and common sizes, build it, and let the renders show your guess. The
   user corrects what matters to them. Ask only about things that change the layout (stair
   direction, a missing wall or opening) or that you truly can't read from any still.
7. **Batch questions.** At most one short list per gate, each item with the still that shows it.
   Keep working while you wait.
8. **Use what the user volunteers.** Use measurements, product links and photos as soon as they
   arrive. Don't go asking for them item by item.

## Detail level (the user picks one preset at the start; default "decluttered")

9. **bare**: the shell only. Walls, floors, ceilings, doors, windows, stairs, structure, and
   fixed installations: built-in cabinets and counters, plumbing fixtures, mechanicals, installed
   appliances. No movable furniture.
10. **shelves cleared**: bare plus all furniture, shelving, desks and tables, with every surface
    and shelf empty.
11. **decluttered**: shelves cleared plus the things that belong there: computers, monitors,
    lamps, microwaves and countertop appliances, books on bookshelves, plants, art, rugs, tools
    on their pegboard. Leave out transient mess: toys on the floor, blankets, garbage, dirty
    clothes, dishes. When in doubt, tidy and rearrange rather than delete.
12. **as-is**: everything that's there, simplified. A garbage pile is one pile, scattered
    notebooks are one stack, a heap of clothes is one soft lump. Don't model every wrapper.
    Same efficiency rule as 2.

## Plausibility (check before every review)

13. **Everything is supported and nothing passes through anything.** Feet on the floor, items
    stop at the wall plane, and no object crosses a doorway. One overhead render plus one side
    look catches most of these.

## Process

14. **Build in 3D, derive every view.** Plans and comparisons are renders of the one scene.
15. **Review means each still beside its render** from the same viewpoint, plus a line on what
    changed and what's assumed.
16. **On a placement correction, look at more frames around that spot before editing.**
17. **Honour exact numbers** the user gives.
18. **As-is first.** No remodel ideas until the user approves the room.

## Rendering

19. **Test pass before finals**: low resolution and low samples, two cameras.
20. **Light from the real fixtures**; daylight only through real openings.
21. **Textures at real-world scale.** Hide ceilings in top views, and build the neighbouring rooms
    so doorways don't show a void.

## Communication

22. Give sizes in metric and imperial. Users approve tersely, so take "looks good" as approval.

## How to add a lesson

Add a lesson only when a mistake would happen again in a *different* house.
- Never add questions to ask, or facts about one house, product, material or finish. Those are
  this project's details, not lessons.
- If an existing principle covers it, sharpen that principle's wording, or fix the code,
  instead of adding a line.
- Write it in general words, with at most one short example.
- Technical facts go in `gotchas.md`.
- Keep this file under ~25 principles.
