"""The Impact Vision chat UI — a single self-contained HTML document.

Zero build step, zero runtime dependencies: one HTML string with inline CSS and
vanilla JavaScript, served straight from the FastAPI app. That keeps the UI
shippable inside the pip wheel (``impact-vision serve-web`` and you're done)
and readable top-to-bottom for contributors, matching the philosophy already
established by :mod:`openharness.web.console`.

Layout
------
* **Left rail** — conversation list with search, rename and delete.
* **Centre** — streaming transcript: markdown assistant messages, collapsible
  tool-call cards, inline permission prompts.
* **Right rail** — artifacts produced during the conversation plus live tasks.
* **Composer** — autosizing input with slash-command autocomplete, file
  drag-and-drop and a stop button while a turn is running.
* **Settings** — provider profile / model / base URL / API key, permission
  mode, plus the REST API details for wiring up external clients.
"""

from __future__ import annotations

from typing import Any

try:
    from fastapi import APIRouter
    from fastapi.responses import HTMLResponse
except ImportError as _exc:  # pragma: no cover - optional dependency
    APIRouter = None  # type: ignore[assignment]
    HTMLResponse = None  # type: ignore[assignment]
    _FASTAPI_IMPORT_ERROR: Exception | None = _exc
else:
    _FASTAPI_IMPORT_ERROR = None


_CSS = r"""
:root{
  --bg:#faf9f5; --bg-elev:#ffffff; --bg-sunken:#f2f0e9;
  --rail:#f5f3ec; --border:#e5e1d6; --border-soft:#eeebe2;
  --text:#1f1e1b; --text-dim:#6b6862; --text-faint:#96928a;
  --accent:#2f6f4f; --accent-soft:#e6f0e9; --accent-text:#ffffff;
  --danger:#b23c2e; --danger-soft:#fbeae7; --warn:#a56a15;
  --code-bg:#f4f2ea; --shadow:0 1px 2px rgba(0,0,0,.05),0 8px 24px rgba(0,0,0,.06);
  --radius:12px; --radius-sm:8px;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,"Helvetica Neue",Arial,sans-serif;
}
html[data-theme="dark"]{
  --bg:#1b1a17; --bg-elev:#232220; --bg-sunken:#161514;
  --rail:#1f1e1b; --border:#35332e; --border-soft:#2b2a26;
  --text:#eceae4; --text-dim:#a5a199; --text-faint:#78746c;
  --accent:#6bbf90; --accent-soft:#1f3129; --accent-text:#0f1a14;
  --danger:#e0836f; --danger-soft:#3a231e; --warn:#d0a24a;
  --code-bg:#1a1917; --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);
  font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased;overflow:hidden;
}
button{font:inherit;color:inherit;cursor:pointer;border:none;background:none}
input,textarea,select{font:inherit;color:inherit}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:6px;border:3px solid transparent;background-clip:padding-box}
::-webkit-scrollbar-thumb:hover{background:var(--text-faint);background-clip:padding-box;border:3px solid transparent}
::-webkit-scrollbar-track{background:transparent}

/* ---------- shell ---------- */
.app{display:grid;grid-template-columns:264px 1fr;height:100vh;overflow:hidden}
.app.rail-hidden{grid-template-columns:0 1fr}
.app.panel-open{grid-template-columns:264px 1fr 320px}
.app.rail-hidden.panel-open{grid-template-columns:0 1fr 320px}

/* ---------- left rail ---------- */
.rail{background:var(--rail);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}
.app.rail-hidden .rail{display:none}
.rail-head{padding:14px 12px 8px;display:flex;flex-direction:column;gap:10px}
.brand{display:flex;align-items:center;gap:9px;padding:0 4px}
.brand-mark{width:26px;height:26px;border-radius:7px;background:var(--accent);color:var(--accent-text);
  display:grid;place-items:center;font-weight:700;font-size:13px;flex:none}
.brand-name{font-weight:600;font-size:14.5px;letter-spacing:-.01em}
.brand-ver{font-size:11px;color:var(--text-faint);margin-left:auto}
.btn-new{display:flex;align-items:center;gap:8px;width:100%;padding:9px 11px;border-radius:var(--radius-sm);
  background:var(--bg-elev);border:1px solid var(--border);font-size:13.5px;font-weight:500;transition:.12s}
.btn-new:hover{border-color:var(--accent);color:var(--accent)}
.rail-search{position:relative}
.rail-search input{width:100%;padding:7px 10px 7px 28px;border-radius:var(--radius-sm);border:1px solid var(--border);
  background:var(--bg-elev);font-size:13px;outline:none}
.rail-search input:focus{border-color:var(--accent)}
.rail-search svg{position:absolute;left:8px;top:50%;transform:translateY(-50%);color:var(--text-faint)}
.rail-list{flex:1;overflow-y:auto;padding:4px 8px 12px}
.rail-group{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-faint);
  padding:12px 6px 6px}
.conv{display:flex;align-items:center;gap:6px;padding:8px 9px;border-radius:var(--radius-sm);cursor:pointer;
  font-size:13.5px;color:var(--text-dim);transition:.1s;position:relative}
.conv:hover{background:var(--bg-elev);color:var(--text)}
.conv.active{background:var(--accent-soft);color:var(--text);font-weight:500}
.conv-title{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.conv-actions{display:none;gap:2px}
.conv:hover .conv-actions,.conv.active .conv-actions{display:flex}
.conv-actions button{padding:3px;border-radius:5px;color:var(--text-faint);display:grid;place-items:center}
.conv-actions button:hover{background:var(--border);color:var(--text)}
.rail-foot{border-top:1px solid var(--border);padding:8px;display:flex;gap:6px}
.rail-foot button{flex:1;padding:7px;border-radius:var(--radius-sm);font-size:12.5px;color:var(--text-dim);
  display:flex;align-items:center;justify-content:center;gap:6px}
.rail-foot button:hover{background:var(--bg-elev);color:var(--text)}

/* ---------- main ---------- */
.main{display:flex;flex-direction:column;min-width:0;overflow:hidden;background:var(--bg)}
.topbar{height:52px;flex:none;display:flex;align-items:center;gap:10px;padding:0 16px;
  border-bottom:1px solid var(--border-soft);background:var(--bg)}
.icon-btn{width:30px;height:30px;border-radius:7px;display:grid;place-items:center;color:var(--text-dim);flex:none}
.icon-btn:hover{background:var(--bg-sunken);color:var(--text)}
.icon-btn.on{background:var(--accent-soft);color:var(--accent)}
.chat-title{font-size:14.5px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
.pill{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:99px;font-size:11.5px;
  background:var(--bg-sunken);color:var(--text-dim);border:1px solid var(--border-soft);white-space:nowrap}
.pill.live{color:var(--accent);border-color:var(--accent)}
.pill b{font-weight:600;color:var(--text)}
.dot{width:6px;height:6px;border-radius:99px;background:var(--text-faint)}
.dot.ok{background:var(--accent)}
.dot.bad{background:var(--danger)}

.scroll{flex:1;overflow-y:auto;scroll-behavior:smooth}
.thread{max-width:768px;margin:0 auto;padding:28px 24px 24px}

/* ---------- messages ---------- */
.msg{margin-bottom:22px;animation:fade .18s ease-out}
@keyframes fade{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:none}}
.msg-user{display:flex;justify-content:flex-end}
.msg-user .bubble{background:var(--accent-soft);border:1px solid var(--border-soft);padding:11px 15px;
  border-radius:16px 16px 4px 16px;max-width:82%;white-space:pre-wrap;word-break:break-word}
.msg-assistant{position:relative}
.msg-assistant .who{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:600;color:var(--text-dim);
  margin-bottom:7px}
.msg-assistant .who .brand-mark{width:19px;height:19px;font-size:10px;border-radius:5px}
.msg-actions{display:flex;gap:4px;margin-top:8px;opacity:0;transition:.15s}
.msg-assistant:hover .msg-actions{opacity:1}
.msg-actions button{padding:4px 8px;border-radius:6px;font-size:11.5px;color:var(--text-faint);
  display:inline-flex;align-items:center;gap:4px}
.msg-actions button:hover{background:var(--bg-sunken);color:var(--text)}
.msg-system{font-size:12.5px;color:var(--text-dim);background:var(--bg-sunken);border:1px solid var(--border-soft);
  border-radius:var(--radius-sm);padding:8px 12px;white-space:pre-wrap;word-break:break-word;font-family:var(--mono)}
.msg-system.err{color:var(--danger);background:var(--danger-soft);border-color:var(--danger)}
.setup-card{border:1px solid var(--border-soft);background:var(--bg-sunken);border-radius:var(--radius-sm);
  padding:14px 16px;font-size:14px;color:var(--text);border-left:4px solid var(--accent)}
.setup-card p{margin:6px 0 0;color:var(--text-dim)}
.setup-card code{font-family:var(--mono);font-size:12.5px;background:var(--bg);padding:1px 5px;border-radius:4px}
.dot.warn{background:#fab219}

/* ---------- markdown ---------- */
.md>*:first-child{margin-top:0}
.md>*:last-child{margin-bottom:0}
.md p{margin:0 0 12px}
.md h1,.md h2,.md h3,.md h4{margin:22px 0 10px;line-height:1.3;font-weight:650;letter-spacing:-.01em}
.md h1{font-size:1.4em}.md h2{font-size:1.22em}.md h3{font-size:1.08em}.md h4{font-size:1em}
.md ul,.md ol{margin:0 0 12px;padding-left:24px}
.md li{margin:3px 0}
.md li>ul,.md li>ol{margin:3px 0}
.md blockquote{margin:0 0 12px;padding:2px 0 2px 14px;border-left:3px solid var(--border);color:var(--text-dim)}
.md hr{border:none;border-top:1px solid var(--border);margin:20px 0}
.md code{font-family:var(--mono);font-size:.875em;background:var(--code-bg);padding:2px 5px;border-radius:5px;
  border:1px solid var(--border-soft);word-break:break-word}
.md pre{margin:0 0 14px;background:var(--code-bg);border:1px solid var(--border);border-radius:var(--radius-sm);
  overflow:hidden;position:relative}
.md pre code{display:block;padding:13px 14px;background:none;border:none;overflow-x:auto;font-size:12.8px;
  line-height:1.55;white-space:pre;word-break:normal}
.md pre .code-head{display:flex;align-items:center;justify-content:space-between;padding:5px 10px;
  border-bottom:1px solid var(--border);font-size:11px;color:var(--text-faint);font-family:var(--mono)}
.md pre .code-head button{padding:2px 7px;border-radius:5px;font-size:11px;color:var(--text-faint)}
.md pre .code-head button:hover{background:var(--border);color:var(--text)}
.md table{border-collapse:collapse;margin:0 0 14px;font-size:13.5px;display:block;overflow-x:auto;max-width:100%}
.md th,.md td{border:1px solid var(--border);padding:6px 11px;text-align:left;vertical-align:top}
.md th{background:var(--bg-sunken);font-weight:600}
.md a{word-break:break-word}
.cursor{display:inline-block;width:7px;height:15px;background:var(--accent);vertical-align:-2px;
  animation:blink 1s steps(2) infinite;margin-left:2px;border-radius:1px}
@keyframes blink{50%{opacity:0}}

/* ---------- tool cards ---------- */
.tool{border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg-elev);margin:0 0 12px;
  overflow:hidden;font-size:13px}
.tool-head{display:flex;align-items:center;gap:8px;padding:8px 11px;cursor:pointer;user-select:none}
.tool-head:hover{background:var(--bg-sunken)}
.tool-name{font-family:var(--mono);font-size:12.5px;font-weight:600}
.tool-sum{color:var(--text-faint);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;
  font-family:var(--mono)}
.tool-status{font-size:11px;padding:1px 7px;border-radius:99px;background:var(--bg-sunken);color:var(--text-faint);
  border:1px solid var(--border-soft);flex:none}
.tool-status.run{color:var(--warn);border-color:var(--warn)}
.tool-status.ok{color:var(--accent);border-color:var(--accent)}
.tool-status.err{color:var(--danger);border-color:var(--danger)}
.tool-body{display:none;border-top:1px solid var(--border);background:var(--bg-sunken)}
.tool.open .tool-body{display:block}
.tool-body pre{margin:0;padding:10px 12px;font-family:var(--mono);font-size:12px;line-height:1.5;
  white-space:pre-wrap;word-break:break-word;max-height:420px;overflow:auto}
.tool-body .label{padding:7px 12px 0;font-size:10.5px;font-weight:600;text-transform:uppercase;
  letter-spacing:.06em;color:var(--text-faint)}
.chev{transition:.15s;color:var(--text-faint);flex:none}
.tool.open .chev{transform:rotate(90deg)}
.spin{animation:spin .9s linear infinite;flex:none}
@keyframes spin{to{transform:rotate(360deg)}}

/* ---------- welcome ---------- */
.welcome{max-width:700px;margin:0 auto;padding:48px 24px;text-align:center}
.welcome h2{font-size:26px;font-weight:600;letter-spacing:-.02em;margin:18px 0 8px}
.welcome p{color:var(--text-dim);margin:0 auto 26px;max-width:520px}
.welcome .brand-mark{width:46px;height:46px;font-size:20px;border-radius:12px;margin:0 auto}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:10px;text-align:left}
.card{border:1px solid var(--border);border-radius:var(--radius);padding:13px 15px;background:var(--bg-elev);
  cursor:pointer;transition:.13s}
.card:hover{border-color:var(--accent);transform:translateY(-1px);box-shadow:var(--shadow)}
.card b{display:block;font-size:13.5px;margin-bottom:3px;font-weight:600}
.card span{font-size:12.5px;color:var(--text-dim);line-height:1.5}

/* ---------- composer ---------- */
.composer-wrap{flex:none;padding:0 24px 18px;background:linear-gradient(to top,var(--bg) 62%,transparent)}
.composer{max-width:768px;margin:0 auto;position:relative}
.attachments{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:4px 9px;border-radius:99px;background:var(--bg-sunken);
  border:1px solid var(--border);font-size:12px;color:var(--text-dim)}
.chip button{color:var(--text-faint);display:grid;place-items:center}
.chip button:hover{color:var(--danger)}
.input-box{border:1px solid var(--border);border-radius:16px;background:var(--bg-elev);box-shadow:var(--shadow);
  transition:.15s;overflow:hidden}
.input-box:focus-within{border-color:var(--accent)}
.input-box.drag{border-color:var(--accent);background:var(--accent-soft)}
.input-box textarea{width:100%;border:none;outline:none;resize:none;background:none;padding:13px 15px 4px;
  font-size:14.5px;line-height:1.55;max-height:260px;min-height:26px;display:block}
.input-box textarea::placeholder{color:var(--text-faint)}
.input-row{display:flex;align-items:center;gap:6px;padding:5px 8px 8px 10px}
.input-row .grow{flex:1}
.send{width:31px;height:31px;border-radius:8px;background:var(--accent);color:var(--accent-text);
  display:grid;place-items:center;transition:.13s;flex:none}
.send:disabled{opacity:.35;cursor:not-allowed}
.send.stop{background:var(--danger)}
.hint{text-align:center;font-size:11px;color:var(--text-faint);margin-top:7px}

/* ---------- slash menu ---------- */
.slash{position:absolute;bottom:100%;left:0;right:0;margin-bottom:8px;background:var(--bg-elev);
  border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);max-height:290px;
  overflow-y:auto;display:none;z-index:40;padding:5px}
.slash.show{display:block}
.slash-item{padding:7px 11px;border-radius:var(--radius-sm);cursor:pointer;display:flex;gap:10px;align-items:baseline}
.slash-item.sel{background:var(--accent-soft)}
.slash-item code{font-family:var(--mono);font-size:12.5px;font-weight:600;color:var(--accent);flex:none}
.slash-item span{font-size:12.5px;color:var(--text-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ---------- right panel ---------- */
.panel{background:var(--rail);border-left:1px solid var(--border);display:none;flex-direction:column;overflow:hidden}
.app.panel-open .panel{display:flex}
.panel-head{height:52px;flex:none;display:flex;align-items:center;gap:8px;padding:0 14px;
  border-bottom:1px solid var(--border);font-size:13.5px;font-weight:600}
.panel-tabs{display:flex;gap:2px;padding:8px 10px 0}
.panel-tabs button{padding:5px 11px;border-radius:7px;font-size:12.5px;color:var(--text-dim)}
.panel-tabs button.on{background:var(--bg-elev);color:var(--text);font-weight:500}
.panel-body{flex:1;overflow-y:auto;padding:10px}
.empty{color:var(--text-faint);font-size:12.5px;text-align:center;padding:32px 12px}
.file{display:flex;align-items:center;gap:9px;padding:9px 10px;border-radius:var(--radius-sm);
  border:1px solid var(--border);background:var(--bg-elev);margin-bottom:6px;font-size:12.5px}
.file .fname{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.file .fmeta{font-size:11px;color:var(--text-faint)}
.file a{color:var(--text-faint);display:grid;place-items:center;padding:3px}
.file a:hover{color:var(--accent)}
.task{display:flex;gap:8px;padding:7px 9px;font-size:12.5px;border-radius:var(--radius-sm);align-items:baseline}
.task .tstat{font-size:10px;padding:1px 6px;border-radius:99px;border:1px solid var(--border);color:var(--text-faint);flex:none}
.task .tstat.completed{color:var(--accent);border-color:var(--accent)}
.task .tstat.in_progress{color:var(--warn);border-color:var(--warn)}

/* ---------- reports: cards, viewer, share ---------- */
.rcard{max-width:760px;margin:16px auto;border:1px solid var(--border);border-radius:var(--radius);
  background:var(--bg-elev);padding:16px 18px;box-shadow:var(--shadow)}
.rcard .rhead{display:flex;gap:12px;align-items:center}
.rcard .mono{flex:none;width:40px;height:40px;border-radius:10px;background:var(--accent);color:var(--accent-text);
  display:grid;place-items:center;font-weight:700;font-size:14px}
.rcard h4{margin:0;font-size:15.5px;line-height:1.3}
.rcard .rmeta{font-size:12.5px;color:var(--text-dim)}
.gate{display:inline-block;font-size:12px;font-weight:600;padding:2px 10px;border-radius:999px;border:1px solid currentColor;margin-top:10px}
.gate.ok{color:var(--accent)} .gate.warn{color:var(--warn)} .gate.bad{color:var(--danger)}
.rrec{font-size:13px;color:var(--text-dim);margin:8px 0 0}
.rstats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}
.rstat .k{font-size:11.5px;color:var(--text-dim)} .rstat .v{font-size:18px;font-weight:650;line-height:1.3}
.rstat .v small{font-size:12px;color:var(--text-faint);font-weight:500}
.ractions{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.ractions .dl{font-size:12px;padding:4px 9px;border:1px solid var(--border);border-radius:7px;color:var(--text-dim)}
.ractions .dl:hover{border-color:var(--accent);color:var(--accent)}
.rcard .busy{display:flex;gap:10px;align-items:center;color:var(--text-dim);font-size:13.5px;margin-top:10px}
.spin{width:14px;height:14px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.card.primary{border-color:var(--accent);background:var(--accent-soft)}
.rep{display:flex;gap:10px;align-items:center;padding:9px 10px;border-radius:var(--radius-sm);cursor:pointer}
.rep:hover{background:var(--bg-elev)}
.rep .gate{margin:0;font-size:10.5px;padding:0 7px}
.viewer{position:fixed;inset:0;z-index:90;background:var(--bg);display:none;flex-direction:column}
.viewer.show{display:flex}
.viewer [hidden]{display:none!important}
.viewer-bar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;padding:10px 14px;border-bottom:1px solid var(--border);background:var(--bg-elev)}
.viewer-bar h3{margin:0 auto 0 0;font-size:15px;font-weight:600}
.viewer-bar label{font-size:12.5px;color:var(--text-dim);display:flex;gap:6px;align-items:center}
.viewer-bar select{padding:5px 8px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg);font-size:13px}
.sharebox{display:none;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 14px;border-bottom:1px solid var(--border);background:var(--accent-soft);font-size:13px}
.sharebox.show{display:flex}
.sharebox input{flex:1;min-width:220px;padding:6px 9px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--bg-elev);font-family:var(--mono);font-size:12px}
.viewer iframe{flex:1;border:0;width:100%;background:var(--bg)}
@media (max-width:700px){.rstats{grid-template-columns:repeat(2,1fr)}}

/* ---------- modals ---------- */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.42);display:none;place-items:center;z-index:100;padding:20px}
.overlay.show{display:grid}
.modal{background:var(--bg-elev);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);
  width:100%;max-width:560px;max-height:86vh;display:flex;flex-direction:column;overflow:hidden}
.modal.wide{max-width:660px}
.modal-head{padding:16px 20px 12px;border-bottom:1px solid var(--border-soft);display:flex;align-items:center;gap:10px}
.modal-head h3{margin:0;font-size:16px;font-weight:600;flex:1}
.modal-body{padding:18px 20px;overflow-y:auto}
.modal-foot{padding:12px 20px 16px;border-top:1px solid var(--border-soft);display:flex;gap:8px;justify-content:flex-end}
.btn{padding:8px 15px;border-radius:var(--radius-sm);font-size:13.5px;font-weight:500;border:1px solid var(--border);
  background:var(--bg-elev);transition:.12s}
.btn:hover{background:var(--bg-sunken)}
.btn.primary{background:var(--accent);color:var(--accent-text);border-color:var(--accent)}
.btn.primary:hover{opacity:.9}
.btn.danger{color:var(--danger);border-color:var(--danger)}
.btn.danger:hover{background:var(--danger-soft)}
.field{margin-bottom:15px}
.field label{display:block;font-size:12.5px;font-weight:600;margin-bottom:5px}
.field .desc{font-size:11.5px;color:var(--text-faint);margin:-2px 0 6px;line-height:1.45}
.field input,.field select,.field textarea{width:100%;padding:8px 11px;border-radius:var(--radius-sm);
  border:1px solid var(--border);background:var(--bg);outline:none;font-size:13.5px}
.field input:focus,.field select:focus{border-color:var(--accent)}
.field input[readonly]{background:var(--bg-sunken);color:var(--text-dim)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.sec{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text-faint);
  margin:22px 0 11px;padding-bottom:6px;border-bottom:1px solid var(--border-soft)}
.sec:first-child{margin-top:0}
.note{font-size:12px;color:var(--text-dim);background:var(--bg-sunken);border:1px solid var(--border-soft);
  border-radius:var(--radius-sm);padding:9px 12px;line-height:1.5}
.note code{font-family:var(--mono);font-size:11.5px;background:var(--code-bg);padding:1px 4px;border-radius:4px}
.perm-tool{font-family:var(--mono);font-weight:600;color:var(--accent)}
.perm-reason{white-space:pre-wrap;word-break:break-word;font-family:var(--mono);font-size:12px;
  background:var(--bg-sunken);border:1px solid var(--border-soft);border-radius:var(--radius-sm);padding:10px 12px;
  max-height:280px;overflow:auto;margin-top:10px}

.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(80px);background:var(--text);
  color:var(--bg);padding:9px 17px;border-radius:99px;font-size:13px;z-index:200;opacity:0;transition:.22s;
  pointer-events:none;box-shadow:var(--shadow)}
.toast.show{opacity:1;transform:translateX(-50%)}

@media(max-width:900px){
  .app,.app.panel-open{grid-template-columns:1fr}
  .rail{position:fixed;inset:0 auto 0 0;width:264px;z-index:60;box-shadow:var(--shadow)}
  .app.rail-hidden .rail{display:none}
  .app:not(.rail-hidden) .rail{display:flex}
  .panel{position:fixed;inset:0 0 0 auto;width:300px;z-index:60}
  .thread,.composer{max-width:100%}
}
"""


_JS = r"""
/* =====================================================================
   Impact Vision — chat client. No frameworks, no build step.
   ===================================================================== */
const $ = (sel, root) => (root || document).querySelector(sel);
const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

const S = {
  ws: null, sessionId: null, sessions: [], commands: [], provider: null,
  busy: false, streamEl: null, streamBuf: '', pendingTools: [],
  attachments: [], artifacts: [], tasks: [], reports: [], filter: '', tab: 'artifacts',
  analyzeNext: false, viewing: null,
  slashIdx: 0, slashItems: [], reconnectDelay: 500, bootstrap: null, modalQueue: [],
};

const token = () => localStorage.getItem('iv_token') || '';
const setToken = (v) => v ? localStorage.setItem('iv_token', v) : localStorage.removeItem('iv_token');

async function api(path, opts) {
  const o = Object.assign({headers: {}}, opts || {});
  if (!(o.body instanceof FormData)) o.headers['Content-Type'] = 'application/json';
  if (token()) o.headers['Authorization'] = 'Bearer ' + token();
  const res = await fetch('/api/v1/chat' + path, o);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

function toast(msg) {
  const el = $('#toast'); el.textContent = msg; el.classList.add('show');
  clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove('show'), 2400);
}

/* ---------------------------------------------------------------------
   Markdown — deliberately small: headings, lists, tables, code, quotes,
   inline emphasis, links. Everything is escaped before formatting so a
   model response can never inject markup.
   ------------------------------------------------------------------- */
const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

function inlineMd(text) {
  let out = esc(text);
  const codes = [];
  out = out.replace(/`([^`]+)`/g, (m, c) => { codes.push(c); return '\u0000' + (codes.length - 1) + '\u0000'; });
  out = out.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, '<em>[image: $1]</em>');
  out = out.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g,
    (m, label, href) => /^(https?:|mailto:|\/|#)/i.test(href)
      ? '<a href="' + href + '" target="_blank" rel="noopener">' + label + '</a>' : m);
  out = out.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g,
    '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
  out = out.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/(^|[^*\w])\*([^*\n]+)\*(?![*\w])/g, '$1<em>$2</em>');
  out = out.replace(/(^|[^_\w])_([^_\n]+)_(?![_\w])/g, '$1<em>$2</em>');
  out = out.replace(/~~([^~]+)~~/g, '<del>$1</del>');
  out = out.replace(/\u0000(\d+)\u0000/g, (m, i) => '<code>' + codes[+i] + '</code>');
  return out;
}

let codeSeq = 0;
function renderMd(src) {
  const lines = String(src || '').replace(/\r\n/g, '\n').split('\n');
  const html = [];
  let i = 0;
  const listStack = [];

  const closeLists = (toDepth) => {
    while (listStack.length > toDepth) html.push('</' + listStack.pop().tag + '>');
  };

  while (i < lines.length) {
    const line = lines[i];

    // fenced code block
    const fence = line.match(/^\s*(`{3,}|~{3,})\s*([\w+#.-]*)\s*$/);
    if (fence) {
      closeLists(0);
      const marker = fence[1][0], lang = fence[2] || '';
      const buf = [];
      i++;
      while (i < lines.length && !new RegExp('^\\s*' + marker + '{3,}\\s*$').test(lines[i])) buf.push(lines[i++]);
      i++;
      const id = 'code' + (codeSeq++);
      html.push(
        '<pre><div class="code-head"><span>' + esc(lang || 'text') + '</span>' +
        '<button type="button" onclick="copyCode(\'' + id + '\')">copy</button></div>' +
        '<code id="' + id + '">' + esc(buf.join('\n')) + '</code></pre>'
      );
      continue;
    }

    // table
    if (/\|/.test(line) && i + 1 < lines.length && /^[\s|:*-]+$/.test(lines[i + 1]) && /-/.test(lines[i + 1])) {
      closeLists(0);
      const cells = (row) => row.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map((c) => c.trim());
      const head = cells(line);
      i += 2;
      const body = [];
      while (i < lines.length && /\|/.test(lines[i]) && lines[i].trim()) body.push(cells(lines[i++]));
      html.push('<table><thead><tr>' + head.map((c) => '<th>' + inlineMd(c) + '</th>').join('') + '</tr></thead><tbody>' +
        body.map((r) => '<tr>' + r.map((c) => '<td>' + inlineMd(c) + '</td>').join('') + '</tr>').join('') +
        '</tbody></table>');
      continue;
    }

    // heading / rule / quote
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) { closeLists(0); const lvl = Math.min(h[1].length, 4); html.push('<h' + lvl + '>' + inlineMd(h[2]) + '</h' + lvl + '>'); i++; continue; }
    if (/^\s*([-*_])\s*\1\s*\1[\s\-*_]*$/.test(line)) { closeLists(0); html.push('<hr>'); i++; continue; }
    if (/^\s*>\s?/.test(line)) {
      closeLists(0);
      const buf = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^\s*>\s?/, ''));
      html.push('<blockquote>' + renderMd(buf.join('\n')) + '</blockquote>');
      continue;
    }

    // list items (nesting by indentation)
    const li = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/);
    if (li) {
      const depth = Math.floor(li[1].replace(/\t/g, '    ').length / 2) + 1;
      const tag = /\d/.test(li[2]) ? 'ol' : 'ul';
      while (listStack.length > depth) html.push('</' + listStack.pop().tag + '>');
      if (listStack.length === depth && listStack[depth - 1].tag !== tag) {
        html.push('</' + listStack.pop().tag + '>');
      }
      while (listStack.length < depth) { html.push('<' + tag + '>'); listStack.push({tag: tag}); }
      let body = li[3];
      const task = body.match(/^\[([ xX])\]\s*(.*)$/);
      if (task) body = (task[1] === ' ' ? '☐ ' : '☑ ') + task[2];
      html.push('<li>' + inlineMd(body) + '</li>');
      i++;
      continue;
    }

    if (!line.trim()) { closeLists(0); i++; continue; }

    // paragraph
    closeLists(0);
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^\s*(#{1,6}\s|>|([-*+]|\d+[.)])\s)/.test(lines[i]) &&
           !/^\s*(`{3,}|~{3,})/.test(lines[i])) para.push(lines[i++]);
    html.push('<p>' + inlineMd(para.join('\n')).replace(/\n/g, '<br>') + '</p>');
  }
  closeLists(0);
  return html.join('');
}

function copyCode(id) {
  const el = document.getElementById(id);
  if (el) { navigator.clipboard.writeText(el.textContent).then(() => toast('Code copied')); }
}

/* ---------------------------------------------------------------------
   Transcript rendering
   ------------------------------------------------------------------- */
const thread = () => $('#thread');

function atBottom() {
  const sc = $('#scroll');
  return sc.scrollHeight - sc.scrollTop - sc.clientHeight < 120;
}
function scrollDown(force) {
  const sc = $('#scroll');
  if (force || atBottom()) requestAnimationFrame(() => { sc.scrollTop = sc.scrollHeight; });
}

function addUser(text) {
  const el = document.createElement('div');
  el.className = 'msg msg-user';
  el.innerHTML = '<div class="bubble"></div>';
  $('.bubble', el).textContent = text;
  thread().appendChild(el);
  scrollDown(true);
}

function addSetupCard(text) {
  const el = document.createElement('div');
  el.className = 'msg';
  const card = document.createElement('div');
  card.className = 'setup-card';
  card.innerHTML =
    '<strong>Connect a model to start chatting</strong>' +
    '<p></p>' +
    '<p class="setup-alt">No key yet? Deck analysis works offline: <a href="#" class="setup-analyze">analyze a pitch deck</a>, ' +
    'or run <code>impact-vision assess deck.pdf</code>.</p>';
  card.querySelector('.setup-analyze').onclick = (e) => { e.preventDefault(); pickDeck(); };
  card.querySelector('p').textContent = text;
  el.appendChild(card);
  thread().appendChild(el);
  const dot = $('#connDot'); if (dot) dot.className = 'dot warn';
  const label = $('#connLabel'); if (label) label.textContent = 'no model configured';
  scrollDown();
}

function addSystem(text, isError) {
  if (isError && /^No API credentials/.test(text || '')) { addSetupCard(text); return; }
  const el = document.createElement('div');
  el.className = 'msg';
  const inner = document.createElement('div');
  inner.className = 'msg-system' + (isError ? ' err' : '');
  inner.textContent = text;
  el.appendChild(inner);
  thread().appendChild(el);
  scrollDown();
}

function assistantShell() {
  const el = document.createElement('div');
  el.className = 'msg msg-assistant';
  el.innerHTML =
    '<div class="who"><span class="brand-mark">IV</span>Impact Vision</div>' +
    '<div class="md"></div>' +
    '<div class="msg-actions"><button type="button" data-copy>⧉ Copy</button></div>';
  el.querySelector('[data-copy]').onclick = () => {
    navigator.clipboard.writeText(el._raw || el.querySelector('.md').innerText).then(() => toast('Copied'));
  };
  return el;
}

function addAssistant(text) {
  const el = assistantShell();
  el._raw = text;
  $('.md', el).innerHTML = renderMd(text);
  thread().appendChild(el);
  scrollDown();
  return el;
}

let rafPending = false;
function paintStream() {
  if (rafPending) return;
  rafPending = true;
  requestAnimationFrame(() => {
    rafPending = false;
    if (!S.streamEl) return;
    $('.md', S.streamEl).innerHTML = renderMd(S.streamBuf) + '<span class="cursor"></span>';
    scrollDown();
  });
}

function toolSummary(input) {
  if (!input || typeof input !== 'object') return '';
  for (const key of ['file_path', 'path', 'command', 'pattern', 'query', 'description', 'url', 'company_name', 'prompt']) {
    if (input[key]) return String(input[key]).slice(0, 130);
  }
  const s = JSON.stringify(input);
  return s.length > 130 ? s.slice(0, 130) + '…' : s;
}

function addTool(item) {
  const el = document.createElement('div');
  el.className = 'tool';
  el.innerHTML =
    '<div class="tool-head">' +
      '<svg class="chev" width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">' +
        '<path d="M6 3l5 5-5 5"/></svg>' +
      '<span class="tool-name"></span><span class="tool-sum"></span>' +
      '<span class="tool-status run">running</span>' +
      '<svg class="spin" width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">' +
        '<path d="M8 1.5a6.5 6.5 0 1 0 6.5 6.5" stroke-linecap="round"/></svg>' +
    '</div>' +
    '<div class="tool-body"><div class="label">Input</div><pre class="tool-in"></pre>' +
    '<div class="label" data-out hidden>Output</div><pre class="tool-out" hidden></pre></div>';
  $('.tool-name', el).textContent = item.tool_name || 'tool';
  $('.tool-sum', el).textContent = toolSummary(item.tool_input);
  $('.tool-in', el).textContent = JSON.stringify(item.tool_input || {}, null, 2);
  $('.tool-head', el).onclick = () => el.classList.toggle('open');
  const wrap = document.createElement('div');
  wrap.className = 'msg';
  wrap.appendChild(el);
  thread().appendChild(wrap);
  scrollDown();
  return el;
}

function finishTool(el, item) {
  if (!el) return;
  const spin = $('.spin', el); if (spin) spin.remove();
  const st = $('.tool-status', el);
  st.className = 'tool-status ' + (item.is_error ? 'err' : 'ok');
  st.textContent = item.is_error ? 'error' : 'done';
  const out = $('.tool-out', el), lbl = $('[data-out]', el);
  const text = String(item.text == null ? '' : item.text);
  out.textContent = text.length > 20000 ? text.slice(0, 20000) + '\n… (truncated)' : text;
  out.hidden = false; lbl.hidden = false;
  if (item.is_error) el.classList.add('open');
  scrollDown();
}

function renderTranscript(rows) {
  thread().innerHTML = '';
  S.pendingTools = [];
  if (!rows || !rows.length) { renderWelcome(); return; }
  const openTools = {};
  rows.forEach((row) => {
    if (row.role === 'user') addUser(row.text);
    else if (row.role === 'assistant') addAssistant(row.text);
    else if (row.role === 'system') addSystem(row.text, row.is_error);
    else if (row.role === 'tool') { openTools[row.tool_name] = addTool(row); }
    else if (row.role === 'tool_result') { finishTool(openTools[row.tool_name], row); delete openTools[row.tool_name]; }
  });
  scrollDown(true);
}

const STARTERS = [
  ['Analyze a pitch deck', 'Drop or choose a PDF, Word, Markdown or text file. Works offline — you get the IC verdict, the decision report and the data in about a second.', pickDeck],
  ['Score a company on the 5 Dimensions', 'Run an IMP 5-Dimension impact assessment for a company I describe.'],
  ['Map a company to the SDGs', 'Map this company to UN SDG goals and targets, with IRIS+ metrics for each.'],
  ['Screen a report for greenwashing', 'Check this sustainability report for vague or unverifiable impact claims.'],
  ['Draft an LP impact report', 'Draft an LP-facing impact report section for our portfolio.'],
  ['Check SFDR / ESRS readiness', 'Assess our disclosure readiness against SFDR PAI and ESRS requirements.'],
];

function renderWelcome() {
  const el = document.createElement('div');
  el.className = 'welcome';
  el.innerHTML =
    '<div class="brand-mark">IV</div>' +
    '<h2>Impact Vision</h2>' +
    '<p>Impact measurement and SDG alignment for VC and impact funds — IRIS+, the 5 Dimensions of Impact, ' +
    'and 20+ ESG and regulatory frameworks. Ask anything, or start here.</p>' +
    '<div class="cards"></div>';
  const cards = $('.cards', el);
  STARTERS.forEach(([title, prompt, action]) => {
    const c = document.createElement('div');
    c.className = 'card' + (action ? ' primary' : '');
    c.setAttribute('role', 'button'); c.tabIndex = 0;
    c.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); c.onclick(); } };
    c.innerHTML = '<b></b><span></span>';
    $('b', c).textContent = title;
    $('span', c).textContent = prompt;
    c.onclick = action || (() => { $('#input').value = prompt; autosize(); $('#input').focus(); });
    cards.appendChild(c);
  });
  thread().appendChild(el);
}

/* ---------------------------------------------------------------------
   WebSocket
   ------------------------------------------------------------------- */
function connect(sessionId) {
  if (S.ws) { S.ws.onclose = null; S.ws.close(); }
  S.sessionId = sessionId || null;
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const params = new URLSearchParams();
  if (sessionId) params.set('session', sessionId);
  if (token()) params.set('token', token());
  const ws = new WebSocket(proto + '//' + location.host + '/ws/chat?' + params.toString());
  S.ws = ws;

  ws.onopen = () => { S.reconnectDelay = 500; setConn(true); };
  ws.onclose = (ev) => {
    setConn(false);
    if (ev.code === 4401) { toast('API key rejected — open Settings'); return; }
    S.reconnectDelay = Math.min(S.reconnectDelay * 2, 15000);
    setTimeout(() => connect(S.sessionId), S.reconnectDelay);
  };
  ws.onmessage = (ev) => { try { onEvent(JSON.parse(ev.data)); } catch (e) { console.error(e); } };
}

function setConn(ok) {
  const dot = $('#connDot');
  dot.className = 'dot ' + (ok ? 'ok' : 'bad');
  $('#connLabel').textContent = ok ? 'connected' : 'reconnecting…';
}

function onEvent(ev) {
  switch (ev.type) {
    case 'snapshot':
      S.sessionId = ev.session_id;
      setTitle(ev.title);
      renderTranscript(ev.transcript);
      S.artifacts = ev.artifacts || [];
      renderPanel();
      setBusy(ev.busy);
      if (ev.startup_error) addSystem(ev.startup_error, true);
      (ev.pending_modals || []).forEach(showModal);
      refreshSessions();
      break;
    case 'ready':
      S.commands = ev.commands || [];
      if (ev.state) renderState(ev.state);
      break;
    case 'state':
      renderState(ev.state);
      break;
    case 'transcript_item': {
      const it = ev.item;
      if (it.role === 'user') addUser(it.text);
      else addSystem(it.text, it.is_error);
      break;
    }
    case 'assistant_delta':
      if (!S.streamEl) { S.streamBuf = ''; S.streamEl = assistantShell(); thread().appendChild(S.streamEl); }
      S.streamBuf += ev.text || '';
      paintStream();
      break;
    case 'assistant_complete': {
      const text = (ev.item && ev.item.text) || S.streamBuf;
      if (S.streamEl) {
        S.streamEl._raw = text;
        $('.md', S.streamEl).innerHTML = renderMd(text);
        S.streamEl = null; S.streamBuf = '';
      } else if (text) { addAssistant(text); }
      scrollDown();
      break;
    }
    case 'tool_started':
      if (S.streamEl) {
        S.streamEl._raw = S.streamBuf;
        $('.md', S.streamEl).innerHTML = renderMd(S.streamBuf);
        if (!S.streamBuf.trim()) S.streamEl.remove();
        S.streamEl = null; S.streamBuf = '';
      }
      S.pendingTools.push({name: ev.item.tool_name, el: addTool(ev.item)});
      break;
    case 'tool_completed': {
      const idx = S.pendingTools.map((t) => t.name).lastIndexOf(ev.item.tool_name);
      const entry = idx >= 0 ? S.pendingTools.splice(idx, 1)[0] : null;
      finishTool(entry && entry.el, ev.item);
      loadArtifacts();
      break;
    }
    case 'tasks': S.tasks = ev.tasks || []; renderPanel(); break;
    case 'busy': setBusy(ev.busy); break;
    case 'turn_complete': setBusy(false); refreshSessions(); break;
    case 'title': setTitle(ev.title); refreshSessions(); break;
    case 'clear_transcript': thread().innerHTML = ''; renderWelcome(); S.artifacts = []; renderPanel(); break;
    case 'modal_request': showModal(ev.modal); break;
    case 'modal_resolved': hideModal(ev.request_id); break;
    case 'compact_progress':
      if (ev.message) addSystem('⟳ ' + ev.message);
      break;
    case 'error': addSystem(ev.message, true); setBusy(false); break;
    case 'closed': break;
  }
}

function setTitle(t) { $('#chatTitle').textContent = t || 'New chat'; }

function setBusy(busy) {
  S.busy = !!busy;
  const btn = $('#send');
  btn.classList.toggle('stop', S.busy);
  btn.title = S.busy ? 'Stop generating' : 'Send';
  btn.innerHTML = S.busy
    ? '<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><rect x="3" y="3" width="10" height="10" rx="2"/></svg>'
    : '<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 13V3M3.5 7.5L8 3l4.5 4.5"/></svg>';
  btn.disabled = false;
}

function renderState(state) {
  if (!state) return;
  $('#modelPill').innerHTML = '';
  const model = state.model || '—';
  $('#modelPill').innerHTML = '<b>' + esc(model) + '</b>';
  $('#modePill').textContent = state.permission_mode || 'Default';
  $('#modePill').title = 'Permission mode — change it in Settings';
}

/* ---------------------------------------------------------------------
   Sessions
   ------------------------------------------------------------------- */
async function refreshSessions() {
  try {
    const data = await api('/sessions');
    S.sessions = data.sessions || [];
    renderSessions();
  } catch (e) { console.warn('session list failed', e); }
}

function timeGroup(ts) {
  const days = (Date.now() / 1000 - (ts || 0)) / 86400;
  if (days < 1) return 'Today';
  if (days < 2) return 'Yesterday';
  if (days < 8) return 'Previous 7 days';
  if (days < 31) return 'Previous 30 days';
  return 'Older';
}

function renderSessions() {
  const list = $('#convList');
  list.innerHTML = '';
  const filter = S.filter.toLowerCase();
  const rows = S.sessions.filter((s) => !filter || (s.title || '').toLowerCase().includes(filter));
  if (!rows.length) { list.innerHTML = '<div class="empty">No conversations yet</div>'; return; }
  let group = null;
  rows.forEach((s) => {
    const g = timeGroup(s.updated_at);
    if (g !== group) {
      group = g;
      const h = document.createElement('div');
      h.className = 'rail-group'; h.textContent = g;
      list.appendChild(h);
    }
    const el = document.createElement('div');
    el.className = 'conv' + (s.session_id === S.sessionId ? ' active' : '');
    el.innerHTML =
      '<span class="conv-title"></span>' +
      '<span class="conv-actions">' +
        '<button type="button" data-ren title="Rename">' +
          '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">' +
          '<path d="M11.5 2.5l2 2L6 12l-3 1 1-3z"/></svg></button>' +
        '<button type="button" data-del title="Delete">' +
          '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">' +
          '<path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.5 8h6l.5-8"/></svg></button>' +
      '</span>';
    $('.conv-title', el).textContent = s.title || 'New chat';
    el.title = (s.title || '') + '  ·  ' + (s.message_count || 0) + ' messages';
    el.onclick = (e) => { if (!e.target.closest('button')) openSession(s.session_id); };
    $('[data-ren]', el).onclick = async (e) => {
      e.stopPropagation();
      const next = prompt('Rename conversation', s.title || '');
      if (next == null) return;
      await api('/sessions/' + s.session_id, {method: 'PATCH', body: JSON.stringify({title: next})});
      if (s.session_id === S.sessionId) setTitle(next);
      refreshSessions();
    };
    $('[data-del]', el).onclick = async (e) => {
      e.stopPropagation();
      if (!confirm('Delete "' + (s.title || 'this conversation') + '"? This cannot be undone.')) return;
      await api('/sessions/' + s.session_id, {method: 'DELETE'});
      if (s.session_id === S.sessionId) { S.sessionId = null; newChat(); } else { refreshSessions(); }
    };
    list.appendChild(el);
  });
}

function openSession(id) {
  if (id === S.sessionId) return;
  thread().innerHTML = '';
  S.streamEl = null; S.streamBuf = ''; S.pendingTools = []; S.artifacts = []; S.tasks = [];
  connect(id);
  renderSessions();
  if (window.innerWidth <= 900) $('#app').classList.add('rail-hidden');
}

async function newChat() {
  try {
    const data = await api('/sessions', {method: 'POST', body: JSON.stringify({title: 'New chat'})});
    openSession(data.session.session_id);
  } catch (e) { toast('Could not start a chat: ' + e.message); }
}

/* ---------------------------------------------------------------------
   Composer
   ------------------------------------------------------------------- */
function autosize() {
  const ta = $('#input');
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 260) + 'px';
}

function send() {
  if (S.busy) { S.ws && S.ws.send(JSON.stringify({type: 'cancel'})); return; }
  const ta = $('#input');
  let text = ta.value.trim();
  if (!text && !S.attachments.length) return;
  if (S.attachments.length) {
    const paths = S.attachments.map((f) => f.path);
    const preface = paths.length === 1
      ? 'Attached file: ' + paths[0]
      : 'Attached files:\n' + paths.map((p) => '- ' + p).join('\n');
    text = preface + (text ? '\n\n' + text : '\n\nPlease review the attached file(s).');
    S.attachments = []; renderAttachments();
  }
  if (!S.ws || S.ws.readyState !== 1) { toast('Not connected — retrying'); return; }
  S.ws.send(JSON.stringify({type: 'submit', text: text}));
  ta.value = ''; autosize(); hideSlash();
  const w = $('.welcome'); if (w) w.remove();
  setBusy(true);
}

/* ---- slash command autocomplete ---- */
function updateSlash() {
  const ta = $('#input');
  const value = ta.value;
  if (!value.startsWith('/') || value.includes('\n')) return hideSlash();
  const term = value.slice(1).split(' ')[0].toLowerCase();
  if (value.trim().includes(' ')) return hideSlash();
  const items = S.commands.filter((c) => c.name.slice(1).toLowerCase().startsWith(term)).slice(0, 40);
  if (!items.length) return hideSlash();
  S.slashItems = items;
  S.slashIdx = Math.min(S.slashIdx, items.length - 1);
  const box = $('#slash');
  box.innerHTML = '';
  items.forEach((c, idx) => {
    const el = document.createElement('div');
    el.className = 'slash-item' + (idx === S.slashIdx ? ' sel' : '');
    el.innerHTML = '<code></code><span></span>';
    $('code', el).textContent = c.name;
    $('span', el).textContent = c.description || '';
    el.onmousedown = (e) => { e.preventDefault(); pickSlash(idx); };
    box.appendChild(el);
  });
  box.classList.add('show');
  const sel = box.children[S.slashIdx];
  if (sel) sel.scrollIntoView({block: 'nearest'});
}
function hideSlash() { $('#slash').classList.remove('show'); S.slashItems = []; S.slashIdx = 0; }
function pickSlash(idx) {
  const c = S.slashItems[idx];
  if (!c) return;
  $('#input').value = c.name + ' ';
  hideSlash(); autosize(); $('#input').focus();
}

/* ---- attachments ---- */
function renderAttachments() {
  const box = $('#attachments');
  box.innerHTML = '';
  S.attachments.forEach((f, idx) => {
    const el = document.createElement('div');
    el.className = 'chip';
    el.innerHTML = '<span></span><button type="button">✕</button>';
    $('span', el).textContent = f.name + ' (' + fmtSize(f.size) + ')';
    $('button', el).onclick = () => { S.attachments.splice(idx, 1); renderAttachments(); };
    box.appendChild(el);
  });
}

function fmtSize(bytes) {
  if (bytes == null) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let n = bytes, u = 0;
  while (n >= 1024 && u < units.length - 1) { n /= 1024; u++; }
  return (u === 0 ? n : n.toFixed(1)) + ' ' + units[u];
}

async function uploadFiles(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  const fd = new FormData();
  files.forEach((f) => fd.append('files', f, f.name));
  toast('Uploading ' + files.length + ' file(s)…');
  try {
    const data = await api('/uploads', {method: 'POST', body: fd});
    S.attachments.push(...(data.files || []));
    renderAttachments();
    toast('Attached — the agent can read these paths');
  } catch (e) { toast('Upload failed: ' + e.message); }
}

/* ---------------------------------------------------------------------
   Reports: analyze a deck offline, view inline, share read-only (W3.2)
   ------------------------------------------------------------------- */
const DECK_EXT = /\.(pdf|md|markdown|txt|docx)$/i;
const GATE_TONE = (g) => /PASS/.test(g) ? 'ok' : /FAIL/.test(g) ? 'bad' : 'warn';
const FILE_LABEL = [['_impact_report.html', 'Report HTML'], ['_ic_memo.html', 'IC memo'], ['_ic_memo.docx', 'IC memo .docx'],
  ['_dd_report.html', 'DD report'], ['_dd_questionnaire.docx', 'DD questions .docx'], ['_data.xlsx', 'Data .xlsx'],
  ['_data.csv', 'Data .csv'], ['_summary.json', 'Summary .json']];

function pickDeck() { S.analyzeNext = true; $('#fileInput').click(); }

async function authed(path) {
  const headers = token() ? {Authorization: 'Bearer ' + token()} : {};
  const res = await fetch(path, {headers});
  if (!res.ok) throw new Error(res.status + ' ' + res.statusText);
  return res;
}

async function downloadFile(rep, name) {
  try {
    const blob = await (await authed('/api/v1/chat/reports/' + rep.id + '/files/' + encodeURIComponent(name))).blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  } catch (e) { toast('Download failed: ' + e.message); }
}

function monogramOf(name) {
  return (name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');
}

async function analyzeFiles(fileList) {
  const f = Array.from(fileList || [])[0];
  if (!f) return;
  if (!DECK_EXT.test(f.name)) { toast('Use a PDF, Word, Markdown or text file'); return; }
  const welcome = $('.welcome', thread()); if (welcome) welcome.remove();
  const card = document.createElement('div');
  card.className = 'rcard';
  card.innerHTML = '<div class="rhead"><div class="mono">…</div><div><h4></h4><div class="rmeta"></div></div></div>' +
    '<div class="busy"><span class="spin"></span><span>Reading the deck and scoring it…</span></div>';
  $('h4', card).textContent = f.name;
  $('.rmeta', card).textContent = fmtSize(f.size);
  thread().appendChild(card); scrollDown(true);
  try {
    const fd = new FormData(); fd.append('files', f, f.name);
    const up = await api('/uploads', {method: 'POST', body: fd});
    const rep = await api('/assess', {method: 'POST', body: JSON.stringify({stored_name: up.files[0].stored_name})});
    fillReportCard(card, rep);
    S.reports.unshift(rep); renderPanel();
  } catch (e) {
    $('.busy', card).textContent = 'Analysis failed: ' + e.message;
  }
}

function fillReportCard(card, rep) {
  const s = rep.summary || {};
  card.innerHTML =
    '<div class="rhead"><div class="mono"></div><div style="min-width:0"><h4></h4><div class="rmeta"></div></div></div>' +
    '<span class="gate"></span><p class="rrec"></p>' +
    '<div class="rstats">' +
      '<div class="rstat"><div class="k">5 Dimensions</div><div class="v s5"></div></div>' +
      '<div class="rstat"><div class="k">Greenwashing risk</div><div class="v sgw"></div></div>' +
      '<div class="rstat"><div class="k">Top SDGs</div><div class="v ssdg"></div></div>' +
      '<div class="rstat"><div class="k">Evidence</div><div class="v sev"></div></div>' +
    '</div>' +
    '<div class="ractions"><button class="btn primary" data-act="view">View report</button>' +
    '<button class="btn" data-act="share">Share…</button><button class="btn" data-act="ask">Ask the agent</button></div>' +
    '<div class="ractions dls" style="margin-top:10px"></div>';
  $('.mono', card).textContent = monogramOf(s.company || rep.company);
  $('h4', card).textContent = s.company || rep.company;
  $('.rmeta', card).textContent = [s.sector, s.geography, rep.source].filter(Boolean).join(' · ');
  const gate = $('.gate', card); gate.textContent = s.gate || '—'; gate.classList.add(GATE_TONE(s.gate || ''));
  $('.rrec', card).textContent = s.recommendation || '';
  $('.s5', card).innerHTML = esc(s.five_d_score == null ? '—' : Number(s.five_d_score).toFixed(1)) + '<small> /5</small>';
  $('.sgw', card).innerHTML = esc(s.greenwashing_risk == null ? '—' : Math.round(s.greenwashing_risk)) + '<small> /100</small>';
  $('.ssdg', card).textContent = (s.top_sdgs || []).map((g) => g.goal).join(' · ') || '—';
  $('.sev', card).innerHTML = esc(s.claims || 0) + '<small> claims · </small>' +
    esc(Object.keys(s.reported_metrics || {}).length) + '<small> metrics</small>';
  card.querySelector('[data-act=view]').onclick = () => openViewer(rep);
  card.querySelector('[data-act=share]').onclick = () => openViewer(rep, true);
  card.querySelector('[data-act=ask]').onclick = () => {
    $('#input').value = 'Use assessment_id ' + rep.assessment_id + ' (' + (s.company || '') +
      '). Explain the verdict and draft the three most important questions for the founders.';
    autosize(); $('#input').focus();
  };
  const dls = $('.dls', card);
  FILE_LABEL.forEach(([suffix, label]) => {
    const name = (rep.files || []).find((n) => n.endsWith(suffix));
    if (!name) return;
    const b = document.createElement('button');
    b.className = 'dl'; b.textContent = label; b.title = name;
    b.onclick = () => downloadFile(rep, name);
    dls.appendChild(b);
  });
}

async function loadReports() {
  try { S.reports = (await api('/reports')).reports || []; renderPanel(); } catch (e) { /* non-fatal */ }
}

function viewerParams() {
  const p = new URLSearchParams({audience: $('#vAudience').value, lang: $('#vLang').value});
  if ($('#vTheme').value) p.set('theme', $('#vTheme').value);
  return p.toString();
}

function viewerUrl() {
  if (S.viewing.portfolio || S.viewing.engagements) {
    const p = new URLSearchParams(); if ($('#vTheme').value) p.set('theme', $('#vTheme').value);
    return '/api/v1/chat/' + (S.viewing.engagements ? 'engagements' : 'portfolio') + '/view?' + p.toString();
  }
  return '/api/v1/chat/reports/' + S.viewing.id + '/view?' + viewerParams();
}

function openEngagements() {
  S.viewing = {engagements: true};
  $('#viewerTitle').textContent = 'Engagements';
  $$('.report-only').forEach((el) => { el.hidden = true; });
  $('#shareBox').classList.remove('show');
  $('#viewer').classList.add('show');
  renderViewer();
  $('#vClose').focus();
}

function openPortfolio() {
  S.viewing = {portfolio: true};
  $('#viewerTitle').textContent = 'Portfolio home';
  $$('.report-only').forEach((el) => { el.hidden = true; });
  $('#shareBox').classList.remove('show');
  $('#viewer').classList.add('show');
  renderViewer();
  $('#vClose').focus();
}

async function renderViewer() {
  const rep = S.viewing; if (!rep) return;
  const frame = $('#viewerFrame');
  try {
    frame.srcdoc = await (await authed(viewerUrl())).text();
  } catch (e) { frame.srcdoc = '<p style="font:15px system-ui;margin:2rem">Could not load the report: ' + esc(e.message) + '</p>'; }
}

function openViewer(rep, share) {
  S.viewing = rep;
  $$('.report-only').forEach((el) => { el.hidden = false; });
  $('#viewerTitle').textContent = (rep.summary && rep.summary.company) || rep.company;
  $('#shareBox').classList.remove('show');
  $('#viewer').classList.add('show');
  renderViewer();
  if (share) createShare();
  $('#vClose').focus();
}

function closeViewer() { $('#viewer').classList.remove('show'); S.viewing = null; $('#viewerFrame').srcdoc = ''; }

async function openViewerTab() {
  try {
    const html = await (await authed(viewerUrl())).text();
    window.open(URL.createObjectURL(new Blob([html], {type: 'text/html'})), '_blank', 'noopener');
  } catch (e) { toast('Could not open: ' + e.message); }
}

async function createShare() {
  const rep = S.viewing; if (!rep) return;
  let audience = $('#vAudience').value;
  if (audience === 'full' || audience === 'ic') audience = 'lp';   /* never share internal views by default */
  $('#shareAudience').value = audience;
  $('#shareBox').classList.add('show');
  await refreshShare();
}

async function refreshShare() {
  const rep = S.viewing; if (!rep) return;
  try {
    const out = await api('/reports/' + rep.id + '/share', {method: 'POST', body: JSON.stringify({
      audience: $('#shareAudience').value, lang: $('#vLang').value, days: Number($('#shareDays').value)})});
    $('#shareUrl').value = location.origin + out.path;
    $('#shareExp').textContent = 'Read-only · expires ' + new Date(out.expires_at * 1000).toLocaleDateString();
  } catch (e) { toast('Share failed: ' + e.message); }
}

/* ---------------------------------------------------------------------
   Right panel
   ------------------------------------------------------------------- */
async function loadArtifacts() {
  if (!S.sessionId) return;
  try {
    const data = await api('/artifacts?session_id=' + encodeURIComponent(S.sessionId));
    S.artifacts = data.artifacts || [];
    renderPanel();
  } catch (e) { /* non-fatal */ }
}

function renderPanel() {
  $$('.panel-tabs button').forEach((b) => b.classList.toggle('on', b.dataset.tab === S.tab));
  const body = $('#panelBody');
  body.innerHTML = '';
  if (S.tab === 'reports') {
    if (S.reports.length) {
      const home = document.createElement('button');
      home.className = 'btn'; home.style.cssText = 'width:100%;margin-bottom:8px';
      home.textContent = 'Open portfolio home';
      home.onclick = openPortfolio;
      body.appendChild(home);
    }
    const engs = document.createElement('button');
    engs.className = 'btn'; engs.style.cssText = 'width:100%;margin-bottom:8px';
    engs.textContent = 'Open engagements';
    engs.onclick = openEngagements;
    body.appendChild(engs);
    if (!S.reports.length) {
      const empty = document.createElement('div');
      empty.className = 'empty';
      empty.textContent = 'Analyze a pitch deck from the welcome screen — reports you create appear here.';
      body.appendChild(empty);
      return;
    }
    S.reports.forEach((r) => {
      const s = r.summary || {};
      const el = document.createElement('div');
      el.className = 'rep'; el.setAttribute('role', 'button'); el.tabIndex = 0;
      el.innerHTML = '<div style="flex:1;min-width:0"><div class="fname"></div><div class="fmeta"></div></div><span class="gate"></span>';
      $('.fname', el).textContent = s.company || r.company;
      $('.fmeta', el).textContent = new Date((r.created_at || 0) * 1000).toLocaleString();
      const g = $('.gate', el); g.textContent = (s.gate || '').replace('INSUFFICIENT EVIDENCE', 'NOT READY'); g.classList.add(GATE_TONE(s.gate || ''));
      el.onclick = () => openViewer(r);
      el.onkeydown = (e) => { if (e.key === 'Enter') openViewer(r); };
      body.appendChild(el);
    });
    return;
  }
  if (S.tab === 'artifacts') {
    if (!S.artifacts.length) {
      body.innerHTML = '<div class="empty">Files the agent writes during this conversation appear here.</div>';
      return;
    }
    S.artifacts.slice().reverse().forEach((a) => {
      const el = document.createElement('div');
      el.className = 'file';
      el.innerHTML =
        '<div style="flex:1;min-width:0"><div class="fname"></div><div class="fmeta"></div></div>' +
        '<a title="Download" target="_blank">' +
          '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">' +
          '<path d="M8 2v8M4.5 7L8 10.5 11.5 7M3 13h10"/></svg></a>';
      $('.fname', el).textContent = a.name;
      $('.fmeta', el).textContent = (a.exists ? fmtSize(a.size) : 'missing') + ' · ' + a.tool;
      $('a', el).href = '/api/v1/chat/artifacts/download?path=' + encodeURIComponent(a.path);
      el.title = a.path;
      body.appendChild(el);
    });
  } else {
    if (!S.tasks.length) {
      body.innerHTML = '<div class="empty">Task list from the agent appears here while it works.</div>';
      return;
    }
    S.tasks.forEach((t) => {
      const el = document.createElement('div');
      el.className = 'task';
      el.innerHTML = '<span class="tstat"></span><span></span>';
      const st = $('.tstat', el);
      st.textContent = (t.status || '').replace('_', ' ');
      st.classList.add(t.status || '');
      $('span:last-child', el).textContent = t.description || t.type;
      body.appendChild(el);
    });
  }
}

/* ---------------------------------------------------------------------
   Modals: permission / question
   ------------------------------------------------------------------- */
function showModal(modal) {
  if (!modal) return;
  S.modalQueue = S.modalQueue.filter((m) => m.request_id !== modal.request_id);
  S.modalQueue.push(modal);
  paintModal();
}
function hideModal(requestId) {
  S.modalQueue = S.modalQueue.filter((m) => m.request_id !== requestId);
  paintModal();
}
function paintModal() {
  const ov = $('#promptOverlay');
  const modal = S.modalQueue[0];
  if (!modal) { ov.classList.remove('show'); return; }
  const body = $('#promptBody'), foot = $('#promptFoot');
  body.innerHTML = ''; foot.innerHTML = '';
  if (modal.kind === 'permission') {
    $('#promptTitle').textContent = 'Permission required';
    const p = document.createElement('p');
    p.innerHTML = 'The agent wants to run <span class="perm-tool"></span>.';
    $('.perm-tool', p).textContent = modal.tool_name;
    body.appendChild(p);
    if (modal.reason) {
      const pre = document.createElement('div');
      pre.className = 'perm-reason'; pre.textContent = modal.reason;
      body.appendChild(pre);
    }
    const deny = document.createElement('button');
    deny.className = 'btn'; deny.textContent = 'Deny';
    deny.onclick = () => { respondPermission(modal.request_id, false); };
    const allow = document.createElement('button');
    allow.className = 'btn primary'; allow.textContent = 'Allow';
    allow.onclick = () => { respondPermission(modal.request_id, true); };
    foot.append(deny, allow);
    setTimeout(() => allow.focus(), 30);
  } else {
    $('#promptTitle').textContent = 'The agent has a question';
    const q = document.createElement('p');
    q.style.whiteSpace = 'pre-wrap';
    q.textContent = modal.question || '';
    const field = document.createElement('div');
    field.className = 'field';
    field.innerHTML = '<label>Your answer</label><input id="answerInput" autocomplete="off">';
    body.append(q, field);
    const submit = document.createElement('button');
    submit.className = 'btn primary'; submit.textContent = 'Send';
    submit.onclick = () => {
      S.ws.send(JSON.stringify({type: 'question_response', request_id: modal.request_id, answer: $('#answerInput').value}));
      hideModal(modal.request_id);
    };
    foot.appendChild(submit);
    setTimeout(() => {
      const inp = $('#answerInput');
      if (inp) { inp.focus(); inp.onkeydown = (e) => { if (e.key === 'Enter') submit.click(); }; }
    }, 30);
  }
  ov.classList.add('show');
}
function respondPermission(requestId, allowed) {
  S.ws.send(JSON.stringify({type: 'permission_response', request_id: requestId, allowed: allowed}));
  hideModal(requestId);
}

/* ---------------------------------------------------------------------
   Settings
   ------------------------------------------------------------------- */
async function openSettings() {
  $('#settingsOverlay').classList.add('show');
  const body = $('#settingsBody');
  body.innerHTML = '<div class="empty">Loading…</div>';
  try {
    const p = await api('/providers');
    S.provider = p;
    renderSettings(p);
  } catch (e) {
    body.innerHTML = '<div class="note">Could not load provider settings: ' + esc(e.message) + '</div>';
  }
}

function renderSettings(p) {
  const body = $('#settingsBody');
  const base = location.origin;
  const GROUPS = [
    ['Anthropic Claude', ['claude-api', 'claude-subscription']],
    ['Hosted APIs', ['openai', 'openrouter', 'deepseek', 'dashscope', 'gemini', 'moonshot', 'mistral', 'xai', 'groq', 'together', 'naxtclaude']],
    ['Subscriptions', ['codex', 'copilot']],
    ['Local & custom', ['ollama', 'custom', 'openai-compatible']],
  ];
  const optFor = (pr) => '<option value="' + esc(pr.name) + '"' + (pr.active ? ' selected' : '') + '>' +
    esc(pr.label) + (pr.configured ? '  ✓' : pr.uses_api_key ? '  — add key' : '') + '</option>';
  const placed = new Set();
  let opts = GROUPS.map(([label, names]) => {
    const inner = names.map((n) => p.profiles.find((pr) => pr.name === n)).filter(Boolean)
      .map((pr) => { placed.add(pr.name); return optFor(pr); }).join('');
    return inner ? '<optgroup label="' + esc(label) + '">' + inner + '</optgroup>' : '';
  }).join('');
  const mine = p.profiles.filter((pr) => !placed.has(pr.name));
  if (mine.length) opts += '<optgroup label="Your profiles">' + mine.map(optFor).join('') + '</optgroup>';

  body.innerHTML =
    '<div class="sec">Model provider</div>' +
    '<div class="field"><label>Provider profile</label>' +
      '<div class="desc">Which LLM endpoint the agent talks to. Saved to <code>~/.openharness/settings.json</code>.</div>' +
      '<select id="setProfile">' + opts + '</select></div>' +
    '<div class="row">' +
      '<div class="field"><label>Model</label>' +
        '<input id="setModel" list="modelOptions" placeholder="e.g. claude-sonnet-5-5">' +
        '<datalist id="modelOptions"></datalist></div>' +
      '<div class="field"><label>API format</label>' +
        '<select id="setFormat">' +
          ['anthropic', 'openai', 'copilot'].map((f) => '<option value="' + f + '">' + f + '</option>').join('') +
        '</select></div>' +
    '</div>' +
    '<div class="field"><label>Base URL</label>' +
      '<div class="desc">Pre-filled for each provider. For your own server pick <b>Custom endpoint</b> and enter any OpenAI-compatible URL (vLLM, LiteLLM, LM Studio, an internal gateway); set API format to <code>anthropic</code> for Anthropic-compatible ones.</div>' +
      '<input id="setBaseUrl" placeholder="https://api.openai.com/v1"></div>' +
    '<div class="field"><label>API key</label>' +
      '<div class="desc" id="keyHint">Stored in the local credential store. Leave blank to keep the existing key.</div>' +
      '<input id="setApiKey" type="password" placeholder="sk-… (write-only)"></div>' +
    '<div class="modal-foot" style="padding:0;border:none;justify-content:flex-start">' +
      '<button class="btn primary" id="saveProvider">Save provider</button>' +
      '<span id="provStatus" style="font-size:12px;color:var(--text-faint);align-self:center"></span>' +
    '</div>' +

    '<div class="sec">Interface</div>' +
    '<div class="row">' +
      '<div class="field"><label>Theme</label><select id="setTheme">' +
        '<option value="light">Light</option><option value="dark">Dark</option><option value="system">Follow system</option>' +
      '</select></div>' +
      '<div class="field"><label>Send with</label><select id="setSend">' +
        '<option value="enter">Enter (Shift+Enter = newline)</option>' +
        '<option value="mod">Ctrl/⌘+Enter</option>' +
      '</select></div>' +
    '</div>' +

    '<div class="sec">Server &amp; REST API</div>' +
    '<div class="field"><label>API base URL</label><input value="' + esc(base) + '" readonly></div>' +
    '<div class="field"><label>Bearer token</label>' +
      '<div class="desc">Only needed when the server runs with <code>IMPACT_VISION_API_KEY</code> set. Stored in this browser.</div>' +
      '<input id="setToken" type="password" placeholder="IMPACT_VISION_API_KEY" value="' + esc(token()) + '"></div>' +
    '<div class="note">Same server, other surfaces:<br>' +
      '· <a href="/docs" target="_blank">/docs</a> — OpenAPI explorer for the 26-tool REST gateway<br>' +
      '· <a href="/console" target="_blank">/console</a> — the tool-form power console<br>' +
      '· <code>' + esc(base) + '/api/v1/*</code> — call the tools directly<br>' +
      '· Workspace: <code>' + esc((S.bootstrap && S.bootstrap.workspace) || '') + '</code></div>';

  const active = p.profiles.find((pr) => pr.active) || {};
  const claudeAliases = (p.claude_models || []).map((m) => m.value);
  const fillProfile = (pr) => {
    const models = (pr.models || []).concat(pr.api_format === 'anthropic' ? claudeAliases : []);
    $('#modelOptions').innerHTML = models.map((m) => '<option value="' + esc(m) + '">').join('');
    $('#setModel').placeholder = models.length ? 'e.g. ' + models[0] : 'model name';
    $('#setBaseUrl').placeholder = pr.name === 'custom' ? 'https://your-server/v1' : 'provider default';
    const env = pr.key_env ? ' Or set <code>' + esc(pr.key_env) + '</code> before starting.' : '';
    $('#keyHint').innerHTML = pr.local
      ? 'Not needed for a local server.'
      : 'Stored in the local credential store' + (pr.configured ? ' — a key is already set; leave blank to keep it.' : '.') + env;
    $('#setApiKey').disabled = !!pr.local;
  };
  $('#setModel').value = p.model || '';
  $('#setBaseUrl').value = p.base_url || '';
  $('#setFormat').value = p.api_format || active.api_format || 'anthropic';
  fillProfile(active);
  $('#setTheme').value = localStorage.getItem('iv_theme') || 'system';
  $('#setSend').value = localStorage.getItem('iv_send') || 'enter';

  $('#setProfile').onchange = () => {
    const pr = p.profiles.find((x) => x.name === $('#setProfile').value);
    if (!pr) return;
    $('#setModel').value = pr.model || '';
    $('#setBaseUrl').value = pr.base_url || '';
    $('#setFormat').value = pr.api_format || 'anthropic';
    fillProfile(pr);
  };
  $('#setTheme').onchange = () => { localStorage.setItem('iv_theme', $('#setTheme').value); applyTheme(); };
  $('#setSend').onchange = () => { localStorage.setItem('iv_send', $('#setSend').value); };
  $('#setToken').onchange = () => { setToken($('#setToken').value.trim()); toast('Token saved — reconnecting'); connect(S.sessionId); };

  $('#saveProvider').onclick = async () => {
    const status = $('#provStatus');
    status.textContent = 'Saving…';
    try {
      const payload = {
        profile: $('#setProfile').value,
        model: $('#setModel').value.trim() || null,
        base_url: $('#setBaseUrl').value.trim(),
        api_format: $('#setFormat').value,
        make_active: true,
      };
      const key = $('#setApiKey').value.trim();
      if (key) payload.api_key = key;
      S.provider = await api('/providers', {method: 'POST', body: JSON.stringify(payload)});
      $('#setApiKey').value = '';
      status.textContent = 'Saved. New chats use these settings.';
      toast('Provider updated');
    } catch (e) {
      status.textContent = '';
      toast('Save failed: ' + e.message);
    }
  };
}

function applyTheme() {
  const pref = localStorage.getItem('iv_theme') || 'system';
  const dark = pref === 'dark' || (pref === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
}

/* ---------------------------------------------------------------------
   Boot
   ------------------------------------------------------------------- */
async function boot() {
  applyTheme();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);

  const ta = $('#input');
  ta.addEventListener('input', () => { autosize(); updateSlash(); });
  ta.addEventListener('keydown', (e) => {
    if ($('#slash').classList.contains('show')) {
      if (e.key === 'ArrowDown') { e.preventDefault(); S.slashIdx = (S.slashIdx + 1) % S.slashItems.length; updateSlash(); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); S.slashIdx = (S.slashIdx - 1 + S.slashItems.length) % S.slashItems.length; updateSlash(); return; }
      if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) { e.preventDefault(); pickSlash(S.slashIdx); return; }
      if (e.key === 'Escape') { e.preventDefault(); hideSlash(); return; }
    }
    const mode = localStorage.getItem('iv_send') || 'enter';
    if (e.key === 'Enter') {
      if (mode === 'enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) { e.preventDefault(); send(); }
      else if (mode === 'mod' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); }
    }
  });

  $('#send').onclick = send;
  $('#newChat').onclick = newChat;
  $('#toggleRail').onclick = () => $('#app').classList.toggle('rail-hidden');
  $('#togglePanel').onclick = () => {
    $('#app').classList.toggle('panel-open');
    $('#togglePanel').classList.toggle('on', $('#app').classList.contains('panel-open'));
    loadArtifacts();
  };
  $('#openSettings').onclick = openSettings;
  $('#settingsClose').onclick = () => $('#settingsOverlay').classList.remove('show');
  $('#settingsOverlay').onclick = (e) => { if (e.target.id === 'settingsOverlay') e.currentTarget.classList.remove('show'); };
  $('#railSearch').oninput = (e) => { S.filter = e.target.value; renderSessions(); };
  $('#attachBtn').onclick = () => $('#fileInput').click();
  $('#fileInput').onchange = (e) => {
    if (S.analyzeNext) analyzeFiles(e.target.files); else uploadFiles(e.target.files);
    S.analyzeNext = false; e.target.value = '';
  };
  $('#vAudience').onchange = renderViewer; $('#vLang').onchange = renderViewer; $('#vTheme').onchange = renderViewer;
  $('#vClose').onclick = closeViewer; $('#vOpen').onclick = openViewerTab; $('#vShare').onclick = createShare;
  $('#shareAudience').onchange = refreshShare; $('#shareDays').onchange = refreshShare;
  $('#shareCopy').onclick = async () => {
    try { await navigator.clipboard.writeText($('#shareUrl').value); toast('Link copied'); }
    catch (e) { $('#shareUrl').select(); toast('Press Ctrl+C to copy'); }
  };
  const thr = thread();
  ['dragenter', 'dragover'].forEach((t) => thr.addEventListener(t, (e) => { if ($('.welcome', thr)) e.preventDefault(); }));
  thr.addEventListener('drop', (e) => {
    if (!$('.welcome', thr) || !e.dataTransfer || !e.dataTransfer.files.length) return;
    e.preventDefault(); analyzeFiles(e.dataTransfer.files);
  });
  $$('.panel-tabs button').forEach((b) => { b.onclick = () => { S.tab = b.dataset.tab; renderPanel(); }; });
  $('#themeBtn').onclick = () => {
    const now = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('iv_theme', now); applyTheme();
  };

  const box = $('#inputBox');
  ['dragenter', 'dragover'].forEach((t) => box.addEventListener(t, (e) => {
    e.preventDefault(); box.classList.add('drag');
  }));
  ['dragleave', 'drop'].forEach((t) => box.addEventListener(t, (e) => {
    e.preventDefault(); if (t === 'dragleave' && box.contains(e.relatedTarget)) return; box.classList.remove('drag');
  }));
  box.addEventListener('drop', (e) => { if (e.dataTransfer && e.dataTransfer.files) uploadFiles(e.dataTransfer.files); });

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); $('#railSearch').focus(); }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'o') { e.preventDefault(); newChat(); }
    if (e.key === 'Escape') {
      if ($('#viewer').classList.contains('show')) { closeViewer(); return; }
      if ($('#settingsOverlay').classList.contains('show')) $('#settingsOverlay').classList.remove('show');
      else if (S.busy) S.ws && S.ws.send(JSON.stringify({type: 'cancel'}));
    }
  });

  try {
    const data = await api('/bootstrap');
    S.bootstrap = data;
    S.sessions = data.sessions || [];
    S.provider = data.provider;
    $('#version').textContent = 'v' + (data.version || '');
    renderSessions();
    if (data.provider) renderState({model: data.provider.model, permission_mode: data.provider.permission_mode});
    const last = localStorage.getItem('iv_last_session');
    const known = S.sessions.find((s) => s.session_id === last);
    connect(known ? last : null);
    loadReports();
  } catch (e) {
    addSystem('Could not reach the Impact Vision server: ' + e.message +
      '\nIf the server requires an API key, open Settings and paste it.', true);
    connect(null);
  }

  setInterval(() => {
    if (S.sessionId) localStorage.setItem('iv_last_session', S.sessionId);
    if (S.ws && S.ws.readyState === 1) S.ws.send(JSON.stringify({type: 'ping'}));
  }, 25000);

  autosize();
  ta.focus();
}

boot();
"""


_HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>Impact Vision</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%232f6f4f'/><text x='16' y='22' font-size='15' font-family='sans-serif' font-weight='bold' fill='white' text-anchor='middle'>IV</text></svg>">
<style>/*__CSS__*/</style>
</head>
<body>
<div class="app" id="app">

  <!-- ============ left rail ============ -->
  <aside class="rail">
    <div class="rail-head">
      <div class="brand">
        <span class="brand-mark">IV</span>
        <span class="brand-name">Impact Vision</span>
        <span class="brand-ver" id="version"></span>
      </div>
      <button class="btn-new" id="newChat" title="New chat (Ctrl/⌘+Shift+O)">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M8 3.5v9M3.5 8h9"/></svg>
        New chat
      </button>
      <div class="rail-search">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg>
        <input id="railSearch" placeholder="Search chats  (Ctrl/⌘+K)" autocomplete="off">
      </div>
    </div>
    <div class="rail-list" id="convList"></div>
    <div class="rail-foot">
      <button id="openSettings" title="Settings">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="2.2"/><path d="M8 1.5v1.8M8 12.7v1.8M14.5 8h-1.8M3.3 8H1.5M12.6 3.4l-1.3 1.3M4.7 11.3l-1.3 1.3M12.6 12.6l-1.3-1.3M4.7 4.7L3.4 3.4"/></svg>
        Settings
      </button>
      <button id="themeBtn" title="Toggle theme">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 9.5A5.5 5.5 0 0 1 6.5 3a5.5 5.5 0 1 0 6.5 6.5z"/></svg>
        Theme
      </button>
    </div>
  </aside>

  <!-- ============ main column ============ -->
  <div class="main">
    <div class="topbar">
      <button class="icon-btn" id="toggleRail" title="Toggle sidebar">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="3" width="12" height="10" rx="2"/><path d="M6 3v10"/></svg>
      </button>
      <span class="chat-title" id="chatTitle">New chat</span>
      <span class="pill" id="modelPill"><b>—</b></span>
      <span class="pill" id="modePill">Default</span>
      <span class="pill"><span class="dot" id="connDot"></span><span id="connLabel">connecting…</span></span>
      <button class="icon-btn" id="togglePanel" title="Artifacts &amp; tasks">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="3" width="12" height="10" rx="2"/><path d="M10 3v10"/></svg>
      </button>
    </div>

    <div class="scroll" id="scroll"><div class="thread" id="thread"></div></div>

    <div class="composer-wrap">
      <div class="composer">
        <div class="slash" id="slash"></div>
        <div class="attachments" id="attachments"></div>
        <div class="input-box" id="inputBox">
          <textarea id="input" rows="1" placeholder="Ask about impact measurement, IRIS+ metrics, SDG alignment, or a portfolio company…  ( / for commands )"></textarea>
          <div class="input-row">
            <button class="icon-btn" id="attachBtn" title="Attach files">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M11 5.5L6.2 10.3a1.7 1.7 0 0 0 2.4 2.4l5-5a3.2 3.2 0 0 0-4.5-4.5l-5 5a4.7 4.7 0 0 0 6.6 6.6l4.1-4.1"/></svg>
            </button>
            <input type="file" id="fileInput" multiple hidden>
            <span class="grow"></span>
            <button class="send" id="send" title="Send"></button>
          </div>
        </div>
        <div class="hint">Impact Vision runs tools on your machine — review actions it asks permission for. Esc stops a running turn.</div>
      </div>
    </div>
  </div>

  <!-- ============ right panel ============ -->
  <aside class="panel">
    <div class="panel-head">Workspace</div>
    <div class="panel-tabs">
      <button data-tab="reports">Reports</button>
      <button data-tab="artifacts" class="on">Artifacts</button>
      <button data-tab="tasks">Tasks</button>
    </div>
    <div class="panel-body" id="panelBody"></div>
  </aside>
</div>

<!-- ============ permission / question modal ============ -->
<div class="overlay" id="promptOverlay">
  <div class="modal">
    <div class="modal-head"><h3 id="promptTitle">Permission required</h3></div>
    <div class="modal-body" id="promptBody"></div>
    <div class="modal-foot" id="promptFoot"></div>
  </div>
</div>

<!-- ============ settings modal ============ -->
<div class="overlay" id="settingsOverlay">
  <div class="modal wide">
    <div class="modal-head">
      <h3>Settings</h3>
      <button class="icon-btn" id="settingsClose">✕</button>
    </div>
    <div class="modal-body" id="settingsBody"></div>
  </div>
</div>

<!-- ============ report viewer (W3.2) ============ -->
<div class="viewer" id="viewer" role="dialog" aria-modal="true" aria-labelledby="viewerTitle">
  <div class="viewer-bar">
    <h3 id="viewerTitle">Report</h3>
    <label class="report-only">Audience <select id="vAudience">
      <option value="full">Full</option><option value="ic">Investment committee</option>
      <option value="lp">LP</option><option value="regulator">Regulator</option><option value="public">Public</option>
    </select></label>
    <label class="report-only">Language <select id="vLang">
      <option value="en">English</option><option value="zh-HK">繁體中文</option><option value="zh-CN">简体中文</option>
    </select></label>
    <label>Theme <select id="vTheme"><option value="">Auto</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
    <button class="btn" id="vOpen" type="button">Open in new tab</button>
    <button class="btn primary report-only" id="vShare" type="button">Share…</button>
    <button class="btn" id="vClose" type="button" aria-label="Close report">Close</button>
  </div>
  <div class="sharebox" id="shareBox">
    <label>Edition <select id="shareAudience">
      <option value="lp">LP</option><option value="public">Public</option><option value="regulator">Regulator</option>
      <option value="ic">Investment committee</option><option value="full">Full (internal)</option>
    </select></label>
    <label>Valid for <select id="shareDays"><option value="7">7 days</option><option value="14" selected>14 days</option>
      <option value="30">30 days</option><option value="90">90 days</option></select></label>
    <input id="shareUrl" readonly aria-label="Share link">
    <button class="btn" id="shareCopy" type="button">Copy link</button>
    <span id="shareExp" style="color:var(--text-dim)"></span>
  </div>
  <iframe id="viewerFrame" title="Report preview" sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"></iframe>
</div>

<div class="toast" id="toast"></div>
<script>/*__JS__*/</script>
</body>
</html>"""


def render_chat_html() -> str:
    """Return the complete, self-contained chat UI document."""
    return _HTML.replace("/*__CSS__*/", _CSS).replace("/*__JS__*/", _JS)


def _require_fastapi() -> None:
    if _FASTAPI_IMPORT_ERROR is not None:  # pragma: no cover - optional dependency
        raise ImportError(
            "FastAPI is required for the web chat UI. Install with: pip install fastapi uvicorn"
        ) from _FASTAPI_IMPORT_ERROR


def chat_ui_router() -> Any:
    """Return a FastAPI router serving the chat UI at ``/`` and ``/chat``."""
    _require_fastapi()
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def _root() -> str:
        return render_chat_html()

    @router.get("/chat", response_class=HTMLResponse, include_in_schema=False)
    async def _chat() -> str:
        return render_chat_html()

    return router


__all__ = ["chat_ui_router", "render_chat_html"]
