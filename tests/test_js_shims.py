"""Tests that violetear.js stubs raise ClientOnlyError when called server-side."""

import pytest

from violetear.js import (
    DOM,
    ClientOnlyError,
    Date,
    DOMElement,
    Event,
    IDBStore,
    Storage,
    console,
    exec,
    fetch,
    get_client_id,
    idb,
    localStorage,
    sessionStorage,
    sleep,
)


def test_dom_find_raises():
    with pytest.raises(ClientOnlyError):
        DOM.find("my-id")


def test_dom_create_raises():
    with pytest.raises(ClientOnlyError):
        DOM.create("div")


def test_storage_get_raises():
    with pytest.raises(ClientOnlyError):
        localStorage.get("key")


def test_storage_set_raises():
    with pytest.raises(ClientOnlyError):
        localStorage.set("key", "value")


def test_storage_getattr_raises():
    with pytest.raises(ClientOnlyError):
        _ = localStorage.foo


def test_sleep_raises():
    import asyncio

    with pytest.raises(ClientOnlyError):
        asyncio.get_event_loop().run_until_complete(sleep(1))


def test_get_client_id_raises():
    with pytest.raises(ClientOnlyError):
        get_client_id()


def test_console_log_raises():
    with pytest.raises(ClientOnlyError):
        console.log("hello")


def test_exec_raises():
    with pytest.raises(ClientOnlyError):
        exec("window.thing()")


def test_date_now_raises():
    with pytest.raises(ClientOnlyError):
        Date.now()


def test_idb_get_raises():
    import asyncio

    with pytest.raises(ClientOnlyError):
        asyncio.get_event_loop().run_until_complete(idb.get("key"))
