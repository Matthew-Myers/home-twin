# start_blender_mcp.py - open Blender (GUI) with the MCP add-on enabled and its server started.
# Run (Windows):  Start-Process "<blender.exe>" -ArgumentList '--python', '<this file>'
#      (macOS/Linux): "<blender>" --python <this file> &
# Logs to <temp>/blender_mcp_start.log (add-on errors included). Works with any add-on whose
# bl_info name contains "MCP" and that registers bpy.ops.blendermcp.start_server.
import bpy, os, tempfile, traceback, addon_utils

LOG = os.path.join(tempfile.gettempdir(), "blender_mcp_start.log")

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

open(LOG, "w").close()
mods = {m.__name__: m for m in addon_utils.modules()}
name = next((n for n, m in mods.items() if "MCP" in m.bl_info.get("name", "")), None)
log(f"add-on module: {name}")
if name is None:
    log("no MCP add-on installed: install it first (see SKILL.md step 3)")
else:
    try:
        loaded, enabled = addon_utils.check(name)
        log(f"before: loaded={loaded} enabled={enabled}")
        if not loaded:
            addon_utils.enable(name, default_set=True,
                               handle_error=lambda e: log("enable error: " + "".join(traceback.format_exception(e))))
        log(f"after: {addon_utils.check(name)}  panel registered: {hasattr(bpy.types, 'BLENDERMCP_PT_Panel')}")
    except Exception:
        log(traceback.format_exc())

def start():
    try:
        bpy.ops.blendermcp.start_server()
        log(f"server running: {bpy.context.scene.blendermcp_server_running}")
    except Exception:
        log("start error: " + traceback.format_exc())
    return None

bpy.app.timers.register(start, first_interval=3.0)
