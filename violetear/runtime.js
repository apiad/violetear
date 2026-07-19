// violetear runtime.js — replaces the Pyodide-side Python bundle.
// Loaded as <script src="/_violetear/runtime.js"> before bundle.js.
// Defines globals that compiled bundle code references directly.
"use strict";

// ---------------------------------------------------------------------------
// Validator primitives — generated _VALIDATORS specs call into these.
// Zero-dependency. Each _check* is (value, path) => value | throw.
// ---------------------------------------------------------------------------
class VioletearValidationError extends Error {
  constructor(path, expected, got) {
    super(`${path}: expected ${expected}, got ${JSON.stringify(got)} (${typeof got})`);
    this.name = "VioletearValidationError";
    this.path = path;
  }
}
const _checkAny = (v) => v;
const _checkStr = (v, p) => {
  if (typeof v !== "string") throw new VioletearValidationError(p, "string", v);
  return v;
};
const _checkBool = (v, p) => {
  if (typeof v !== "boolean") throw new VioletearValidationError(p, "boolean", v);
  return v;
};
const _checkNumber = (v, p) => {
  if (typeof v !== "number" || Number.isNaN(v)) throw new VioletearValidationError(p, "number", v);
  return v;
};
const _checkInt = (v, p) => {
  if (typeof v !== "number" || !Number.isInteger(v)) throw new VioletearValidationError(p, "integer", v);
  return v;
};
const _checkList = (v, p, elem) => {
  if (!Array.isArray(v)) throw new VioletearValidationError(p, "list", v);
  v.forEach((x, i) => elem(x, `${p}[${i}]`));
  return v;
};
const _checkDict = (v, p, val) => {
  if (v === null || typeof v !== "object" || Array.isArray(v)) throw new VioletearValidationError(p, "object", v);
  for (const k of Object.keys(v)) val(v[k], `${p}.${k}`);
  return v;
};
const _checkOptional = (v, p, inner) => {
  if (v === null || v === undefined) return v;
  return inner(v, p);
};
const _checkShape = (v, p, fields) => {
  if (v === null || typeof v !== "object" || Array.isArray(v)) throw new VioletearValidationError(p, "object", v);
  for (const k of Object.keys(fields)) fields[k](v[k], `${p}.${k}`);
  return v;
};
function _validateKwargs(fnName, kwargs, spec) {
  if (!spec) return kwargs;
  const errors = [];
  for (const field of Object.keys(spec)) {
    try {
      spec[field](kwargs ? kwargs[field] : undefined, `${fnName}.${field}`);
    } catch (e) {
      errors.push(e.message);
    }
  }
  if (errors.length) {
    const e = new VioletearValidationError(fnName, "valid kwargs", kwargs);
    e.message = `${fnName}: ${errors.join("; ")}`;
    e.errors = errors;
    throw e;
  }
  return kwargs;
}

// ---------------------------------------------------------------------------
// _py — Python semantics helpers the transpiler emits calls into.
// ---------------------------------------------------------------------------
const _py = {
  truthy(x) {
    if (typeof x === "boolean") return x;
    if (x === null || x === undefined) return false;
    if (typeof x === "number") return x !== 0;
    if (typeof x === "string") return x.length > 0;
    if (Array.isArray(x)) return x.length > 0;
    if (typeof x === "object") return Object.keys(x).length > 0;
    return true;
  },
  and(a, bf) { return this.truthy(a) ? bf() : a; },
  or(a, bf) { return this.truthy(a) ? a : bf(); },
  eq(a, b) {
    if (a === b) return true;
    if (a === null || b === null || a === undefined || b === undefined) return false;
    if (typeof a !== "object" || typeof b !== "object") return a === b;
    const aArr = Array.isArray(a), bArr = Array.isArray(b);
    if (aArr !== bArr) return false;
    if (aArr) {
      if (a.length !== b.length) return false;
      for (let i = 0; i < a.length; i++) if (!this.eq(a[i], b[i])) return false;
      return true;
    }
    const ka = Object.keys(a), kb = Object.keys(b);
    if (ka.length !== kb.length) return false;
    for (const k of ka) {
      if (!Object.prototype.hasOwnProperty.call(b, k)) return false;
      if (!this.eq(a[k], b[k])) return false;
    }
    return true;
  },
  ne(a, b) { return !this.eq(a, b); },
  format(value, spec) {
    const m = /^(0?)(\d*)(?:\.(\d+))?([a-zA-Z%]?)$/.exec(spec);
    if (!m) return String(value);
    const zero = m[1] === "0";
    const width = m[2] ? parseInt(m[2], 10) : 0;
    const prec = m[3] !== undefined ? parseInt(m[3], 10) : null;
    const type = m[4].toLowerCase();
    let s;
    if (type === "d") s = String(Math.trunc(Number(value)));
    else if (type === "f") s = Number(value).toFixed(prec === null ? 6 : prec);
    else if (type === "x") s = Math.trunc(Number(value)).toString(16);
    else if (type === "%") s = (Number(value) * 100).toFixed(prec === null ? 6 : prec) + "%";
    else if (prec !== null && typeof value === "string") s = value.slice(0, prec);
    else s = String(value);
    if (width > s.length) {
      const pad = width - s.length;
      if (type === "" || type === "s") {
        s = s + " ".repeat(pad);
      } else if (zero && (s[0] === "-" || s[0] === "+")) {
        s = s[0] + "0".repeat(pad) + s.slice(1);
      } else {
        s = (zero ? "0" : " ").repeat(pad) + s;
      }
    }
    return s;
  },
  mod(a, b) { return ((a % b) + b) % b; },
  mul(a, b) {
    if (typeof a === "string" && typeof b === "number") return a.repeat(Math.max(0, b));
    if (typeof b === "string" && typeof a === "number") return b.repeat(Math.max(0, a));
    if (Array.isArray(a) && typeof b === "number") return Array.from({ length: Math.max(0, b) }, () => a).flat();
    if (Array.isArray(b) && typeof a === "number") return Array.from({ length: Math.max(0, a) }, () => b).flat();
    return a * b;
  },
  add(a, b) {
    if (Array.isArray(a) && Array.isArray(b)) return a.concat(b);
    return a + b;
  },
  len(x) {
    if (x === null || x === undefined) return 0;
    if (typeof x === "string" || Array.isArray(x)) return x.length;
    if (typeof x === "object") return Object.keys(x).length;
    return 0;
  },
  repr(x) {
    if (typeof x === "string") return "'" + x + "'";
    return this.str(x);
  },
  str(x) {
    if (x === true) return "True";
    if (x === false) return "False";
    if (x === null || x === undefined) return "None";
    if (Array.isArray(x)) return "[" + x.map((e) => this.repr(e)).join(", ") + "]";
    if (typeof x === "object") return "{" + Object.entries(x).map(([k, v]) => this.repr(k) + ": " + this.repr(v)).join(", ") + "}";
    return String(x);
  },
  contains(c, x) {
    if (typeof c === "string") return c.includes(x);
    if (Array.isArray(c)) return c.some((e) => this.eq(e, x));
    if (c !== null && typeof c === "object") return Object.prototype.hasOwnProperty.call(c, x);
    return false;
  },
};

// ---------------------------------------------------------------------------
// ReactiveRegistry — pub/sub for @app.local state
// ---------------------------------------------------------------------------
const ReactiveRegistry = (() => {
  const _subs = {}; // path -> { id -> callback }
  const _values = {}; // path -> last notified value (for flush_subtree)
  let _counter = 0;
  return {
    notify(path, value) {
      _values[path] = value;
      const bucket = _subs[path];
      if (!bucket) return;
      for (const cb of Object.values(bucket)) {
        try { cb(value); } catch (e) { console.error("[violetear] reactive update error:", e); }
      }
    },
    bind(path, callback) {
      if (!_subs[path]) _subs[path] = {};
      const id = _counter++;
      _subs[path][id] = callback;
      return () => { if (_subs[path]) delete _subs[path][id]; };
    },
    // Apply cached values to all subscribers (called after partial inject to
    // immediately reflect current state in newly-hydrated elements).
    flush_subtree(_root) {
      for (const [path, value] of Object.entries(_values)) {
        const bucket = _subs[path];
        if (!bucket) continue;
        for (const cb of Object.values(bucket)) {
          try { cb(value); } catch (e) { console.error("[violetear] reactive flush error:", e); }
        }
      }
    },
  };
})();

// ---------------------------------------------------------------------------
// _DOMEl — wraps a native browser element with a fluent mutation API.
// DOM.find / DOM.query return instances of this class.
// ---------------------------------------------------------------------------
class _DOMEl {
  constructor(el) { this._el = el; }

  // Content
  get text() { return this._el ? this._el.textContent : ""; }
  set text(v) { if (this._el) this._el.textContent = String(v); }
  get html() { return this._el ? this._el.innerHTML : ""; }
  set html(v) { if (this._el) this._el.innerHTML = String(v); }
  async load(url) {
    const r = await fetch(url);
    if (!r.ok) { console.error(`[violetear] partial load failed: ${r.status} ${url}`); return; }
    this._el.innerHTML = await r.text();
    if (_violetear_scope) _hydrate_subtree(this._el, _violetear_scope);
  }

  // Classes
  add_class(...names) { if (this._el) this._el.classList.add(...names); return this; }
  remove_class(...names) { if (this._el) this._el.classList.remove(...names); return this; }
  toggle_class(name) { if (this._el) this._el.classList.toggle(name); return this; }
  has_class(name) { return this._el ? this._el.classList.contains(name) : false; }

  // Attributes
  attr(key, value) {
    if (!this._el) return value !== undefined ? this : null;
    if (value === undefined) return this._el.getAttribute(key);
    this._el.setAttribute(key, String(value));
    return this;
  }
  remove_attr(key) { if (this._el) this._el.removeAttribute(key); return this; }

  // Visibility
  hide() { if (this._el) this._el.style.display = "none"; return this; }
  show(display = "") { if (this._el) this._el.style.display = display; return this; }

  // Form value
  get value() { return this._el ? this._el.value : undefined; }
  set value(v) { if (this._el) this._el.value = String(v); }

  // Structure
  clear() { if (this._el) this._el.innerHTML = ""; return this; }
  remove() { if (this._el) this._el.remove(); }

  // Focus / scroll
  focus() { if (this._el) this._el.focus(); return this; }
  blur() { if (this._el) this._el.blur(); return this; }
  scroll_into_view(smooth = true) {
    if (this._el) this._el.scrollIntoView({ behavior: smooth ? "smooth" : "instant" });
  }

  // Events
  on(event, fn) { if (this._el) this._el.addEventListener(event, fn); return this; }
  off(event, fn) { if (this._el) this._el.removeEventListener(event, fn); return this; }

  // Legacy helpers kept for backward compatibility (example 05)
  add(...classes) { return this.add_class(...classes); }
  append(child) { if (this._el && child._el) this._el.appendChild(child._el); return this; }
  query(selector) {
    if (!this._el) return [];
    return Array.from(this._el.querySelectorAll(selector)).map(e => new _DOMEl(e));
  }
}

// ---------------------------------------------------------------------------
// DOM — static factory for DOM element wrappers
// ---------------------------------------------------------------------------
const DOM = {
  find(id) { return new _DOMEl(document.getElementById(id)); },
  query(selector) { return new _DOMEl(document.querySelector(selector)); },
  query_all(selector) { return Array.from(document.querySelectorAll(selector)).map(e => new _DOMEl(e)); },
  // Legacy helpers kept for backward compatibility (example 05)
  create(tag) { return new _DOMEl(document.createElement(tag)); },
  body() { return new _DOMEl(document.body); },
};

// ---------------------------------------------------------------------------
// Storage — JSON-transparent wrapper with namespacing
// ---------------------------------------------------------------------------
class _Storage {
  constructor(backend, prefix) {
    this._backend = backend;
    this._prefix = prefix ? prefix + ":" : "";
  }
  _k(key) { return this._prefix + key; }
  get(key, def = null) {
    const raw = this._backend.getItem(this._k(key));
    if (raw === null) return def;
    try { return JSON.parse(raw); } catch { return raw; }
  }
  set(key, value) { this._backend.setItem(this._k(key), JSON.stringify(value)); }
  remove(key) { this._backend.removeItem(this._k(key)); }
  has(key) { return this._backend.getItem(this._k(key)) !== null; }
  clear() {
    const prefix = this._prefix;
    Object.keys(this._backend)
      .filter(k => k.startsWith(prefix))
      .forEach(k => this._backend.removeItem(k));
  }
}

// Proxy enables attribute-style access: localStorage.foo = bar
function _makeStorage(backend, prefix) {
  const store = new _Storage(backend, prefix);
  return new Proxy(store, {
    get(t, prop) {
      if (prop in t || typeof prop === "symbol") return t[prop];
      return t.get(prop);
    },
    set(t, prop, value) {
      if (prop.startsWith("_")) { t[prop] = value; return true; }
      t.set(prop, value);
      return true;
    },
  });
}

// Placeholder — overwritten by Violetear_hydrate with the app's prefix
let localStorage = _makeStorage(window.localStorage, "");
let sessionStorage = _makeStorage(window.sessionStorage, "");

// ---------------------------------------------------------------------------
// IDBStore — async KV backed by IndexedDB
// ---------------------------------------------------------------------------
class IDBStore {
  constructor(dbName) {
    this._dbName = dbName;
    this._db = null;
  }
  async _open() {
    if (this._db) return this._db;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(this._dbName, 1);
      req.onupgradeneeded = e => e.target.result.createObjectStore("kv");
      req.onsuccess = e => { this._db = e.target.result; resolve(this._db); };
      req.onerror = e => reject(e.target.error);
    });
  }
  async _tx(mode, fn) {
    const db = await this._open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("kv", mode);
      const store = tx.objectStore("kv");
      const req = fn(store);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  async get(key, def = null) {
    const raw = await this._tx("readonly", s => s.get(key));
    if (raw === undefined) return def;
    return raw;
  }
  async set(key, value) { await this._tx("readwrite", s => s.put(value, key)); }
  async remove(key) { await this._tx("readwrite", s => s.delete(key)); }
  async has(key) { return (await this._tx("readonly", s => s.getKey(key))) !== undefined; }
  async keys() { return this._tx("readonly", s => s.getAllKeys()); }
  async items() {
    const db = await this._open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("kv", "readonly");
      const store = tx.objectStore("kv");
      const result = [];
      store.openCursor().onsuccess = e => {
        const cursor = e.target.result;
        if (cursor) { result.push([cursor.key, cursor.value]); cursor.continue(); }
        else resolve(result);
      };
    });
  }
  async clear() { await this._tx("readwrite", s => s.clear()); }
}

let idb = new IDBStore("");

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function sleep(seconds) { return new Promise(r => setTimeout(r, seconds * 1000)); }

const _CLIENT_ID = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
function get_client_id() { return _CLIENT_ID; }

function exec(js_code) { eval(js_code); } // eslint-disable-line no-eval

// ---------------------------------------------------------------------------
// Hydration — bind events and reactive data attributes within a subtree.
// _violetear_scope is set on first hydration so that DOM.load() can
// re-hydrate injected partials without needing to pass the scope through.
// ---------------------------------------------------------------------------
let _violetear_scope = null;

function _hydrate_subtree(root, scope) {
  // Event bindings
  root.querySelectorAll("*").forEach(el => {
    for (const attr of Array.from(el.attributes)) {
      if (attr.name.startsWith("data-on-")) {
        const event = attr.name.slice(8);
        const fn_name = attr.value;
        const fn = scope[fn_name];
        if (fn) el.addEventListener(event, fn);
        else console.warn(`[violetear] handler not found: ${fn_name}`);
      }
    }
  });

  // Reactive bindings
  root.querySelectorAll("*").forEach(el => {
    for (const attr of Array.from(el.attributes)) {
      if (!attr.name.startsWith("data-bind-")) continue;
      const prop = attr.name.slice(10); // e.g. "text", "value", "class"
      const path = attr.value;          // e.g. "UiState.mode"
      let updater;
      if (prop === "text") updater = v => { el.innerText = String(v); };
      else if (prop === "html") updater = v => { el.innerHTML = String(v); };
      else if (prop === "value") updater = v => { el.value = String(v); };
      else if (prop === "class") updater = v => { el.className = String(v); };
      else updater = v => {
        if (v === false || v === null) el.removeAttribute(prop);
        else el.setAttribute(prop, String(v));
      };
      ReactiveRegistry.bind(path, updater);
    }
  });

  // Apply current reactive values to newly-registered elements
  ReactiveRegistry.flush_subtree(root);
}

let _violetear_socket = null;

// Queue of messages to send when the socket opens.
let _ws_send_queue = [];

function _ws_send(obj) {
  const msg = JSON.stringify(obj);
  if (_violetear_socket && _violetear_socket.readyState === WebSocket.OPEN) {
    _violetear_socket.send(msg);
  } else {
    _ws_send_queue.push(msg);
  }
}

// ---------------------------------------------------------------------------
// _shared — handles shared_sync / shared_set for @app.shared state classes.
// _shared_objects is populated by bundle.js (generated per-app at startup).
// ---------------------------------------------------------------------------
let _shared_objects = {};  // overwritten by bundle.js

const _shared = {
  _receiving: false,

  set(cls, field, value) {
    _ws_send({ type: "shared_set", class: cls, field: field, value: value });
  },

  handle(msg) {
    const obj = _shared_objects[msg.class];
    if (!obj) {
      console.warn(`[violetear] shared_sync for unknown class: ${msg.class}`);
      return;
    }
    _shared._receiving = true;
    try {
      obj[msg.field] = msg.value;
    } catch (e) {
      console.error(`[violetear] shared_sync assignment error: ${e.message}`);
    } finally {
      _shared._receiving = false;
    }
  },

  handle_error(msg) {
    console.error(
      `[violetear] shared write rejected — ${msg.class}.${msg.field}: ${msg.reason}`
    );
  },
};

function _setup_websocket(scope, validators) {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${location.host}/_violetear/ws?client_id=${_CLIENT_ID}`;
  const socket = new WebSocket(url);
  _violetear_socket = socket;
  window.violetear_socket = socket;

  socket.onopen = () => {
    // Flush any messages queued before the socket opened
    while (_ws_send_queue.length) {
      socket.send(_ws_send_queue.shift());
    }
    const handlers = scope._lifecycle?.connect ?? [];
    handlers.forEach(fn => fn().catch(e => console.error("[violetear] connect handler error:", e)));
  };

  socket.onmessage = event => {
    let data;
    try { data = JSON.parse(event.data); } catch { return; }
    if (data.type === "rpc") {
      const fn = scope[data.func];
      if (!fn) { console.warn(`[violetear] rpc handler not found: ${data.func}`); return; }
      try {
        _validateKwargs(data.func, data.kwargs ?? {}, validators?.[data.func]);
      } catch (e) {
        console.error(`[violetear] invalid inbound payload for ${data.func}:`, e.message);
        return;
      }
      fn(data.kwargs ?? {}).catch(e => console.error(`[violetear] rpc error in ${data.func}:`, e));
    } else if (data.type === "shared_sync") {
      _shared.handle(data);
    } else if (data.type === "shared_error") {
      _shared.handle_error(data);
    }
  };

  socket.onclose = () => {
    const handlers = scope._lifecycle?.disconnect ?? [];
    handlers.forEach(fn => fn().catch(() => {}));
    setTimeout(() => _setup_websocket(scope, validators), 3000);
  };
}

async function _dispatch_ready(scope) {
  const handlers = scope._lifecycle?.ready ?? [];
  for (const fn of handlers) {
    try { await fn(); } catch (e) { console.error("[violetear] ready handler error:", e); }
  }
}

// ---------------------------------------------------------------------------
// Entry point — called at end of bundle.js
// ---------------------------------------------------------------------------
async function Violetear_hydrate(scope, opts = {}) {
  // Store scope so DOM.load() can re-hydrate injected partials
  _violetear_scope = scope;

  // Apply storage prefix (namespacing)
  const prefix = opts.storage_prefix ?? "";
  localStorage = _makeStorage(window.localStorage, prefix);
  sessionStorage = _makeStorage(window.sessionStorage, prefix);
  idb = new IDBStore(prefix ? `violetear:${prefix}` : "violetear");

  _hydrate_subtree(document, scope);

  const validators = opts.validators ?? {};
  const needs_websocket = Object.keys(scope).some(k => !k.startsWith("_"));
  if (needs_websocket) _setup_websocket(scope, validators);

  await _dispatch_ready(scope);
}
