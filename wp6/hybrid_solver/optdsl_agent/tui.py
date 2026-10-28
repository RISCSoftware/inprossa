"""A terminal UI for the harness, built on ``textual``.

Why a TUI at all: the line REPL is fine for one question, but the harness is
inherently multi-pane — you want the model digest, the conversation, and the
last solve result visible at once, and you want to scroll back through tool
output without losing your place.

``textual`` is an *optional* dependency. The core harness must stay installable
with only ``minizinc``, so this module imports it lazily and the CLI reports a
clear install hint when it is missing.

The TUI is a thin shell: every action delegates to :mod:`optdsl_agent.commands`
or the tool registry, so it cannot drift from the REPL.
"""

from __future__ import annotations

from typing import Any

from .agent import AgentLoop
from .commands import (
    HELP_TEXT,
    _turn_trace,
    describe_session,
    is_command,
    matching_commands,
    run_command,
)
from .config import AgentConfig
from .digest import model_digest
from .session import Session

INSTALL_HINT = (
    "The TUI needs the optional 'textual' dependency:\n"
    "    pip install textual\n"
    "or, with the project extra:\n"
    "    pip install -e .[tui]"
)


def textual_available() -> bool:
    """True when ``textual`` can be imported."""
    try:
        import textual  # noqa: F401
    except ImportError:
        return False
    return True


def build_app(session: Session, client: Any, config: AgentConfig) -> Any:
    """Construct the Textual app.

    Kept separate from :func:`run_tui` so tests can mount the app with
    ``app.run_test()`` instead of taking over the terminal.
    """
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, ScrollableContainer
    from textual.widgets import Footer, Header, Input, OptionList, RichLog, Static
    from textual.widgets.option_list import Option

    class OptDSLApp(App[None]):
        """Three panes: model digest, conversation, and status."""

        CSS = """
        Screen { layout: vertical; }
        #body { height: 1fr; }
        #digest {
            width: 42%;
            border: round $primary;
            padding: 0 1;
            scrollbar-gutter: stable;
        }
        #digest.source-view {
            width: 55%;
            border: round $accent;
        }
        #digest-text {
            width: 1fr;
            height: auto;
        }
        #conversation {
            width: 1fr;
            border: round $secondary;
            padding: 0 1;
        }
        #status {
            height: 1;
            background: $panel;
            color: $text-muted;
            padding: 0 1;
        }
        #completions {
            display: none;
            height: auto;
            max-height: 12;
            border: round $accent;
            background: $surface;
        }
        #completions.visible { display: block; }
        #prompt { dock: bottom; }
        """

        BINDINGS = [
            Binding("ctrl+c", "quit", "Quit", show=True),
            Binding("ctrl+l", "clear", "Clear", show=True),
            Binding("f4", "toggle_left", "Left: digest/source", show=True),
            Binding("f1", "help", "Help", show=True),
            Binding("f5", "analyze", "Analyze", show=True),
        ]

        def __init__(self) -> None:
            super().__init__()
            self.session = session
            self.config = config
            self.loop = AgentLoop(session, client)
            self._busy = False
            #: What the left pane shows: "digest" (summary) or "source".
            self._left_view = "digest"
            #: Command names currently offered in the popup, in display order.
            self._completion_names: list[str] = []

        # -- layout --------------------------------------------------------

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal(id="body"):
                # ScrollableContainer makes the left pane focusable, so wheel,
                # PgUp/PgDn and arrow keys can scroll the digest/source text.
                with ScrollableContainer(id="digest"):
                    yield Static(id="digest-text", markup=False)
                yield RichLog(id="conversation", wrap=True, markup=False, highlight=False)
            yield Static(id="status")
            yield OptionList(id="completions")
            yield Input(placeholder="Ask a question, or type /help", id="prompt")
            yield Footer()

        def on_mount(self) -> None:
            self.title = "OptDSL agent"
            self.sub_title = session.label
            self._refresh_left()
            self._set_status(self._status_line())
            self._write(
                f"Loaded {session.label}.\n"
                "Type /help for commands, or / to see them. F1 shows help, F5 re-analyses, "
                "F4 toggles the left pane between digest and source.\n"
            )
            self.query_one("#prompt", Input).focus()

        # -- completion popup ----------------------------------------------

        def on_input_changed(self, event: Any) -> None:
            """Show or hide the command popup as the user types.

            The popup appears only while the command word is being typed: once
            there is a space the user is writing an argument, and offering
            command names there would be wrong.
            """
            self._update_completions(event.value)

        def _update_completions(self, value: str) -> None:
            popup = self._popup()
            if popup is None:
                # A Changed message can arrive after the screen is torn down.
                return

            if not value.startswith("/") or " " in value:
                self._hide_completions()
                return

            matches = matching_commands(value)
            if not matches:
                self._hide_completions()
                return

            self._completion_names = [spec.name for spec in matches]
            popup.clear_options()
            for spec in matches:
                # The signature carries the argument hint; the help explains it.
                popup.add_option(
                    Option(f"{spec.signature:<22} {spec.help}", id=spec.name)
                )
            popup.add_class("visible")
            popup.highlighted = 0

        def _popup(self) -> Any:
            """The completion list, or ``None`` when it is not mounted."""
            found = self.query("#completions")
            return found.first(OptionList) if found else None

        def _hide_completions(self) -> None:
            popup = self._popup()
            if popup is None:
                return
            popup.remove_class("visible")
            popup.clear_options()
            self._completion_names = []

        def _completions_visible(self) -> bool:
            popup = self._popup()
            return popup is not None and popup.has_class("visible")

        def _accept_completion(self, name: str) -> None:
            """Insert the chosen command and close the popup."""
            prompt = self.query_one("#prompt", Input)
            prompt.value = f"/{name} "
            prompt.cursor_position = len(prompt.value)
            self._hide_completions()
            prompt.focus()

        def on_option_list_option_selected(self, event: Any) -> None:
            if event.option.id:
                self._accept_completion(event.option.id)

        def on_key(self, event: Any) -> None:
            """Route navigation keys to the popup while it is open.

            Textual would otherwise send Up/Down to the Input's history and Enter
            straight to submit, so the popup has to intercept them first.
            """
            if not self._completions_visible():
                return

            popup = self.query_one("#completions", OptionList)

            if event.key == "down":
                popup.action_cursor_down()
                event.stop()
            elif event.key == "up":
                popup.action_cursor_up()
                event.stop()
            elif event.key == "tab":
                if popup.highlighted is not None and self._completion_names:
                    self._accept_completion(self._completion_names[popup.highlighted])
                event.stop()
            elif event.key == "escape":
                self._hide_completions()
                event.stop()
            elif event.key == "enter":
                # Enter on a highlighted entry completes it; a second Enter
                # submits. That keeps the popup from swallowing the command.
                if popup.highlighted is not None and self._completion_names:
                    self._accept_completion(self._completion_names[popup.highlighted])
                    event.stop()

        # -- actions -------------------------------------------------------

        def action_clear(self) -> None:
            self.query_one("#conversation", RichLog).clear()

        def action_help(self) -> None:
            self._write(HELP_TEXT)

        def action_analyze(self) -> None:
            self._left_view = "digest"
            self._refresh_left()
            self._write("Model re-analysed (left pane: digest).")

        def action_toggle_left(self) -> None:
            """Switch the left pane between the model digest and the full source."""
            self._left_view = "source" if self._left_view == "digest" else "digest"
            self._refresh_left()
            # Show the top of the new content instead of a stale scroll offset.
            self.query_one("#digest").scroll_home(animate=False)
            self._set_status(self._status_line())
            self._write(f"left pane: {self._left_view}")

        # -- input ---------------------------------------------------------

        def on_input_submitted(self, event: Any) -> None:
            line = event.value.strip()
            prompt = self.query_one("#prompt", Input)
            prompt.value = ""
            self._hide_completions()
            if not line:
                return
            if self._busy:
                self._write("Still working on the previous request.")
                return

            self._write(f"\n> {line}\n")

            if is_command(line):
                self._run_command(line)
                return

            self._run_agent(line)

        def _run_command(self, line: str) -> None:
            """Run a slash command off the UI thread.

            ``/solve`` and ``/lns`` block for as long as the solver runs, and
            ``/tune`` for minutes. Running them on the event loop froze the
            interface, and ``/solve`` additionally failed outright because the
            MiniZinc runner starts its own event loop.
            """
            self._busy = True
            self._set_status("working...")

            def progress(text: str) -> None:
                self.call_from_thread(self._write, text)

            def work() -> None:
                try:
                    result = run_command(line, self.session, self.loop, self.config, progress=progress)
                except Exception as exc:  # noqa: BLE001 - surfaced in the pane
                    self.call_from_thread(self._write, f"error: {type(exc).__name__}: {exc}")
                    self.call_from_thread(self._set_status, "error")
                    self.call_from_thread(self._finish)
                    return

                if result.quit:
                    self.call_from_thread(self.exit)
                    return

                if result.trace:
                    self.call_from_thread(self._write_gray, result.trace)
                if result.text:
                    self.call_from_thread(self._write, result.text)
                for artifact in result.artifacts:
                    self.call_from_thread(self._write, f"wrote {artifact}")
                self.call_from_thread(self._refresh_left)
                self.call_from_thread(
                    self._set_status, self._status_line()
                )
                self.call_from_thread(self._finish)

            self.run_worker(work, thread=True, exclusive=True)

        def _run_agent(self, line: str) -> None:
            """Run the agent loop off the UI thread.

            A model call takes seconds; blocking the event loop would freeze the
            interface and make the app look hung.
            """
            self._busy = True
            self._set_status("thinking...")

            def work() -> None:
                try:
                    turn = self.loop.run(line)
                except Exception as exc:  # noqa: BLE001 - surfaced in the pane
                    self.call_from_thread(self._write, f"error: {type(exc).__name__}: {exc}")
                    self.call_from_thread(self._set_status, "error")
                    self.call_from_thread(self._finish)
                    return

                text = turn.final_text or "(no reply)"
                self.call_from_thread(self._write_gray, _turn_trace(turn))
                self.call_from_thread(self._write, text)
                if turn.stopped_reason:
                    self.call_from_thread(self._write, f"[stopped: {turn.stopped_reason}]")
                self.call_from_thread(self._refresh_left)
                self.call_from_thread(
                    self._set_status, self._status_line()
                )
                self.call_from_thread(self._finish)

            self.run_worker(work, thread=True, exclusive=True)

        def _finish(self) -> None:
            self._busy = False
            self.query_one("#prompt", Input).focus()

        # -- helpers -------------------------------------------------------

        def _write(self, text: str) -> None:
            self.query_one("#conversation", RichLog).write(text)

        def _write_gray(self, text: str | None) -> None:
            """Show a light-grey trace window (agent activity / tool calls)."""
            if not text:
                return
            from rich.panel import Panel
            from rich.text import Text

            self.query_one("#conversation", RichLog).write(
                Panel(Text(text), border_style="grey37", expand=False)
            )

        def _set_status(self, text: str) -> None:
            self.query_one("#status", Static).update(text)

        def _status_line(self) -> str:
            """Session summary plus which left-pane view is active."""
            return (
                describe_session(self.session, self.config)
                + f" | left pane: {self._left_view}"
            )

        def _refresh_left(self) -> None:
            """Render the left pane according to the selected view."""
            text = self.query_one("#digest-text", Static)
            if self._left_view == "source":
                self.query_one("#digest").add_class("source-view")
                text.update(self.session.source)
                return
            self.query_one("#digest").remove_class("source-view")
            self._refresh_digest()

        def _refresh_digest(self) -> None:
            try:
                digest = model_digest(self.session.source)
            except Exception as exc:  # noqa: BLE001 - a broken model must not kill the UI
                digest = f"could not analyse the model: {exc}"
            self.query_one("#digest-text", Static).update(digest)

    return OptDSLApp()


def run_tui(session: Session, client: Any, config: AgentConfig) -> int:
    """Start the TUI. Returns a process exit code."""
    if not textual_available():
        print(INSTALL_HINT)
        return 2

    build_app(session, client, config).run()
    return 0
