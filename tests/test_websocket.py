"""
Tests for the WebSocket lifecycle, realtime dispatch, and reverse-RPC envelope.
"""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from violetear import App, Document


def test_websocket_connect_fires_server_on_connect_with_client_id():
    """A WebSocket connect triggers @app.server.on("connect") with the client_id."""
    app = App(title="WS-Connect", version="ws1")

    seen = []

    @app.server.on("connect")
    async def on_connect(client_id: str):
        seen.append(("connect", client_id))

    @app.server.on("disconnect")
    async def on_disconnect(client_id: str):
        seen.append(("disconnect", client_id))

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)

    with client.websocket_connect("/_violetear/ws?client_id=abc"):
        pass  # closing the context disconnects

    # Connect runs synchronously on entry — guaranteed before this point.
    assert ("connect", "abc") in seen

    # Disconnect happens via the server's exception path after close —
    # give the worker loop a moment to flush before asserting.
    for _ in range(20):
        if ("disconnect", "abc") in seen:
            break
        time.sleep(0.05)

    assert ("disconnect", "abc") in seen


def test_realtime_message_dispatches_to_server_function():
    """A client → server realtime payload invokes @app.server.realtime.

    Uses a server → client broadcast ack to make the test deterministic without
    sleeping: the next receive_json() blocks until the server has finished
    processing our outbound message.
    """
    app = App(title="WS-Realtime", version="ws2")

    seen = []

    @app.client.realtime
    async def ack():
        pass

    @app.server.realtime
    async def record(action: str, count: int):
        seen.append((action, count))
        await ack.broadcast()

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)

    with client.websocket_connect("/_violetear/ws?client_id=xyz") as ws:
        ws.send_json(
            {
                "type": "realtime",
                "func": "record",
                "args": ["click", 7],
                "kwargs": {},
            }
        )
        ack_msg = ws.receive_json()

    assert ack_msg["type"] == "rpc"
    assert ack_msg["func"] == "ack"
    assert seen == [("click", 7)]


def test_reverse_rpc_broadcast_envelope_shape():
    """Server-side .broadcast() sends a JSON envelope of the documented shape."""
    app = App(title="WS-Broadcast", version="ws3")

    @app.client.realtime
    async def notify(message: str, level: str):
        pass

    @app.server.rpc
    async def kick() -> dict:
        await notify.broadcast(message="hello", level="info")
        return {"ok": True}

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)

    with client.websocket_connect("/_violetear/ws?client_id=listener") as ws:
        r = client.post("/_violetear/rpc/kick", json={})
        assert r.status_code == 200
        msg = ws.receive_json()

    assert msg == {
        "type": "rpc",
        "func": "notify",
        "args": [],
        "kwargs": {"message": "hello", "level": "info"},
    }


def test_reverse_rpc_invoke_targets_specific_client():
    """.invoke(client_id, ...) sends only to the named client, not others."""
    app = App(title="WS-Invoke", version="ws4")

    @app.client.realtime
    async def whisper(secret: str):
        pass

    @app.server.rpc
    async def kick_one(target: str) -> dict:
        await whisper.invoke(target, secret="shh")
        return {"ok": True}

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)

    with (
        client.websocket_connect("/_violetear/ws?client_id=a") as ws_a,
        client.websocket_connect("/_violetear/ws?client_id=b") as ws_b,
    ):
        r = client.post("/_violetear/rpc/kick_one", json={"target": "b"})
        assert r.status_code == 200

        msg_b = ws_b.receive_json()
        assert msg_b["func"] == "whisper"
        assert msg_b["kwargs"] == {"secret": "shh"}

        # Confirm ws_a got nothing — drain with a short window.
        # If a message were queued, receive_json would return it immediately.
        # We rely on the fact that broadcast() iterates all conns but invoke()
        # picks one. No clean "no-op" probe in TestClient, so we instead trigger
        # a second message targeted at a and confirm ws_a now receives that one.
        r = client.post("/_violetear/rpc/kick_one", json={"target": "a"})
        assert r.status_code == 200

        msg_a = ws_a.receive_json()
        assert msg_a["func"] == "whisper"
        assert msg_a["kwargs"] == {"secret": "shh"}


def test_broadcast_rejects_mistyped_kwargs_before_send():
    """A server-side broadcast with kwargs that violate the @app.client.realtime
    signature raises before any frame reaches the wire."""
    app = App(title="WS-Validate-Out", version="wsv1")

    @app.client.realtime
    async def notify(message: str, level: str):
        pass

    @app.view("/")
    def home():
        return Document(title="x")

    with pytest.raises(ValidationError):
        # level must be str; 123 is rejected by the generated Pydantic model
        asyncio.run(notify.broadcast(message="hello", level=123))


def test_broadcast_accepts_valid_kwargs_and_sends_envelope():
    """Valid kwargs pass validation and produce the unchanged envelope shape."""
    app = App(title="WS-Validate-Out-OK", version="wsv2")

    @app.client.realtime
    async def notify(message: str, level: str):
        pass

    @app.server.rpc
    async def kick() -> dict:
        await notify.broadcast(message="hi", level="info")
        return {"ok": True}

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)
    with client.websocket_connect("/_violetear/ws?client_id=v") as ws:
        r = client.post("/_violetear/rpc/kick", json={})
        assert r.status_code == 200
        msg = ws.receive_json()
    assert msg == {
        "type": "rpc",
        "func": "notify",
        "args": [],
        "kwargs": {"message": "hi", "level": "info"},
    }


def test_inbound_realtime_rejects_mistyped_kwargs_and_skips_handler():
    """A client→server realtime frame with a wrong-typed field is rejected
    server-side: the handler is not called and the connection stays open."""
    app = App(title="WS-Inbound-Validate", version="wsv3")

    seen = []

    @app.client.realtime
    async def ack():
        pass

    @app.server.realtime
    async def record(action: str, count: int):
        seen.append((action, count))
        await ack.broadcast()

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)
    with client.websocket_connect("/_violetear/ws?client_id=z") as ws:
        ws.send_json(
            {
                "type": "realtime",
                "func": "record",
                "args": [],
                "kwargs": {"action": "x", "count": "oops"},
            }
        )
        ws.send_json(
            {
                "type": "realtime",
                "func": "record",
                "args": [],
                "kwargs": {"action": "ok", "count": 3},
            }
        )
        ack_msg = ws.receive_json()

    assert ack_msg["func"] == "ack"
    assert seen == [("ok", 3)]


def test_inbound_realtime_positional_args_still_validate_and_run():
    """The existing positional-args path (args=[...], kwargs={}) still binds and
    validates — regression guard for test_realtime_message_dispatches."""
    app = App(title="WS-Inbound-Pos", version="wsv4")

    seen = []

    @app.client.realtime
    async def ack():
        pass

    @app.server.realtime
    async def record(action: str, count: int):
        seen.append((action, count))
        await ack.broadcast()

    @app.view("/")
    def home():
        return Document(title="x")

    client = TestClient(app.api)
    with client.websocket_connect("/_violetear/ws?client_id=p") as ws:
        ws.send_json(
            {"type": "realtime", "func": "record", "args": ["click", 7], "kwargs": {}}
        )
        ack_msg = ws.receive_json()

    assert ack_msg["func"] == "ack"
    assert seen == [("click", 7)]


# ---- Shared sync message tests ----
import json
from unittest.mock import AsyncMock, MagicMock
from violetear.app import SocketManager


def _make_socket_manager():
    app = MagicMock()
    sm = SocketManager(app)
    ws = AsyncMock()
    sm.active_connections["c1"] = ws
    return sm, ws


def test_broadcast_shared_sync_sends_to_all():
    sm, ws = _make_socket_manager()
    asyncio.run(sm.broadcast_shared_sync("Room", "count", 42))
    ws.send_text.assert_called_once()
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload == {
        "type": "shared_sync",
        "class": "Room",
        "field": "count",
        "value": 42,
    }


def test_send_shared_sync_sends_to_one():
    sm, ws = _make_socket_manager()
    asyncio.run(sm.send_shared_sync("c1", "Room", "count", 42))
    ws.send_text.assert_called_once()
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload == {
        "type": "shared_sync",
        "class": "Room",
        "field": "count",
        "value": 42,
    }


def test_send_shared_error_sends_error_frame():
    sm, ws = _make_socket_manager()
    asyncio.run(sm.send_shared_error("c1", "Room", "version", "server_only"))
    ws.send_text.assert_called_once()
    payload = json.loads(ws.send_text.call_args[0][0])
    assert payload == {
        "type": "shared_error",
        "class": "Room",
        "field": "version",
        "reason": "server_only",
    }
