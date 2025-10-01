"""
title: WrenAI Database Query Pipeline (Streaming)
author: Javad Asoodeh
date: 2025-10-01
version: 3.1
license: MIT
description: Streamed NL→SQL reasoning, results, summaries, and charts using Wren AI APIs.
requirements: requests, pydantic
"""

import os, time, json, uuid, logging, requests
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)

class Pipeline:
    class Valves(BaseModel):
        WREN_UI_URL: str
        WREN_UI_TIMEOUT: int
        MAX_ROWS: int
        MODEL_NAME: str

    def __init__(self):
        self.nlsql_response = ""
        # Thread ID management: store thread IDs per Open WebUI chat
        self.thread_ids = {}  # {openwebui_chat_id: wren_ui_thread_id}
        self.last_sql: dict[str, str] = {}     # { openwebui_chat_id: last_success_sql }
        self.last_question: dict[str, str] = {}# { openwebui_chat_id: last_question }

        self.valves = self.Valves(
            **{
                "pipelines": ["*"],
                "WREN_UI_URL": os.getenv("WREN_UI_URL", "http://wren-ui:3000"),
                "WREN_UI_TIMEOUT": int(os.getenv("WREN_UI_TIMEOUT", "600")),
                "MAX_ROWS": int(os.getenv("MAX_ROWS", "500")),
                "MODEL_NAME": os.getenv("MODEL_NAME", "WrenAI Database Query (Streaming)"),
            }
        )
        
        # Set the name from the valve value
        self.name = self.valves.MODEL_NAME

    @property
    def name(self):
        """Dynamic name property that updates when valves change."""
        return self.valves.MODEL_NAME

    @name.setter
    def name(self, value):
        """Setter for name property."""
        self._name = value

    async def on_startup(self):
        # Update name in case valves were changed after initialization
        self.name = self.valves.MODEL_NAME
        logging.info(f"WrenAI Pipeline started with URL: {self.valves.WREN_UI_URL}")
        logging.info(f"Pipeline name: {self.name}")

    async def on_shutdown(self):
        logging.info("Pipeline down")

    def get_thread_id_for_chat(self, openwebui_chat_id: str) -> str:
        """Get the Wren-UI thread ID for a given Open WebUI chat ID."""
        return self.thread_ids.get(openwebui_chat_id)

    def set_thread_id_for_chat(self, openwebui_chat_id: str, wren_ui_thread_id: str):
        """Set the Wren-UI thread ID for a given Open WebUI chat ID."""
        self.thread_ids[openwebui_chat_id] = wren_ui_thread_id
        logging.info(f"Stored thread ID {wren_ui_thread_id} for chat {openwebui_chat_id}")

    def is_new_chat(self, openwebui_chat_id: str) -> bool:
        """Check if this is a new chat (no stored thread ID)."""
        return openwebui_chat_id not in self.thread_ids

    # ---------- HTTP helpers ----------
    def _headers(self):
        h = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "WrenAI-OpenWebUI-Pipeline/3.1",
            "Connection": "keep-alive",
        }
        return h

    def _post_json(self, path: str, payload: dict, timeout: int | None = None):
        url = f"{self.valves.WREN_UI_URL}{path}"
        t = (30, timeout or self.valves.WREN_UI_TIMEOUT)
        r = requests.post(url, json=payload, headers=self._headers(), timeout=t)
        if r.status_code >= 400:
            try: return r.json()
            except: r.raise_for_status()
        return r.json()

    def _get_sse(self, path: str, payload: dict):
        """
        POST with SSE (Server-Sent Events). Uses 'requests' + streaming iterator.
        Endpoint must be a streaming one (e.g. /stream/generate_sql).
        """
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
                # SSE lines are like: "data: {...json...}"
                if line.startswith("data:"):
                    data = line[len("data:"):].strip()
                    if data:
                        try:
                            yield json.loads(data)
                        except Exception:
                            # Some servers may send keep-alives or non-JSON messages
                            yield {"type": "raw", "data": data}

    # ---------- Formatting ----------
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
        extra = ""
        if len(records) > max_rows:
            extra = f"\n\n**Total rows:** {len(records):,} (showing first {max_rows:,})"
        else:
            extra = f"\n\n**Total rows:** {len(records):,}"
        return head + "\n".join(lines) + extra

    def _clean(self, s: str | None) -> str:
        if not s: return ""
        return (
            s.replace("\\n", "\n")
             .replace('\\"', '"')
             .replace("\\'", "'")
             .replace('\\\\', '\\')
        )

    # ---------- Wren AI higher-level calls ----------
    def _run_sql(self, sql: str, thread_id: str | None):
        payload = {"sql": sql}
        if thread_id: payload["threadId"] = thread_id
        return self._post_json("/api/v1/run_sql", payload)

    def _generate_summary(self, question: str, sql: str, thread_id: str | None):
        payload = {"question": question, "sql": sql}
        if thread_id: payload["threadId"] = thread_id
        return self._post_json("/api/v1/generate_summary", payload)

    def _generate_chart(self, question: str, sql: str, thread_id: str | None):
        payload = {"question": question, "sql": sql}
        if thread_id: payload["threadId"] = thread_id
        return self._post_json("/api/v1/generate_vega_chart", payload)

    # Streaming generate_sql (preferred for reasoning UI)
    def _stream_generate_sql(self, question: str, thread_id: str | None):
        payload = {"question": question}
        if thread_id: payload["threadId"] = thread_id
        for evt in self._get_sse("/api/v1/stream/generate_sql", payload):
            yield evt

    # Non-stream generate_sql (used only to detect NON_SQL_QUERY to get explanationQueryId)
    def _generate_sql_once(self, question: str, thread_id: str | None):
        payload = {"question": question}
        if thread_id: payload["threadId"] = thread_id
        return self._post_json("/api/v1/generate_sql", payload)

    def _stream_explanation(self, explanation_query_id: str):
        # GET stream_explanation?queryId=...
        path = f"/api/v1/stream_explanation?queryId={explanation_query_id}"
        url = f"{self.valves.WREN_UI_URL}{path}"
        with requests.get(
            url,
            headers={**self._headers(), "Accept": "text/event-stream"},
            stream=True,
            timeout=(30, self.valves.WREN_UI_TIMEOUT),
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line: 
                    continue
                # SSE lines are like: "data: {...json...}"
                if line.startswith("data:"):
                    data = line[len("data:"):].strip()
                    if data:
                        try:
                            yield json.loads(data)
                        except Exception:
                            # Some servers may send keep-alives or non-JSON messages
                            yield {"type": "raw", "data": data}

    # ---------- Pipeline entry ----------
    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        """
        UX behavior:
        • Always stream reasoning states from /stream/generate_sql.
        • If NON_SQL_QUERY -> stream explanation text.
        • If SQL OK -> run SQL, stream rows; then generate summary.
        • Provide "Show chart" action using last SQL in chat.
        """
        # Extract Open WebUI chat ID
        openwebui_chat_id = None
        if body and 'metadata' in body:
            metadata = body['metadata']
            openwebui_chat_id = metadata.get('chat_id') or metadata.get('session_id') or metadata.get('thread_id')
        
        if not openwebui_chat_id:
            logging.info("No Open WebUI chat ID found, treating as new conversation")
            openwebui_chat_id = "unknown-chat"
        
        chat_id = openwebui_chat_id
        
        # Get or determine Wren-UI thread ID
        wren_ui_thread_id = self.get_thread_id_for_chat(chat_id)
        
        if wren_ui_thread_id:
            logging.info(f"Using existing Wren-UI thread ID: {wren_ui_thread_id} for chat: {chat_id}")
        else:
            logging.info(f"New chat detected: {chat_id}, will get thread ID from Wren-UI response")

        # Simple action: "show chart"
        if user_message.strip().lower() in {"show chart", "chart", "/chart"}:
            last_sql = self.last_sql.get(chat_id)
            last_q = self.last_question.get(chat_id, "")
            if not last_sql:
                return "⚠️ No SQL found in this chat yet. Ask a data question first, then send **Show chart**."
            yield "### 📈 Generating chart…\n"
            try:
                chart = self._generate_chart(last_q, last_sql, wren_ui_thread_id)
                if "vegaSpec" in chart:
                    spec_json = json.dumps(chart["vegaSpec"], ensure_ascii=False)
                    # Open WebUI can render JSON blocks nicely; frontends can pick this up to embed Vega.
                    yield "```json\n" + spec_json + "\n```\n"
                    yield "_Tip: paste this spec into the Vega Editor or wire your UI to render Vega-Lite._"
                else:
                    yield f"❌ Chart error: {chart.get('error','Unknown error')}."
            except Exception as e:
                yield f"❌ Chart exception: {e}"
            return

        # Normal question flow
        question = user_message.strip()
        self.last_question[chat_id] = question
        yield f"### 🧠 Reasoning (live)\n"


        # First, try to stream the reasoning + SQL plan
        final_sql: str | None = None
        non_sql_query_id: str | None = None
        try:
            for evt in self._stream_generate_sql(question, wren_ui_thread_id):
                t = evt.get("type")
                data = evt.get("data") or {}
                if t == "message_start":
                    yield "- started\n"
                elif t == "state":
                    state = data.get("state")
                    if state:
                        yield f"- {state}\n"
                    
                    # Capture thread ID from sql_generation_start state
                    if state == "sql_generation_start" and data.get("threadId") and not wren_ui_thread_id:
                        self.set_thread_id_for_chat(chat_id, data["threadId"])
                        wren_ui_thread_id = data["threadId"]
                        logging.info(f"Captured thread ID from sql_generation_start: {wren_ui_thread_id}")
                    
                    # Show helpful extras when present
                    if data.get("rephrasedQuestion"):
                        yield f"  - rephrased: {data['rephrasedQuestion']}\n"
                    if data.get("retrievedTables"):
                        yield f"  - tables: {', '.join(data['retrievedTables'])}\n"
                    if state == "sql_generation_success" and data.get("sql"):
                        final_sql = data["sql"]
                        # stream the SQL block as soon as we get it
                        yield "\n### 🔍 SQL Query (generated)\n"
                        yield f"```sql\n{final_sql}\n```\n"
                elif t == "error":
                    # Handle NON_SQL_QUERY and other errors
                    error_code = (evt.get("data") or {}).get("code", "UNKNOWN")
                    error_msg = (evt.get("data") or {}).get("error", "Unknown error")
                    yield f"\n❌ Streaming error [{error_code}]: {error_msg}\n"
                    
                    # If it's NON_SQL_QUERY, get the explanationQueryId
                    if error_code == "NON_SQL_QUERY":
                        non_sql_query_id = (evt.get("data") or {}).get("explanationQueryId")
                        if non_sql_query_id:
                            yield "\n### 💬 Explanation (live)\n"
                            try:
                                for exp_evt in self._stream_explanation(non_sql_query_id):
                                    msg = exp_evt.get("message")
                                    if msg:
                                        yield msg
                            except Exception as e:
                                yield f"\n❌ Explanation stream error: {e}\n"
                        else:
                            # Fallback: use /ask (non-stream) explanation form
                            ask = self._post_json("/api/v1/ask", {"question": question})
                            if ask.get("type") == "NON_SQL_QUERY" and ask.get("explanation"):
                                exp = self._clean(ask["explanation"])
                                yield f"\n### 💬 Explanation\n\n{exp}\n"
                        # Store threadId if present and this is a new chat
                        if evt.get("threadId") and not wren_ui_thread_id:
                            self.set_thread_id_for_chat(chat_id, evt["threadId"])
                            wren_ui_thread_id = evt["threadId"]
                        return
                elif t == "message_stop":
                    # done with streaming
                    # Capture thread ID from message_stop if we don't have one yet
                    if data.get("threadId") and not wren_ui_thread_id:
                        self.set_thread_id_for_chat(chat_id, data["threadId"])
                        wren_ui_thread_id = data["threadId"]
                        logging.info(f"Captured thread ID from message_stop: {wren_ui_thread_id}")
                    pass
                else:
                    # Some servers send raw content or other types
                    pass
        except requests.HTTPError as e:
            yield f"\n❌ Streaming failed: {e}\n"

        # If we didn't get SQL from the stream and it wasn't a NON_SQL_QUERY (already handled above)
        if not final_sql and not non_sql_query_id:
            # Non-stream call to detect other errors
            gen = self._generate_sql_once(question, wren_ui_thread_id)
            code = gen.get("code")
            if code == "NON_SQL_QUERY":
                # This shouldn't happen since we handle it in the stream above, but just in case
                exp_id = gen.get("explanationQueryId")
                if exp_id:
                    yield "\n### 💬 Explanation (live)\n"
                    try:
                        for evt in self._stream_explanation(exp_id):
                            msg = evt.get("message")
                            if msg:
                                yield msg
                    except Exception as e:
                        yield f"\n❌ Explanation stream error: {e}\n"
                    # Store threadId if present and this is a new chat
                    if gen.get("threadId") and not wren_ui_thread_id:
                        self.set_thread_id_for_chat(chat_id, gen["threadId"])
                        wren_ui_thread_id = gen["threadId"]
                        logging.info(f"Captured thread ID from fallback response: {wren_ui_thread_id}")
                    return
                else:
                    # Fallback: use /ask (non-stream) explanation form
                    ask = self._post_json("/api/v1/ask", {"question": question})
                    if ask.get("type") == "NON_SQL_QUERY" and ask.get("explanation"):
                        exp = self._clean(ask["explanation"])
                        yield f"\n### 💬 Explanation\n\n{exp}\n"
                        if ask.get("threadId") and not wren_ui_thread_id:
                            self.set_thread_id_for_chat(chat_id, ask["threadId"])
                            wren_ui_thread_id = ask["threadId"]
                            logging.info(f"Captured thread ID from ask fallback: {wren_ui_thread_id}")
                        return
            # If it wasn't NON_SQL_QUERY, surface the error we got
            err = gen.get("error", "No SQL generated.")
            yield f"\n❌ Could not generate SQL: {err}\n"
            return

        # Store thread ID from successful SQL generation if this is a new chat
        if not wren_ui_thread_id and final_sql:
            # Try to get thread ID from the last successful response
            # This is a fallback in case thread ID wasn't captured earlier
            pass

        # Run the SQL and stream rows
        yield "\n### 📋 Results (streaming)\n"
        run = self._run_sql(final_sql, wren_ui_thread_id)
        if run.get("error"):
            yield f"❌ SQL execution error: {run['error']}\n"
            return

        records = run.get("records", [])
        cols    = run.get("columns", [])
        total   = run.get("totalRows", len(records))
        self.last_sql[chat_id] = final_sql  # for later "Show chart"
        if not records:
            yield "_No data returned._\n"
        else:
            # Stream as chunks to avoid oversize messages
            table_md = self._md_table(records, cols, self.valves.MAX_ROWS)
            chunk = 2000
            for i in range(0, len(table_md), chunk):
                yield table_md[i : i + chunk]

        # Generate a natural-language summary (non-stream, fast & simple)
        yield "\n\n### 🧾 Summary\n"
        try:
            summ = self._generate_summary(question, final_sql, wren_ui_thread_id)
            if summ.get("summary"):
                yield self._clean(summ["summary"]) + "\n"
            else:
                yield "_(No summary returned.)_\n"
        except Exception as e:
            yield f"_Summary failed: {e}_\n"

        # Offer a chart action
        yield "\n---\n"
        yield "➡️ **Type `Show chart`** to render an interactive Vega-Lite spec for this result.\n"
