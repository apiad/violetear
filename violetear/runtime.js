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
};

// ---------------------------------------------------------------------------
// ReactiveRegistry — pub/sub for @app.local state
// ---------------------------------------------------------------------------
const ReactiveRegistry = (() => {
  const _subs = {}; // path -> { id -> callback }
  let _counter = 0;
  return {
    notify(path, value) {
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
  };
})();

// ---------------------------------------------------------------------------
// DOMElement — wraps a native browser element
// ---------------------------------------------------------------------------
class DOMElement {
  constructor(el) { this._el = el; }

  get text() { return this._el ? this._el.innerText : ""; }
  set text(v) { if (this._el) this._el.innerText = String(v); }

  get html() { return this._el ? this._el.innerHTML : ""; }
  set html(v) { if (this._el) this._el.innerHTML = String(v); }

  get value() { return this._el ? this._el.value : undefined; }
  set value(v) { if (this._el) this._el.value = String(v); }

  add(...classes) { classes.forEach(c => this._el && this._el.classList.add(c)); return this; }
  remove(...classes) { classes.forEach(c => this._el && this._el.classList.remove(c)); return this; }
  toggle(cls, force) {
    if (!this._el) return this;
    if (force === true) this._el.classList.add(cls);
    else if (force === false) this._el.classList.remove(cls);
    else this._el.classList.toggle(cls);
    return this;
  }
  append(child) { if (this._el && child._el) this._el.appendChild(child._el); return this; }
  attr(name, value) {
    if (!this._el) return value !== undefined ? this : null;
    if (value === undefined) return this._el.getAttribute(name);
    this._el.setAttribute(name, String(value));
    return this;
  }
  on(event, handler) { if (this._el) this._el.addEventListener(event, handler); return this; }
  query(selector) {
    if (!this._el) return [];
    return Array.from(this._el.querySelectorAll(selector)).map(e => new DOMElement(e));
  }
}

// ---------------------------------------------------------------------------
// DOM — static factory
// ---------------------------------------------------------------------------
const DOM = {
  find(id) { return new DOMElement(document.getElementById(id)); },
  create(tag) { return new DOMElement(document.createElement(tag)); },
  query(selector) { return Array.from(document.querySelectorAll(selector)).map(e => new DOMElement(e)); },
  body() { return new DOMElement(document.body); },
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
// Hydration — events, reactive bindings, WebSocket
// ---------------------------------------------------------------------------
function _hydrate_events(scope) {
  document.querySelectorAll("*").forEach(el => {
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
}

function _hydrate_bindings() {
  document.querySelectorAll("*").forEach(el => {
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
}

let _violetear_socket = null;

function _setup_websocket(scope, validators) {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${location.host}/_violetear/ws?client_id=${_CLIENT_ID}`;
  const socket = new WebSocket(url);
  _violetear_socket = socket;
  window.violetear_socket = socket;

  socket.onopen = () => {
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
  // Apply storage prefix (namespacing)
  const prefix = opts.storage_prefix ?? "";
  localStorage = _makeStorage(window.localStorage, prefix);
  sessionStorage = _makeStorage(window.sessionStorage, prefix);
  idb = new IDBStore(prefix ? `violetear:${prefix}` : "violetear");

  _hydrate_events(scope);
  _hydrate_bindings();

  const validators = opts.validators ?? {};
  const needs_websocket = Object.keys(scope).some(k => !k.startsWith("_"));
  if (needs_websocket) _setup_websocket(scope, validators);

  await _dispatch_ready(scope);
}
