# Registering the blender MCP server in Claude Code

Package: `blender-mcp` was renamed **mcp-for-blender** (https://github.com/ahujasid/mcp-for-blender).
The old name still installs a compatibility shim.

## Standard

Needs `uv` (`winget install astral-sh.uv`, `brew install uv`).

```
claude mcp add blender --scope user -e DISABLE_TELEMETRY=true -- uvx mcp-for-blender
```

## Windows: "Connection closed" right after start

Smart App Control / Application Control blocks the unsigned `.exe` launcher uv generates
(os error 4551). Claude only sees "Connection closed". Start the package through `python -c`
instead, so no generated .exe runs. Working `~/.claude.json` entry (`.mcpServers.blender`):

```json
{"type":"stdio",
 "command":"C:\\Users\\<user>\\AppData\\Local\\Microsoft\\WinGet\\Packages\\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\\uvx.exe",
 "args":["--from","blender-mcp","python","-c","from blender_mcp_shim import main; main()"],
 "env":{"DISABLE_TELEMETRY":"true"}}
```

For `mcp-for-blender`, use `--from mcp-for-blender python -c "from <module> import main; main()"`
with the module the package's entry point names (`importlib.metadata.entry_points()`).
Use the full path to `uvx.exe` if it isn't on the PATH Claude sees. Back up `~/.claude.json`
before editing it by hand.

## Check it outside Claude

Spawn the exact command, send an MCP `initialize`, and expect about 9 tools in `tools/list`.

## After registering

MCP tools load only when a session starts. The user starts a new session, or reconnects via
`/mcp` in a terminal `claude`. Reconnecting from inside the running session did not work.
