---
name: blender-mcp-setup
description: Get Claude driving the user's live Blender window over the blender MCP server (mcp-for-blender), and prove it works. Use before any task that needs live Blender control (execute_blender_code, look, Poly Haven import), when blender MCP tools are missing or fail with "Could not connect to Blender" / "Connection closed", or when the user can't find the Blender add-on or its Connect button. Falls back to headless Blender when the live link can't be made to work.
---

# Blender MCP setup

Goal: the `mcp__blender__*` tools drive **the Blender window the user is looking at**, proven by a
visible change. Work down the checklist; stop at the first step that already passes.

## 1. Blender installed?

Look for `C:\Program Files\Blender Foundation\Blender *\blender.exe` (Windows),
`/Applications/Blender.app/Contents/MacOS/Blender` (macOS), or `blender` on PATH / snap / flatpak
(Linux). If missing, ask the user to install the current LTS from blender.org (or their package
manager, e.g. `winget install BlenderFoundation.Blender`). Don't download installers yourself.

## 2. MCP server registered in Claude?

If no `mcp__blender__*` tools exist (check with ToolSearch "blender"; they may still be connecting),
register the server. Installed as part of the home-twin plugin, it is already declared in the
plugin's `.mcp.json` and needs only `uv` on PATH and a restart. See `reference/server-registration.md` (uv, the Windows Smart App Control
workaround, telemetry off). MCP tools load only when a session starts, so the user must start a new
session afterwards.

## 3. Add-on installed and connected?

`get_addon_status`. If it reports "Could not connect to Blender":

- Is Blender running and listening on port 9876? Windows: `Get-Process blender`,
  `Test-NetConnection localhost -Port 9876`. macOS/Linux: `pgrep -l blender`, `nc -z localhost 9876`.
- Is the add-on installed? Headless check:
  `blender -b --python-expr "import addon_utils; print([m.__name__ for m in addon_utils.modules() if 'MCP' in m.bl_info.get('name','')])"`.
  If not, install it headless (the user doesn't have to click through Preferences):
  `blender -b --python-expr "import bpy; bpy.ops.preferences.addon_install(filepath=r'<addon.py>', overwrite=True); bpy.ops.preferences.addon_enable(module='addon'); bpy.ops.wm.save_userpref()"`
  using `addon.py` from the mcp-for-blender repo (https://github.com/ahujasid/mcp-for-blender), at the
  release that matches the server version. Ask the user before downloading it, save it to a new
  empty folder, and skim it first (grep telemetry, bind, subprocess, api_key): it must listen on
  localhost only.
- **Fastest fix, no menus:** launch a Blender window that enables the add-on and starts the server:
  `Start-Process "<blender.exe>" -ArgumentList '--python', '<this skill>\scripts\start_blender_mcp.py'`.
  (macOS/Linux: `"<blender>" --python <this skill>/scripts/start_blender_mcp.py &`.) It logs to
  `blender_mcp_start.log` in the system temp folder. Tell the user to use that new window.
- If you walk the user through the UI instead, read the add-on's real tab and button names from the
  installed file (`bl_category` and the operator labels in the add-on's `addon.py`, under Blender's
  user scripts folder: `bpy.utils.user_resource('SCRIPTS', path='addons')`).
  They change between versions ("BlenderMCP" became "MCP for Blender" / "Connect to MCP server").
  After one failed round of menu directions, use the launcher instead.

## 4. Prove it drives the visible window

`execute_blender_code` adds a bright red cube at the origin and switches the viewport to material
shading. `look` at it, ask the user "Do you see a red cube?", and delete it after they confirm.
Tools can "work" against a background instance while the user's screen doesn't change, so never
assume.

## 5. Fallback

If the live link can't be made to work, run everything headless (`blender -b -P script.py -- args`)
and show the user rendered images. Say so plainly.

## Rules once connected

- Scripts that run in live Blender must not call `bpy.ops.wm.read_factory_settings()`: it unloads
  the add-on and drops the connection. Clear data blocks instead (guard with `bpy.app.background`).
- Long Cycles renders over MCP freeze the user's UI and can time the tool call out. Render
  headless in the background and load or show the result.
- `view3d.view_all` frames everything, including huge ground planes. Set
  `region_3d.view_location / view_distance / view_rotation` to frame the subject.
- Look shader nodes up by type (`n.type == "BSDF_PRINCIPLED"`), not by name: names are localised.
- Asset libraries are off until enabled: `scene.blendermcp_use_polyhaven = True`. Leave the paid
  3D generators off unless the user opts in.
- Turn telemetry off (`DISABLE_TELEMETRY=true` in the server env, and `disable_telemetry` if offered).
