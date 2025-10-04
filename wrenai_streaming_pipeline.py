"""
title: WrenAI Database Query Pipeline (Streaming via /stream/ask — single call, no history, ignore UI auto-prompts)
author: Javad Asoodeh
date: 2025-10-04
version: 4.4
license: MIT
description: Calls /stream/ask exactly once for real user questions. Ignores Open-WebUI synthetic prompts (follow-ups, auto-title, etc.). Chart generation kept as your working version (Vega Editor link + PNG/SVG HTML).
requirements: requests, pydantic
"""

import os, json, logging, requests
from typing import List, Union, Generator, Iterator, Optional, Dict
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)


class Pipeline:
    class Valves(BaseModel):
        WREN_UI_URL: str
        WREN_UI_TIMEOUT: int = 600
        MAX_ROWS: int = 500
        MODEL_NAME: str = "WrenAI Database Query (Streaming)"

    def __init__(self):
        # session-scoped state (per Open-WebUI chat)
        self.thread_ids: Dict[str, str] = {}        # { chat_id: wren_thread_id }
        self.last_sql: Dict[str, str] = {}          # { chat_id: last_success_sql }
        self.last_question: Dict[str, str] = {}     # { chat_id: last_effective_question }

        self.valves = self.Valves(
            **{
                "pipelines": ["*"],
                "WREN_UI_URL": os.getenv("WREN_UI_URL", "http://wren-ui:3000"),
                "WREN_UI_TIMEOUT": int(os.getenv("WREN_UI_TIMEOUT", "600")),
                "MAX_ROWS": int(os.getenv("MAX_ROWS", "500")),
                "MODEL_NAME": os.getenv("MODEL_NAME", "WrenAI Database Query (Streaming)"),
            }
        )
        self._name = self.valves.MODEL_NAME

    # ---------------- Lifecycle ----------------
    @property
    def name(self): return self.valves.MODEL_NAME
    @name.setter
    def name(self, value): self._name = value

    async def on_startup(self):
        self.name = self.valves.MODEL_NAME
        logging.info(f"WrenAI Pipeline started. Base URL: {self.valves.WREN_UI_URL}")

    async def on_shutdown(self):
        logging.info("WrenAI Pipeline down")

    # ---------------- Thread helpers ----------------
    def get_thread_id_for_chat(self, chat_id: str) -> Optional[str]:
        return self.thread_ids.get(chat_id)

    def set_thread_id_for_chat(self, chat_id: str, thread_id: str):
        self.thread_ids[chat_id] = thread_id
        logging.info(f"Stored thread ID {thread_id} for chat {chat_id}")

    # ---------------- HTTP helpers ----------------
    def _headers(self):
        return {
            "Accept": "application/json; charset=utf-8",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "WrenAI-OpenWebUI-Pipeline/4.4",
            "Connection": "keep-alive",
        }

    def _post_json(self, path: str, payload: dict, timeout: Optional[int] = None):
        url = f"{self.valves.WREN_UI_URL}{path}"
        r = requests.post(url, json=payload, headers=self._headers(), timeout=(30, timeout or self.valves.WREN_UI_TIMEOUT))
        if r.status_code >= 400:
            try:
                return r.json()
            except Exception:
                r.raise_for_status()
        return r.json()

    def _post_sse(self, path: str, payload: dict):
        """Single streaming call site."""
        url = f"{self.valves.WREN_UI_URL}{path}"
        with requests.post(
            url,
            json=payload,
            headers={**self._headers(), "Accept": "text/event-stream"},
            stream=True,
            timeout=(30, self.valves.WREN_UI_TIMEOUT),
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if not data:
                        continue
                    try:
                        yield json.loads(data)
                    except Exception:
                        yield {"type": "raw", "data": data}

    # ---------------- Formatting helpers ----------------
    def _md_table(self, records: List[dict], columns: List[dict], max_rows: int) -> str:
        if not records or not columns:
            return "No data available."
        names = [c["name"] for c in columns]
        head = "| " + " | ".join(names) + " |\n| " + " | ".join(["---"] * len(names)) + " |\n"
        lines = []
        for rec in records[:max_rows]:
            vals = []
            for n in names:
                v = rec.get(n, "")
                if isinstance(v, float):
                    vals.append(f"{v:,.2f}" if abs(v) >= 1000 else f"{v:.2f}")
                elif isinstance(v, int):
                    vals.append(f"{v:,}")
                else:
                    vals.append("" if v is None else str(v))
            lines.append("| " + " | ".join(vals) + " |")
        extra = (
            f"\n\n**Total rows:** {len(records):,} (showing first {max_rows:,})"
            if len(records) > max_rows
            else f"\n\n**Total rows:** {len(records):,}"
        )
        return head + "\n".join(lines) + extra

    def _clean(self, s: Optional[str]) -> str:
        if not s:
            return ""
        return (
            s.replace("\\n", "\n")
             .replace('\\"', '"')
             .replace("\\'", "'")
             .replace('\\\\', '\\')
        )

    # ---------------- Vega (working block) ----------------
    _base64_uri = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-$"
    def _lz_char_from_int(self, a: int) -> str: return self._base64_uri[a]

    def _lz_compress_to_uri_component(self, uncompressed: str) -> str:
        """Minimal Python adaptation of LZ-String compressToEncodedURIComponent."""
        if uncompressed is None: return ""
        dict_map, dict_to_create = {}, {}
        wc = ""
        enlarge_in, dict_size, num_bits = 2, 3, 2
        data, data_val, data_position = [], 0, 0
        def write_bits(value, numbits):
            nonlocal data_val, data_position, data
            for _ in range(numbits):
                data_val = (data_val << 1) | (value & 1); value >>= 1
                if data_position == 5:
                    data.append(self._lz_char_from_int(data_val)); data_val = 0; data_position = 0
                else:
                    data_position += 1
        for cc in uncompressed:
            if cc not in dict_map:
                dict_map[cc] = dict_size; dict_size += 1; dict_to_create[cc] = True
            wc2 = wc + cc
            if wc2 in dict_map:
                wc = wc2
            else:
                if wc in dict_to_create:
                    if ord(wc[0]) < 256: write_bits(0, num_bits); write_bits(ord(wc[0]), 8)
                    else: write_bits(1, num_bits); write_bits(ord(wc[0]), 16)
                    enlarge_in -= 1
                    if enlarge_in == 0: enlarge_in, num_bits = 2 ** num_bits, num_bits + 1
                    del dict_to_create[wc]
                else:
                    write_bits(dict_map[wc], num_bits); enlarge_in -= 1
                    if enlarge_in == 0: enlarge_in, num_bits = 2 ** num_bits, num_bits + 1
                dict_map[wc2] = dict_size; dict_size += 1; wc = cc
        if wc:
            if wc in dict_to_create:
                if ord(wc[0]) < 256: write_bits(0, num_bits); write_bits(ord(wc[0]), 8)
                else: write_bits(1, num_bits); write_bits(ord(wc[0]), 16)
                del dict_to_create[wc]
            else:
                write_bits(dict_map[wc], num_bits)
            enlarge_in -= 1
            if enlarge_in == 0: enlarge_in, num_bits = 2 ** num_bits, num_bits + 1
        write_bits(2, num_bits)
        while True:
            data_val <<= 1
            if data_position == 5:
                data.append(self._lz_char_from_int(data_val)); break
            else:
                data_position += 1
        return "".join(data)

    def build_vega_editor_url(self, vega_spec: dict, mode: str = "vega-lite") -> str:
        payload = {"mode": mode, "spec": vega_spec}
        encoded = self._lz_compress_to_uri_component(json.dumps(payload, ensure_ascii=False))
        return f"https://vega.github.io/editor/#/url/vega-lite/{encoded}"

    def build_standalone_html(self, vega_spec: dict, title: str = "Vega-Lite Chart") -> str:
        spec_json = json.dumps(vega_spec, ensure_ascii=False, indent=2)
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin:0; padding:16px; background:#f9fafb; }}
    .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    .bar {{ display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin-bottom:20px; }}
    .bar a {{ text-decoration:none; padding:10px 16px; border-radius:8px; border:1px solid #d0d7de; background:#f6f8fa; font-size:14px; font-weight:500; transition:all 0.2s; }}
    .bar a:hover {{ background:#1570EF; color:white; border-color:#1570EF; }}
    #vis {{ width:100%; height:500px; margin-top:16px; }}
    .hint {{ color:#6b7280; font-size:12px; margin-top:12px; font-style:italic; }}
    .error {{ color:#b91c1c; background:#fee; padding:16px; border-radius:8px; border:1px solid #fcc; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="bar">
      <a href="#" id="savePNG">🖼️ Save as PNG</a>
      <a href="#" id="saveSVG">📄 Save as SVG</a>
    </div>
    <div id="vis"></div>
    <div class="hint">Tip: Hover over elements to see values. Click action buttons above to export.</div>
  </div>

  <script type="text/javascript">
    const spec = {spec_json};
    vegaEmbed('#vis', spec, {{ actions: false, renderer: 'canvas' }}).then(result => {{
      const view = result.view;
      document.getElementById('savePNG').addEventListener('click', e => {{
        e.preventDefault();
        view.toImageURL('png').then(url => {{
          const a = document.createElement('a'); a.href = url; a.download = 'chart.png';
          document.body.appendChild(a); a.click(); document.body.removeChild(a);
        }}).catch(err => alert('PNG export failed: ' + err.message));
      }});
      document.getElementById('saveSVG').addEventListener('click', e => {{
        e.preventDefault();
        view.toSVG().then(svg => {{
          const blob = new Blob([svg], {{ type: 'image/svg+xml' }});
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = 'chart.svg';
          document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
        }}).catch(err => alert('SVG export failed: ' + err.message));
      }});
    }}).catch(err => {{
      document.getElementById('vis').innerHTML = '<div class="error"><strong>Error loading chart:</strong><br>' + err + '</div>';
      console.error('Vega-Embed Error:', err);
    }});
  </script>
</body>
</html>"""

    # ---------------- Wren endpoints ----------------
    def _run_sql(self, sql: str, thread_id: Optional[str]):
        payload = {"sql": sql}
        if thread_id:
            payload["threadId"] = thread_id
        return self._post_json("/api/v1/run_sql", payload)

    def _generate_chart(self, question: str, sql: str, thread_id: Optional[str]):
        # working behavior you had (question + sql [+ threadId])
        if not question or not question.strip():
            raise ValueError("Question is required for chart generation")
        if not sql or not sql.strip():
            raise ValueError("SQL query is required for chart generation")
        payload = {"question": question.strip(), "sql": sql.strip()}
        if thread_id:
            payload["threadId"] = thread_id
        return self._post_json("/api/v1/generate_vega_chart", payload)

    # ---------------- Command & auto-prompt detection ----------------
    def _is_chart_cmd(self, txt: str) -> bool:
        t = (txt or "").strip().lower()
        return t in {"show chart", "chart", "/chart"}

    def _is_openwebui_autoprompt(self, txt: str) -> bool:
        """
        Detects Open-WebUI synthetic prompts (follow-ups, auto-title, etc.).
        These are NOT real user questions and must NOT call Wren.
        """
        if not txt:
            return False
        low = txt.lower()

        # Generic markers present in OWUI synthetic prompts
        if "chat_history" in low or "<chat_history>" in low or "</chat_history>" in low:
            return True
        if "### task:" in low or "output: json" in low or "your entire response must consist solely of a json object" in low:
            return True

        # Follow-ups generator templates
        if "follow-up" in low or "follow ups" in low or '"follow_ups"' in low:
            return True
        if "suggest 3-5 relevant follow-up questions" in low:
            return True

        # Auto-title generator templates
        if "generate a concise, 3-5 word title" in low:
            return True
        if "emoji summarizing the chat history" in low and "title" in low:
            return True
        if '"title":' in low and "examples:" in low and "chat history" in low:
            return True

        # Any other system-like prompts that reference /stream/ask with history
        if "/stream/ask" in low and "chat history" in low:
            return True

        return False

    # ---------------- Pipeline ----------------
    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        """
        • Uses only `user_message` as the question (ignores `messages` history completely).
        • Exactly one POST to /api/v1/stream/ask for actual user questions.
        • Ignores Open-WebUI synthetic prompts so they don't hit Wren.
        • After sql_execution_end, pulls rows once via /run_sql.
        • Chart generation on demand via "Show chart".
        """
        metadata = (body or {}).get("metadata", {})
        chat_id = metadata.get("chat_id") or metadata.get("session_id") or metadata.get("thread_id") or "unknown-chat"
        thread_id = self.get_thread_id_for_chat(chat_id)

        # ONLY the direct user message; never read `messages` history
        question = (user_message or "").strip()
        if not question:
            return "Please enter a question."

        # Ignore Open-WebUI auto-prompts (prevents the duplicate /stream/ask you see in logs)
        if self._is_openwebui_autoprompt(question):
            return ""

        # Chart command
        if self._is_chart_cmd(question):
            last_sql = self.last_sql.get(chat_id)
            last_q = self.last_question.get(chat_id, "")
            if not last_sql:
                return ("⚠️ **No SQL query found in this chat yet.**\n\nAsk a data question first, then send **Show chart**.")
            if not last_q:
                return ("⚠️ **No question found in this chat yet.**\n\nAsk a data question first, then send **Show chart**.")

            def _chart():
                yield "### 📈 Generating chart…\n"
                try:
                    chart = self._generate_chart(last_q, last_sql, thread_id)
                    if "error" in chart:
                        yield f"❌ **Chart generation failed** `{chart.get('code','UNKNOWN')}`\n\n{chart.get('error','Unknown error')}\n"
                        return
                    spec = chart.get("vegaSpec")
                    if not spec:
                        yield f"❌ Unexpected chart response: {chart}\n"; return
                    # 1) Raw spec
                    yield "```json\n" + json.dumps(spec, ensure_ascii=False) + "\n```\n"
                    # 2) Vega Editor link
                    try:
                        editor_url = self.build_vega_editor_url(spec, mode="vega-lite")
                        yield f"[Open in Vega Editor]({editor_url})\n"
                    except Exception as e:
                        yield f"_Could not build Vega Editor link: {e}_\n"
                    # 3) Standalone HTML viewer
                    try:
                        html = self.build_standalone_html(spec, title="WrenAI Chart")
                        yield "\n<details><summary>Standalone HTML viewer (click to expand)</summary>\n\n"
                        yield "```html\n" + html + "\n```\n"
                        yield "</details>\n"
                        yield "_Save the HTML block above as `chart.html` and open it in a browser for an interactive chart._\n"
                    except Exception as e:
                        yield f"_Could not build standalone HTML: {e}_\n"
                    yield "_Tip: the Vega Editor link opens the chart already filled — no copy/paste needed._"
                except Exception as e:
                    yield f"❌ **Chart generation exception:** {e}\n"
            return _chart()

        # ---- Single /stream/ask call for real questions ----
        def _stream():
            nonlocal thread_id
            yield "### 🧠 Live pipeline (/stream/ask)\n"

            final_sql: Optional[str] = None
            saw_sql_exec_end = False
            effective_question = question

            payload = {"question": question}  # question only; no history
            if thread_id:
                payload["threadId"] = thread_id

            try:
                for evt in self._post_sse("/api/v1/stream/ask", payload):
                    et = evt.get("type")

                    if et == "message_start":
                        yield "- message_start\n"

                    elif et == "state":
                        data = evt.get("data", {})
                        state = data.get("state")
                        if state:
                            yield f"- {state}\n"

                        if data.get("threadId") and not thread_id:
                            thread_id = data["threadId"]
                            self.set_thread_id_for_chat(chat_id, thread_id)

                        if data.get("rephrasedQuestion"):
                            effective_question = data["rephrasedQuestion"]
                            yield f"  - rephrased: {effective_question}\n"
                        if data.get("retrievedTables"):
                            yield f"  - tables: {', '.join(data['retrievedTables'])}\n"
                        if state == "sql_generation_success" and data.get("sql"):
                            final_sql = data["sql"]
                            yield "\n### 🔍 SQL Query (generated)\n"
                            yield f"```sql\n{final_sql}\n```\n"
                        if state == "sql_execution_end":
                            saw_sql_exec_end = True

                    elif et == "content_block_start":
                        cb = evt.get("content_block", {})
                        if cb.get("type") == "text":
                            name = cb.get("name") or "content"
                            # Two leading newlines break out of the preceding bullet list so markdown renders correctly
                            yield f"\n\n### 🧾 {name.replace('_',' ').title()}\n\n"

                    elif et == "content_block_delta":
                        delta = evt.get("delta", {})
                        text = delta.get("text") or delta.get("value") or ""
                        if text:
                            yield text

                    elif et == "content_block_stop":
                        yield "\n"

                    elif et == "error":
                        data = evt.get("data", {})
                        code = data.get("code", "UNKNOWN")
                        msg = data.get("error", "Unknown error")
                        yield f"\n❌ Error `{code}`: {msg}\n"
                        return

                    elif et == "message_stop":
                        data = evt.get("data", {})
                        if data.get("threadId") and not thread_id:
                            thread_id = data["threadId"]
                            self.set_thread_id_for_chat(chat_id, thread_id)
                        yield "- message_stop\n"

            except requests.HTTPError as e:
                yield f"\n❌ Streaming failed: {e}\n"
                return

            # Persist for charting
            self.last_question[chat_id] = (effective_question or question or "").strip()

            if final_sql and saw_sql_exec_end:
                self.last_sql[chat_id] = final_sql
                yield "\n### 📋 Results\n"
                run = self._run_sql(final_sql, thread_id)
                if run.get("error"):
                    yield f"❌ SQL execution error: {run['error']}\n"
                else:
                    records = run.get("records", [])
                    cols = run.get("columns", [])
                    if records:
                        table_md = self._md_table(records, cols, self.valves.MAX_ROWS)
                        chunk = 2000
                        for i in range(0, len(table_md), chunk):
                            yield table_md[i:i+chunk]
                    else:
                        yield "_No data returned._\n"

                yield "\n---\n"
                yield "➡️ **Type `Show chart`** to render a Vega-Lite chart for this result.\n"
            else:
                yield "\n---\n"
                yield "ℹ️ No SQL was produced for this question. Ask a data-related question to get tables and charts.\n"

        return _stream()
