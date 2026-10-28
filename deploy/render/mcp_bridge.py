"""Stateless MCP backed by DeepTutor's durable turn service.

The bearer key grants access to the local administrator's tutoring workspace.
Only connect it to an owner-private plugin. Never expose it in browser code.
"""
import hmac
import json
import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from jsonschema import ValidationError, validate

LOG = logging.getLogger(__name__)
CAPABILITIES = ["chat", "deep_solve", "deep_question", "deep_research", "ask_questions", "mastery_path"]
ID = {"type": "string", "minLength": 1, "maxLength": 200}


def schema(properties=None, required=None):
    return {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": False}


TOOLS = [
    {"name": "deeptutor_status", "description": "Check DeepTutor readiness without exposing provider credentials.", "inputSchema": schema(), "annotations": {"readOnlyHint": True}},
    {"name": "deeptutor_start", "description": "Start a tutoring, problem-solving, quiz or research task. Returns turn_id immediately; use deeptutor_result to read progress. Model usage may incur provider charges.", "inputSchema": schema({"message": {"type": "string", "minLength": 1, "maxLength": 30000}, "capability": {"type": "string", "enum": CAPABILITIES}, "session_id": ID, "knowledge_bases": {"type": "array", "maxItems": 10, "items": ID}}, ["message"])},
    {"name": "deeptutor_result", "description": "Read task status and paginated durable events. Continue with next_seq when has_more is true. If waiting_input, ask the user and call deeptutor_reply.", "inputSchema": schema({"turn_id": ID, "after_seq": {"type": "integer", "minimum": 0}}, ["turn_id"]), "annotations": {"readOnlyHint": True}},
    {"name": "deeptutor_reply", "description": "Submit the user's answer to a task waiting for input.", "inputSchema": schema({"turn_id": ID, "text": {"type": "string", "minLength": 1, "maxLength": 10000}}, ["turn_id", "text"])},
    {"name": "deeptutor_cancel", "description": "Cancel a running task without deleting its saved conversation.", "inputSchema": schema({"turn_id": ID}, ["turn_id"])},
    {"name": "deeptutor_sessions", "description": "List the owner's recent tutoring conversations.", "inputSchema": schema(), "annotations": {"readOnlyHint": True}},
]


class DeepTutorService:
    async def call(self, name, args, app):
        from deeptutor.app import DeepTutorApp, TurnRequest
        from deeptutor.services.workspace.context import workspace_context

        client = DeepTutorApp(workspace_id="")
        with workspace_context(""):
            if name == "deeptutor_status":
                return {"ready": bool(getattr(app.state, "ready", False)), "version": "1.6.15", "capabilities": CAPABILITIES,
                        "provider_setup": "Configure and test a model in DeepTutor Settings → Providers. Server readiness does not imply model readiness.",
                        "code_execution": "disabled", "scope": "owner workspace"}
            if name == "deeptutor_start":
                session, turn = await client.start_turn(TurnRequest(content=args["message"], capability=args.get("capability", "chat"), session_id=args.get("session_id"), knowledge_bases=args.get("knowledge_bases", []), language="zh", tools=[], workspace_id=""))
                return {"session_id": session["id"], "turn_id": turn["id"], "status": turn.get("status", "queued")}
            if name == "deeptutor_result":
                store = client.container.store_provider.get()
                turn = await store.get_turn(args["turn_id"])
                if turn is None:
                    raise ValueError("Task not found")
                events = await store.get_events(args["turn_id"], args.get("after_seq", 0))
                page = events[:30]
                return {"turn_id": args["turn_id"], "status": turn.get("status"), "events": page,
                        "next_seq": page[-1]["seq"] if page else args.get("after_seq", 0), "has_more": len(events) > len(page)}
            if name == "deeptutor_reply":
                return {"accepted": await client.submit_user_reply(args["turn_id"], text=args["text"])}
            if name == "deeptutor_cancel":
                return {"cancelled": await client.cancel_turn(args["turn_id"])}
            if name == "deeptutor_sessions":
                return {"sessions": await client.list_sessions(limit=20)}
            raise ValueError("Unknown tool")


def install(app, service=None, token_getter=None):
    service = service or DeepTutorService()
    token_getter = token_getter or (lambda: os.environ.get("DEEPTUTOR_MCP_TOKEN", ""))

    @app.get("/api/client-health", include_in_schema=False)
    async def health():
        ready = bool(getattr(app.state, "ready", False))
        return JSONResponse({"ready": ready}, status_code=200 if ready else 503)

    @app.post("/api/client-mcp", include_in_schema=False)
    async def rpc(request: Request):
        expected = token_getter()
        supplied = request.headers.get("authorization", "")
        if len(expected) < 32 or not hmac.compare_digest(supplied.encode(), ("Bearer " + expected).encode()):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 131072:
                return JSONResponse({"error": "Request too large"}, status_code=413)
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeError):
            return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
        if not isinstance(body, dict) or body.get("jsonrpc") != "2.0" or not isinstance(body.get("method"), str):
            return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}})
        method = body["method"]
        if "id" not in body:
            return Response(status_code=202)
        envelope = {"jsonrpc": "2.0", "id": body["id"]}
        if method == "server/discover":
            result = {"supportedVersions": ["2026-07-28"], "capabilities": {"tools": {}}}
        elif method == "initialize":
            result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "serverInfo": {"name": "deeptutor", "version": "1.0.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = body.get("params") or {}
            if not isinstance(params, dict):
                return JSONResponse({**envelope, "error": {"code": -32602, "message": "Invalid parameters"}})
            name = params.get("name")
            tool = next((t for t in TOOLS if t["name"] == name), None)
            if not tool:
                return JSONResponse({**envelope, "error": {"code": -32602, "message": "Unknown tool"}})
            args = params.get("arguments", {})
            try:
                validate(args, tool["inputSchema"])
                data = await service.call(name, args, app)
                result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str)}]}
            except ValidationError:
                result = {"isError": True, "content": [{"type": "text", "text": "Invalid tool arguments"}]}
            except Exception:
                # Provider exceptions may contain credentials: never echo/log them here.
                LOG.warning("DeepTutor MCP operation failed: %s", name)
                result = {"isError": True, "content": [{"type": "text", "text": "Operation failed. Check DeepTutor provider setup and task state in the web app."}]}
        else:
            return JSONResponse({**envelope, "error": {"code": -32601, "message": "Method not found"}})
        return JSONResponse({**envelope, "result": result}, headers={"Cache-Control": "no-store"})
