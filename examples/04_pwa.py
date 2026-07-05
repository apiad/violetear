"""Tier 4 canonical example — an installable, offline-capable pomodoro timer.

SSR + Pyodide bundle + PWA. Demonstrates `@app.view(pwa=Manifest(...))`,
Service Worker asset caching (bundle + stylesheet + Pyodide files cached
on first load — the app works offline after that), `violetear.storage`
cross-reload persistence, an `asyncio` tick loop on the client side, and
`@app.local` mutation from a non-callback client function.

Run:

    python examples/04_pwa.py

Then open http://localhost:8000 in a browser. Click "Start" — the timer
counts down in real time. Switch modes (work / short break / long break)
to swap the duration. Refresh the page: the last state restores from
localStorage (paused — you decide when to resume). Open DevTools →
Application to see the manifest and the registered Service Worker; go
offline and reload — the app still loads from the SW cache.
"""

from dataclasses import dataclass

from violetear import App, Document, StyleSheet
from violetear.color import Colors
from violetear.js import Event, localStorage, sleep
from violetear.pwa import Manifest
from violetear.units import px, rem


# Version is pinned (rather than left to default) so the Service Worker's
# CACHE_NAME stays stable across server restarts — otherwise every restart
# invalidates the cache and forces a re-download (see violetear/pwa.py).
app = App(title="Pomodoro", version="1.0.0")


# ---------------------------------------------------------------------------
# Reactive state
# ---------------------------------------------------------------------------
#
# Mode durations live as defaults on the dataclass rather than module-level
# constants — gap 7.7 means free names referenced from client functions
# silently NameError in the bundle. Inlining the seconds-per-mode lookup
# inside each client function (below) is the workaround.


@app.local
@dataclass
class PomodoroState:
    mode: str = "work"
    seconds_left: int = 1500  # 25 min
    running: bool = False
    sessions: int = 0
    time_display: str = "25:00"
    toggle_label: str = "Start"


# ---------------------------------------------------------------------------
# Client-side helpers + callbacks
# ---------------------------------------------------------------------------


@app.client
async def save_state():
    localStorage.pomodoro = {
        "mode": str(PomodoroState.mode),
        "seconds_left": int(PomodoroState.seconds_left),
        "sessions": int(PomodoroState.sessions),
        # Intentionally never persist `running=True` — on reload we always
        # pause so the user explicitly resumes. Simpler than wall-time math.
    }


@app.client
async def render_time():
    # Update the MM:SS string from seconds_left. Called from any code path
    # that mutates seconds_left so the bound span stays in sync.
    s = int(PomodoroState.seconds_left)
    if s < 0:
        s = 0
    minutes = s // 60
    seconds = s % 60
    PomodoroState.time_display = f"{minutes:02d}:{seconds:02d}"


@app.client
async def tick():
    # Long-running async loop. Plain `@app.client` (not `.callback`) because
    # callbacks are reserved for DOM event handlers — the framework validates
    # callbacks take an `event` arg. `start` awaits tick from its handler;
    # other buttons (pause, reset) fire on their own coroutines and remain
    # responsive even while this loop is mid-await.
    # Mode durations inlined (gap 7.7).
    durations = {"work": 1500, "short": 300, "long": 900}

    while bool(PomodoroState.running):
        await sleep(1)
        s = int(PomodoroState.seconds_left) - 1
        if s <= 0:
            # Phase complete: bump session counter on a finished "work" leg,
            # then auto-advance to the next mode (every 4th work session
            # earns a long break, otherwise short).
            current_mode = str(PomodoroState.mode)
            if current_mode == "work":
                PomodoroState.sessions = int(PomodoroState.sessions) + 1
                next_mode = "long" if int(PomodoroState.sessions) % 4 == 0 else "short"
            else:
                next_mode = "work"
            PomodoroState.mode = next_mode
            PomodoroState.seconds_left = durations[next_mode]
            PomodoroState.running = False
            PomodoroState.toggle_label = "Start"
            await render_time()
            await save_state()
            return
        PomodoroState.seconds_left = s
        await render_time()
        await save_state()


@app.client.callback
async def toggle(event: Event):
    # Single Start/Pause button. The label flips so the user can always see
    # whether the timer is running. When starting, await tick() — the loop
    # owns the running coroutine until it sees running=False (set here on
    # the next click) or seconds_left hits zero.
    if bool(PomodoroState.running):
        PomodoroState.running = False
        PomodoroState.toggle_label = "Start"
        await save_state()
        return
    PomodoroState.running = True
    PomodoroState.toggle_label = "Pause"
    await tick()


@app.client.callback
async def reset(event: Event):
    # Reset to the full duration of the current mode. Stops the timer.
    durations = {"work": 1500, "short": 300, "long": 900}
    PomodoroState.running = False
    PomodoroState.toggle_label = "Start"
    PomodoroState.seconds_left = durations[str(PomodoroState.mode)]
    await render_time()
    await save_state()


@app.client.callback
async def switch_mode(event: Event):
    # Each mode button carries data-mode="work|short|long" — read it off the
    # event target rather than from a module-level lookup table.
    durations = {"work": 1500, "short": 300, "long": 900}
    new_mode = str(event.target.dataset.mode)
    if not durations[new_mode]:
        return
    PomodoroState.running = False
    PomodoroState.toggle_label = "Start"
    PomodoroState.mode = new_mode
    PomodoroState.seconds_left = durations[new_mode]
    await render_time()
    await save_state()


@app.client.on("ready")
async def restore():
    saved = localStorage.pomodoro
    if saved is None:
        return
    if saved.mode is not None:
        PomodoroState.mode = str(saved.mode)
    if saved.seconds_left is not None:
        PomodoroState.seconds_left = int(saved.seconds_left)
    if saved.sessions is not None:
        PomodoroState.sessions = int(saved.sessions)
    # Always restore paused — user clicks start to resume.
    PomodoroState.running = False
    PomodoroState.toggle_label = "Start"
    await render_time()


# ---------------------------------------------------------------------------
# Stylesheet — flat class selectors only (gap 7.1)
# ---------------------------------------------------------------------------


sheet = StyleSheet(normalize=True)

sheet.select("body").font(
    size=rem(1.0), family="system-ui, -apple-system, 'Segoe UI', sans-serif"
).color(Colors.DarkSlateGray).background(Colors.WhiteSmoke).padding(rem(2.5))

sheet.select(".page").rules(max_width="420px").margin("auto").background(
    Colors.White
).padding(rem(2.5)).rounded(px(12)).border(px(1), Colors.Gainsboro)

sheet.select(".page-title").font(size=rem(1.75), weight=700).color(
    Colors.Firebrick
).margin(bottom=rem(0.25))

sheet.select(".subtitle").color(Colors.SlateGray).font(size=rem(0.9)).margin(
    bottom=rem(1.5)
)

sheet.select(".mode-row").flexbox(direction="row", gap=px(8)).margin(bottom=rem(1.5))
sheet.select(".mode-button").rules(
    padding="8px 12px",
    border=f"1px solid {Colors.Gainsboro}",
    cursor="pointer",
    font_size="0.875rem",
    font_weight=600,
    flex="1",
).background(Colors.White).color(Colors.DarkSlateGray).rounded(px(6))

sheet.select(".time-display").font(
    size=rem(4.5), weight=700, family="ui-monospace, 'SF Mono', monospace"
).color(Colors.Firebrick).rules(text_align="center").margin(
    top=rem(1.0), bottom=rem(1.0)
)

sheet.select(".mode-label").font(size=rem(0.875), weight=600).color(
    Colors.SlateGray
).rules(text_align="center", text_transform="uppercase", letter_spacing="0.05em")

sheet.select(".controls").flexbox(direction="row", gap=px(8)).margin(top=rem(1.5))
sheet.select(".control-primary").rules(
    padding="12px 20px",
    border="none",
    cursor="pointer",
    font_size="1rem",
    font_weight=600,
    flex="1",
).background(Colors.Firebrick).color(Colors.White).rounded(px(6))
sheet.select(".control-secondary").rules(
    padding="12px 20px",
    border=f"1px solid {Colors.Gainsboro}",
    cursor="pointer",
    font_size="1rem",
    font_weight=600,
    flex="1",
).background(Colors.White).color(Colors.DarkSlateGray).rounded(px(6))

sheet.select(".footer").margin(top=rem(2.0)).flexbox(
    direction="row", gap=px(6), align="center", justify="center"
).font(size=rem(0.875)).color(Colors.SlateGray)
sheet.select(".session-count").font(weight=700).color(Colors.Firebrick)


# ---------------------------------------------------------------------------
# View — PWA enabled via Manifest passed to @app.view
# ---------------------------------------------------------------------------


pomodoro_manifest = Manifest(
    name="Pomodoro",
    short_name="🍅",
    description="A minimal pomodoro timer that works offline.",
    background_color="#ffffff",
    theme_color="#dc2626",
    display="standalone",
)


@app.view("/", pwa=pomodoro_manifest)
def index():
    doc = Document(title="Pomodoro")
    doc.style(href="/style.css", sheet=sheet)

    with doc.body as body:
        with body.div(classes="page") as page:
            page.h1(text="🍅 Pomodoro").classes("page-title")
            page.p(text="Work in focused bursts. Refresh-safe. Offline-ready.").classes(
                "subtitle"
            )

            # Mode selector — three buttons, each carrying its mode in data-mode.
            # `attrs(**{"data-mode": ...})` because kwargs can't have dashes and
            # `data_mode=` would render literally (gap 7.4 — no underscore strip).
            with page.div(classes="mode-row") as modes:
                modes.button(text="Work", classes="mode-button").attrs(
                    type="button", **{"data-mode": "work"}
                ).on("click", switch_mode)
                modes.button(text="Short break", classes="mode-button").attrs(
                    type="button", **{"data-mode": "short"}
                ).on("click", switch_mode)
                modes.button(text="Long break", classes="mode-button").attrs(
                    type="button", **{"data-mode": "long"}
                ).on("click", switch_mode)

            # Big time readout — text bound to time_display so the tick loop
            # mutating PomodoroState.time_display updates the DOM live.
            page.div(classes="time-display").text(PomodoroState.time_display)

            # Current mode label below the time.
            page.div(classes="mode-label").text(PomodoroState.mode)

            # Primary controls — toggle (Start/Pause flips reactively) + Reset.
            with page.div(classes="controls") as controls:
                controls.button(classes="control-primary").attrs(type="button").text(
                    PomodoroState.toggle_label
                ).on("click", toggle)
                controls.button(text="Reset", classes="control-secondary").attrs(
                    type="button"
                ).on("click", reset)

            # Session counter footer.
            with page.div(classes="footer") as footer:
                footer.span(text="Completed work sessions: ")
                footer.span(classes="session-count").text(PomodoroState.sessions)

    return doc


if __name__ == "__main__":
    app.run()
