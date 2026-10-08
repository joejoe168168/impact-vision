# Impact Vision Web Interface — Complete Guide

Impact Vision ships a browser chat interface in the style of ChatGPT or
Claude.ai, backed by the *same* agent runtime the CLI uses: same 89 tools,
same skills, same slash commands, same permission model, same IRIS+ / SDG /
ESG framework expertise.

One command starts everything:

```bash
impact-vision serve-web --open
```

Then open <http://127.0.0.1:8787>.

---

## Contents

1. [What you get](#1-what-you-get)
2. [Install and start](#2-install-and-start)
3. [First run — configuring your model](#3-first-run--configuring-your-model)
4. [The interface, part by part](#4-the-interface-part-by-part)
5. [Working with files](#5-working-with-files)
6. [Slash commands](#6-slash-commands)
7. [Permissions and safety](#7-permissions-and-safety)
8. [Keyboard shortcuts](#8-keyboard-shortcuts)
9. [Using the REST API from the same server](#9-using-the-rest-api-from-the-same-server)
10. [Running it for a team](#10-running-it-for-a-team)
11. [Configuration reference](#11-configuration-reference)
12. [Architecture](#12-architecture)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. What you get

`serve-web` mounts four surfaces on a single port:

| URL | What it is |
|---|---|
| `/` | **Chat UI** — streaming conversation, tool cards, file upload, artifacts |
| `/console` | **Tool console** — typed forms for every REST endpoint (the power-user view) |
| `/docs` | **OpenAPI explorer** — try any endpoint from the browser |
| `/api/v1/*` | **REST gateway** — 26 endpoints for scripts and third-party integrations |
| `/ws/chat` | **WebSocket** — the live agent stream the chat UI speaks |

The chat UI is a single self-contained HTML document: no npm, no build step,
no CDN, no external fonts. It ships inside the Python package, so
`pip install` → `serve-web` is the whole setup.

---

## 2. Install and start

```bash
# from a clone
pip install -e .

# start on the default port
impact-vision serve-web

# common variations
impact-vision serve-web --open                 # also open your browser
impact-vision serve-web --port 9000            # different port
impact-vision serve-web --workspace ~/funds/q3 # agent works in that folder
impact-vision serve-web --host 0.0.0.0         # reachable on your LAN (see §10)
impact-vision serve-web --reload               # auto-reload while developing
```

Equivalent manual invocation:

```bash
uvicorn openharness.web.app:app --host 127.0.0.1 --port 8787
```

On startup the CLI prints every mounted surface, the workspace directory and
whether authentication is on:

```
Impact Vision → http://127.0.0.1:8787
  · Chat UI:      http://127.0.0.1:8787/
  · Tool console: http://127.0.0.1:8787/console
  · OpenAPI:      http://127.0.0.1:8787/docs
  · REST API:     http://127.0.0.1:8787/api/v1/*
  · Workspace:    /Users/you/funds/q3
  · Auth:         local only (other sites and hosts are refused)
```

### The workspace matters

The agent reads and writes files relative to the **workspace** — the directory
the server was started in, or whatever `--workspace` points at. Start the
server in the folder holding the pitch decks, data rooms and reports you want
to work on. Uploads land in `<workspace>/.impact-vision/uploads/`, and
downloads are restricted to the workspace subtree.

---

## 3. First run — configuring your model

If you have never run `impact-vision setup`, the first message will come back
with *"No API credentials configured."* Fix it without leaving the browser:

1. Click **Settings** (bottom-left).
2. Pick a **Provider profile**. They are grouped in the picker, and the hosted
   ones come with the base URL and a default model already filled in, so you
   only paste a key:

   | Group | Profiles | Notes |
   |---|---|---|
   | Anthropic Claude | Anthropic-Compatible API, Claude Subscription | Defaults to `claude-sonnet-5-5` |
   | Hosted APIs | OpenAI, OpenRouter, DeepSeek, Alibaba Qwen (DashScope), Google Gemini, Moonshot (Kimi), Mistral, xAI (Grok), Groq, Together AI, NaxtClaude | Each keeps its key in its own slot |
   | Subscriptions | Codex Subscription, GitHub Copilot | OAuth, no key |
   | Local & custom | Ollama (local, no key), Custom endpoint (OpenAI-compatible), OpenAI-Compatible API | Any `localhost` URL needs no key |

   A profile marked **— add key** has no key yet. Instead of pasting one you can
   set the environment variable shown under the key field (for example
   `OPENROUTER_API_KEY` or `DEEPSEEK_API_KEY`) before starting the server.

3. Set the **Model** (the field autocompletes known model IDs).
4. Set the **Base URL** if you are pointing at a non-default endpoint.
5. Paste the **API key** and click **Save provider**.

The key goes into your local credential store (keyring where available,
otherwise an obfuscated file under `~/.openharness/`); the rest is written to
`~/.openharness/settings.json`. The key field is write-only — it is never sent
back to the browser.

**Saved settings apply to new conversations.** Click **New chat** after
changing the provider.

### Examples

**Local model via Ollama**

```
Provider profile : Ollama (local, no key)
Model            : llama3.2        (any model you have pulled)
API format       : openai
Base URL         : http://localhost:11434/v1   (pre-filled)
API key          : (not needed)
```

**Claude via API key**

```
Provider profile : Anthropic-Compatible API
Model            : claude-sonnet-5-5
API format       : anthropic
Base URL         : (blank)
API key          : sk-ant-...
```

**Any model through OpenRouter**

```
Provider profile : OpenRouter (any model, one key)
Model            : anthropic/claude-sonnet-5.5   (or openai/gpt-5.4, deepseek/deepseek-chat, …)
Base URL         : https://openrouter.ai/api/v1  (pre-filled)
API key          : sk-or-...
```

**Your own server**

```
Provider profile : Custom endpoint (OpenAI-compatible)
Model            : whatever your server serves
API format       : openai          (or anthropic for an Anthropic-compatible gateway)
Base URL         : https://llm.internal.example/v1
API key          : your gateway key, if it needs one
```

You can also configure everything from the terminal instead — `impact-vision
setup`, `impact-vision auth login`, or `/model` and `/provider` inside a chat.
All three paths write to the same settings file.

---

## 4. The interface, part by part

### Left rail — conversations

- **New chat** starts a fresh conversation with its own agent runtime.
- The list is grouped by *Today / Yesterday / Previous 7 days / …*.
- **Search** filters by title (`Ctrl/⌘+K` focuses it).
- Hover a row for **rename** (pencil) and **delete** (bin).
- Titles are derived from your first message and can be renamed at any time.

Conversations persist to `~/.openharness/web-chat/<id>.json`, so they survive
a server restart. Reopening one replays the full transcript — messages, tool
calls, tool output and all.

### Top bar

| Element | Meaning |
|---|---|
| Sidebar toggle | Collapse the conversation rail |
| Title | Current conversation |
| Model pill | Active model for this session |
| Mode pill | Permission mode — *Default*, *Plan Mode* or *Auto* |
| Connection pill | Green = live WebSocket; red = reconnecting (it retries automatically with backoff) |
| Panel toggle | Show/hide the workspace panel on the right |

### Centre — the transcript

- **Your messages** appear as bubbles on the right.
- **Assistant replies** stream token by token with a blinking cursor, rendered
  as markdown: headings, **bold**, lists (including nesting and task lists),
  tables, block quotes, links and fenced code blocks with a **copy** button.
- **Tool calls** appear as collapsible cards showing the tool name, a one-line
  summary of its arguments, and a status chip (*running* → *done* / *error*).
  Click to expand the full JSON input and the raw output. Failed calls
  auto-expand.
- **Hover an assistant message** for a **Copy** button, which copies the
  original markdown, not the rendered HTML.

### Right panel — workspace

- **Artifacts** — every file the agent wrote during this conversation, with
  size and a download button. Populated from write-tool arguments and from
  `saved to: …` lines in tool output, so `impact_report` XLSX/HTML exports and
  `lp_ddq_export` files show up automatically.
- **Tasks** — the agent's live task list while it works through a long job.

### Composer

- Autosizing input; **Enter** sends, **Shift+Enter** adds a newline (swap this
  in Settings → *Send with*).
- **Paperclip** or **drag-and-drop** to attach files.
- While a turn is running the send button becomes a red **stop** button.

---

## 5. Working with files

### Uploading

Drag a PDF, XLSX, CSV or DOCX onto the composer (or use the paperclip). Each
file is saved to `<workspace>/.impact-vision/uploads/` with a timestamped,
sanitised name, and appears as a chip above the input.

When you send, Impact Vision prefixes your message with the absolute paths:

```
Attached file: /Users/you/funds/q3/.impact-vision/uploads/20260816-101500-Acme_Deck.pdf

Run a full impact DD on this deck.
```

The agent then uses `pitch_deck_analyze`, `read_file` and the rest of the
toolbox against the real file on disk.

Default limit is 64 MB per file — raise it with `IMPACT_VISION_MAX_UPLOAD_MB`.

### Downloading

Generated reports appear in the **Artifacts** panel. Downloads are restricted
to the workspace subtree and the uploads directory; a request for a path
outside those roots is rejected with `403`. Add more roots with
`IMPACT_VISION_DOWNLOAD_ROOTS` (OS path separator delimited).

### A typical DD session

1. Start the server in your deal folder: `impact-vision serve-web -w ~/deals/acme`
2. Drag `acme-deck.pdf` into the composer.
3. Ask: *"Run the full impact DD workflow on this deck — 5-Dimension score,
   SDG map, IRIS+ gap analysis, greenwashing screen — then write an HTML
   report to acme-impact.html."*
4. Approve the write when prompted.
5. Download `acme-impact.html` from the Artifacts panel.

---

## 6. Slash commands

Type `/` in the composer for an autocomplete menu — arrow keys to move, `Tab`
or `Enter` to accept, `Esc` to dismiss. All 59 CLI commands work:

```
/agents  /branch  /bridge  /clear  /commit  /compact  /config  /context
/continue  /copy  /cost  /diff  /doctor  /effort  /exit  /export  /fast
/feedback  /files  /help  /hooks  /init  /issue  /keybindings  /login
/logout  /mcp  /memory  /model  /onboarding  /output-style  /passes
/permissions  /plan  /plugin  /pr_comments  /privacy-settings  /provider
/rate-limit-options  /release-notes  /reload-plugins  /resume  /rewind
/session  /share  /skills  /stats  /status  /subagents  /summary  /tag
/tasks  /theme  /turns  /upgrade  /usage  /version  /vim  /voice
```

The ones you will reach for most:

| Command | Use |
|---|---|
| `/help` | List everything |
| `/model claude-opus-5-5` | Switch model mid-conversation |
| `/permissions full_auto` | Stop being asked to approve every write |
| `/cost`, `/usage` | Token spend so far |
| `/compact` | Shrink a long conversation to keep context headroom |
| `/skills` | See the loaded impact skills (IRIS+ expert, 5 Dimensions, ToC, …) |
| `/mcp` | MCP server status |
| `/export` | Write the transcript to a file |
| `/clear` | Empty the transcript (the conversation stays in the sidebar) |

Terminal-only commands like `/vim` are accepted but have no visible effect in
the browser.

---

## 7. Permissions and safety

The web chat starts every conversation in the **fund** tool profile: the impact
tools plus safe helpers (read and search files, web search/fetch, ask you a
question). Shell commands, file edits, git worktrees, schedulers and
sub-agents are not available, and file reads are confined to the workspace and
upload folders, so text hidden in a document can't make the agent read other
files on the machine. `full_auto` can't be switched on over the web API. Set
`IMPACT_VISION_TOOL_PROFILE=developer` before `impact-vision serve-web` to
restore the full coding-agent toolset.

Tools still act on the machine hosting the server. In the default permission mode every mutating
tool triggers an **Allow / Deny** dialog showing the tool name and why it needs
confirmation. Read-only tools run without prompting.

- **Allow** lets that call through.
- **Deny** returns a refusal to the agent, which usually adapts.
- Stopping the turn (**Esc** or the stop button) auto-denies anything pending.
- Prompts survive a page refresh — reconnecting replays them.

To stop being asked in a trusted workspace, run `/permissions full_auto`.
Never do this on a server exposed beyond your own machine.

The agent can also ask you open questions; those appear as a text-input dialog
in the same place.

---

## 8. Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Enter` | Send |
| `Shift+Enter` | Newline |
| `Ctrl/⌘+K` | Focus conversation search |
| `Ctrl/⌘+Shift+O` | New chat |
| `Esc` | Stop the running turn / close Settings |
| `/` | Open the slash-command menu |
| `↑` `↓` `Tab` | Navigate and accept in the slash menu |

---

## 9. Using the REST API from the same server

The chat UI and the REST gateway share one process and one port, so anything
you can do in chat you can also script.

```bash
# health
curl http://127.0.0.1:8787/api/v1/health

# 5-Dimension score
curl -X POST http://127.0.0.1:8787/api/v1/score \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme Solar","description":"Off-grid solar for rural households",
       "sector":"Energy","geography":"Kenya",
       "reported_metrics":{"households_served":45000}}'
```

Impact-tool endpoints include `/api/v1/score`, `/sdg-map`, `/greenwashing`,
`/gap-analysis`, `/framework`, `/cross-reference`, `/report`, `/pipeline`,
`/batch`, `/esg-toolbox` and more — browse them at `/docs`.

The chat layer adds its own endpoints under `/api/v1/chat`:

| Method & path | Purpose |
|---|---|
| `GET /api/v1/chat/bootstrap` | Sessions + provider config + workspace, for page load |
| `GET /api/v1/chat/sessions` | List conversations |
| `POST /api/v1/chat/sessions` | Create one (optional `model`, `active_profile`, `permission_mode`, `system_prompt`) |
| `GET /api/v1/chat/sessions/{id}` | Full transcript |
| `PATCH /api/v1/chat/sessions/{id}` | Rename |
| `DELETE /api/v1/chat/sessions/{id}` | Delete |
| `GET /api/v1/chat/providers` | Provider profiles and auth state |
| `POST /api/v1/chat/providers` | Set profile / model / base URL / API key |
| `POST /api/v1/chat/uploads` | Multipart upload |
| `GET /api/v1/chat/artifacts?session_id=…` | Files produced in a conversation |
| `GET /api/v1/chat/artifacts/download?path=…` | Download one |
| `WS /ws/chat?session=…&token=…` | Live conversation stream |

### Driving a conversation programmatically

```python
import asyncio, json, websockets

async def ask(question: str) -> str:
    async with websockets.connect("ws://127.0.0.1:8787/ws/chat") as ws:
        await ws.recv()                                    # snapshot
        await ws.send(json.dumps({"type": "submit", "text": question}))
        parts = []
        while True:
            event = json.loads(await ws.recv())
            if event["type"] == "assistant_delta":
                parts.append(event["text"])
            elif event["type"] == "turn_complete":
                return "".join(parts)

print(asyncio.run(ask("Which IRIS+ metrics fit off-grid solar?")))
```

**Client → server messages:** `submit` (`text`), `cancel`,
`permission_response` (`request_id`, `allowed`), `question_response`
(`request_id`, `answer`), `rename` (`title`), `ping`.

**Server → client events:** `snapshot`, `ready`, `state`, `transcript_item`,
`assistant_delta`, `assistant_complete`, `tool_started`, `tool_completed`,
`tasks`, `busy`, `turn_complete`, `title`, `clear_transcript`,
`modal_request`, `modal_resolved`, `compact_progress`, `error`, `closed`,
`pong`.

---

## 10. Running it for a team

The defaults are built for `localhost` and are safe there: without a key the
server only answers requests addressed to a local host name (`127.0.0.1`,
`localhost`), refuses cross-site requests and WebSocket handshakes from other
web pages, and sends no CORS headers. Binding to another address without a key
(`--host 0.0.0.0`) prints a one-time login URL with a generated token. Before
exposing the server to anyone else, do all of the following.

**1. Require a token.**

```bash
export IMPACT_VISION_API_KEY="$(openssl rand -hex 24)"
impact-vision serve-web --host 0.0.0.0
```

Every REST call then needs `Authorization: Bearer <key>`; the browser sends
the WebSocket token as a subprotocol (`?token=<key>` also works). With a key
set, any `Host` name is accepted (put it behind your domain). In the browser, open **Settings → Server &
REST API → Bearer token**, paste the key, and the page reconnects with it.

**2. Allow other origins only if you need them.** CORS is same-origin by
default. A separate dashboard on another domain needs:

```bash
export IMPACT_VISION_CORS_ORIGINS="https://impact.yourfund.com"
```

To reach a key-less server through a name other than `localhost` (e.g. a VM's
hostname on your own network), list it: `IMPACT_VISION_ALLOWED_HOSTS=ivbox.local`.

**3. Terminate TLS in front of it.** Put nginx, Caddy or a cloud load balancer
ahead of uvicorn and make sure it forwards WebSocket upgrades:

```nginx
location / {
    proxy_pass         http://127.0.0.1:8787;
    proxy_http_version 1.1;
    proxy_set_header   Upgrade    $http_upgrade;   # required for /ws/chat
    proxy_set_header   Connection "upgrade";
    proxy_set_header   Host       $host;
    proxy_read_timeout 3600s;                      # long agent turns
}
```

The page derives the WebSocket URL from `location`, so `https://` pages
automatically use `wss://`.

**Understand what you are sharing.** Every user of a shared server drives the
*same* runtime, in the *same* workspace, under the *same* filesystem
permissions and the *same* provider credentials. There is no per-user
isolation and no multi-tenant account model. Treat it as a shared workstation
for a trusted team — never as a public service — and keep the permission mode
at *Default* so writes require an explicit approval.

---

## 11. Configuration reference

### CLI

| Option | Default | Meaning |
|---|---|---|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8787` | Port |
| `--workspace`, `-w` | current directory | Directory the agent works in |
| `--open` | off | Open a browser once the server is up |
| `--reload` | off | Auto-reload on code changes (development) |

### Environment variables

| Variable | Default | Effect |
|---|---|---|
| `IMPACT_VISION_API_KEY` | *(unset)* | Require a bearer token on REST and WebSocket |
| `IMPACT_VISION_CORS_ORIGINS` | *(unset: same-origin only)* | Comma-separated allowed origins |
| `IMPACT_VISION_ALLOWED_HOSTS` | *(unset: local names only)* | Extra `Host` names a key-less server answers (`*` = any) |
| `IMPACT_VISION_WEB_ALLOW_FULL_AUTO` | *(unset)* | Allow `full_auto` sessions to be created over the web API |
| `IMPACT_VISION_FUND_DOMICILE` | *(unset)* | Fund jurisdiction(s) for portfolio-home deadlines, e.g. `HK` or `EU,UK` |
| `IMPACT_VISION_UPLOAD_DIR` | `~/.openharness/web-uploads` | Where uploads land (pdf, docx, pptx, xlsx, csv, txt, md, json, yaml, images) |
| `IMPACT_VISION_MAX_UPLOAD_MB` | `64` | Per-file upload limit |
| `IMPACT_VISION_DOWNLOAD_ROOTS` | *(unset)* | Extra directories downloads may serve from |
| `IMPACT_VISION_WEB_HOME` | `~/.openharness` | Base directory for stored transcripts |
| `IMPACT_VISION_TOOL_PROFILE` | `fund` (web) / `developer` (terminal) | `fund` = impact tools + safe helpers; `developer` = full coding-agent toolset |
| `OPENHARNESS_CONFIG_DIR` | `~/.openharness` | Settings and credentials |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | *(unset)* | Picked up if no key is stored |

### Where things live

```
~/.openharness/settings.json          provider, model, permission mode
~/.openharness/web-chat/<id>.json     browser conversation transcripts
~/.openharness/data/sessions/         engine-level session snapshots
~/.openharness/web-uploads/          files uploaded from the browser
```

### Browser-local settings

Theme, send-key preference, bearer token and last-open conversation live in
`localStorage` — per browser, never sent to the server except the token, which
is sent as credentials.

---

## 12. Architecture

```
Browser  ──HTTP──▶  chat_ui.py       one self-contained HTML document
         ──WS────▶  chat_api.py      WebSocket + REST (sessions, provider, files)
                         │
                         ▼
                    chat_session.py   ChatSession — pub/sub over one runtime
                         │
                         ▼
                    ui/runtime.py     build_runtime / handle_line
                         │
                         ▼
                    QueryEngine + ToolRegistry + skills + MCP + permissions
```

`ChatSession` is the browser-side sibling of `ui/backend_host.py`, which
drives the same runtime over stdin/stdout JSON lines for the terminal UI. Both
consume the identical `StreamEvent` vocabulary from
`openharness.engine.stream_events`, so the chat UI, the terminal UI, the CLI
and the MCP server never drift apart: add a tool once and all four see it.

Each conversation owns one `RuntimeBundle`. Events are broadcast to every
subscribed WebSocket, so closing a tab never interrupts a running turn, and
reopening it replays the transcript.

**Files**

| File | Role |
|---|---|
| `src/openharness/web/chat_ui.py` | The HTML/CSS/JS document |
| `src/openharness/web/chat_api.py` | WebSocket + REST endpoints |
| `src/openharness/web/chat_session.py` | Session lifecycle, events, persistence, artifacts |
| `src/openharness/web/app.py` | Mounts chat, console, SSE and the REST gateway |
| `src/openharness/web/console.py` | The tool-form console at `/console` |
| `tests/test_web_chat.py` | 29 tests over the UI, REST surface and WebSocket protocol |

---

## 13. Troubleshooting

**"No API credentials configured."**
Open Settings and add a provider API key (§3), then start a **New chat** —
existing conversations keep the runtime they were built with.

**Connection pill stays red.**
The server is down or a proxy is dropping the WebSocket upgrade. Check the
server log; if you are behind a reverse proxy, confirm the `Upgrade` and
`Connection` headers from §10. The page retries with exponential backoff up to
15 s, so it recovers on its own once the server is back.

**"API key rejected — open Settings."**
`IMPACT_VISION_API_KEY` is set on the server but the browser has no matching
token. Paste it under Settings → Server & REST API → Bearer token.

**Uploads fail with 413.**
The file is over the limit. Raise `IMPACT_VISION_MAX_UPLOAD_MB` and restart.

**A download returns 403.**
The file is outside the workspace and the uploads directory. Either start the
server from a parent directory or add the location to
`IMPACT_VISION_DOWNLOAD_ROOTS`.

**Changing the model in Settings did nothing.**
Provider settings apply to conversations created *after* the change. Click
**New chat**, or use `/model <name>` to switch inside the current one.

**A turn is stuck.**
Press `Esc` or the stop button. If the agent is looping, `/turns 32` caps how
many agentic steps a single turn may take.

**Port already in use.**
`impact-vision serve-web --port 8788`.

---

## See also

- [`README.md`](../README.md) — project overview and tool catalogue
- [`docs/fund-manager-guide.md`](fund-manager-guide.md) — impact workflows end to end
- [`docs/cursor-integration.md`](cursor-integration.md) — MCP setup for Claude Desktop, Cursor and VS Code
