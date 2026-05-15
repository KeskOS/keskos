from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from .actions import builtin_result, execute_action
from .cache import cache_dir, warm_caches
from .models import Result, SearchContext
from .providers import apps, calc, commands, files, places, power, recent, settings, units, web, windows
from .recent import RecentStore
from .utils import CATEGORY_WEIGHTS, escape_markup, is_math_expression, launcher_debug_log, normalize_text


MODE_NAMES = {
    "main": "kesk-main",
    "apps": "kesk-apps",
    "windows": "kesk-windows",
    "settings": "kesk-settings",
    "power": "kesk-power",
}

MODE_PROMPTS = {
    "main": "KESK >",
    "apps": "APPS >",
    "windows": "WINDOWS >",
    "settings": "SETTINGS >",
    "power": "POWER >",
}

def debug_log(message: str) -> None:
    launcher_debug_log(message)


def effective_query(explicit_query: str, entry_text: str) -> str:
    if explicit_query.strip():
        return explicit_query
    if entry_text.strip():
        return entry_text
    return explicit_query


def action_digest(action: dict) -> str:
    action_type = action.get("type")
    if action_type == "app":
        return f"app:{action.get('desktop_id', '')}"
    if action_type == "path":
        return f"path:{action.get('path', '')}"
    if action_type == "settings":
        return f"settings:{action.get('module', '')}"
    if action_type == "web":
        return f"web:{action.get('url', '')}"
    if action_type == "power":
        return f"power:{action.get('name', '')}"
    if action_type == "window":
        return f"window:{action.get('window_id', '')}"
    if action_type == "browser":
        return f"browser:{action.get('url', '')}"
    if action_type == "terminal":
        return "builtin:terminal"
    if action_type == "command":
        return f"command:{action.get('command', '')}"
    if action_type == "copy":
        return f"copy:{action.get('value', '')}"
    if action_type == "switch-mode":
        return f"switch:{action.get('mode', '')}"
    return json.dumps(action, sort_keys=True, ensure_ascii=True)


def serialize_info(result: Result) -> str:
    payload = {
        "id": result.id,
        "title": result.title,
        "subtitle": result.subtitle,
        "category": result.category,
        "action": result.action,
        "copy_value": result.copy_value,
        "dangerous": result.dangerous,
        "recent_key": result.recent_key,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def deserialize_info(raw: str | None) -> Result | None:
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    action = payload.get("action")
    if not isinstance(action, dict):
        return None
    return Result(
        id=str(payload.get("id", "selection")),
        title=str(payload.get("title", "Selected item")),
        subtitle=str(payload.get("subtitle", "")),
        category=str(payload.get("category", "")),
        score=0,
        action=action,
        copy_value=payload.get("copy_value"),
        dangerous=bool(payload.get("dangerous")),
        recent_key=payload.get("recent_key"),
    )


def load_state() -> dict:
    raw = os.environ.get("ROFI_DATA", "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_context(mode: str, query: str, recent_store: RecentStore) -> SearchContext:
    home = Path.home()
    session_type = os.environ.get("XDG_SESSION_TYPE", "")
    if not session_type:
        session_type = "wayland" if os.environ.get("WAYLAND_DISPLAY") else "x11"

    return SearchContext(
        mode=mode,
        query=query,
        session_type=session_type.lower(),
        home=home,
        cache_dir=cache_dir(),
        data_dir=recent_store.path.parent,
        recent_boosts=recent_store.boost_map(),
    )


def home_results(context: SearchContext) -> list[Result]:
    homepage_url = "/usr/share/keskos/browser-home/index.html"
    if context.session_type == "wayland":
        windows_action = {"type": "launcher", "mode": "windows"}
        if shutil.which("kdotool"):
            windows_subtitle = "Meta+Shift+Tab | Wayland via kdotool"
        else:
            windows_subtitle = "Meta+Shift+Tab | Wayland helper missing"
    else:
        windows_action = {"type": "launcher", "mode": "windows"}
        windows_subtitle = "Meta+Shift+Tab"
    return [
        Result(id="home:terminal", title="Terminal", subtitle="Meta+T or Meta+Enter", category="Home", score=7000, action={"type": "terminal"}),
        Result(id="home:files", title="Files", subtitle="Meta+N", category="Home", score=6990, action={"type": "path", "path": str(context.home), "prefer_dolphin": True}),
        Result(id="home:browser", title="Browser", subtitle="Meta+B | Preferred browser homepage", category="Home", score=6980, action={"type": "browser", "url": f"file://{homepage_url}" if Path(homepage_url).is_file() else None}),
        Result(id="home:apps", title="App Search", subtitle="Meta+Shift+K", category="Home", score=6970, action={"type": "launcher", "mode": "apps"}),
        Result(id="home:windows", title="Active Windows", subtitle=windows_subtitle, category="Home", score=6960, action=windows_action),
        Result(id="home:settings", title="Settings", subtitle="Meta+Shift+S", category="Home", score=6950, action={"type": "launcher", "mode": "settings"}),
        Result(id="home:power", title="Power", subtitle="Meta+P", category="Home", score=6940, action={"type": "launcher", "mode": "power"}),
    ]


def empty_state_result(mode: str, query: str) -> Result:
    title = "No results yet"
    subtitle = "Keep typing to search apps, files, settings, web shortcuts, and tools."

    if mode == "main" and is_math_expression(query):
        subtitle = "Calculator results appear once the expression is complete."
    elif mode == "apps":
        subtitle = "No matching desktop apps were found for the current query."
    elif mode == "windows":
        subtitle = "No matching open windows were found for the current query."
    elif mode == "settings":
        subtitle = "No matching KDE settings shortcut was found for the current query."
    elif mode == "power":
        subtitle = "No matching power or session action was found for the current query."

    return Result(
        id=f"status:{mode}:{query}",
        title=title,
        subtitle=subtitle,
        category="Status",
        score=-1,
        action={"type": "noop"},
        terms=[query],
        nonselectable=True,
        permanent=True,
    )


def dedupe_results(results: list[Result]) -> list[Result]:
    deduped: dict[str, Result] = {}
    for result in results:
        key = result.recent_key or action_digest(result.action)
        current = deduped.get(key)
        if current is None or result.score > current.score:
            deduped[key] = result
    return list(deduped.values())


def build_results(mode: str, query: str, store: RecentStore, state: dict) -> tuple[list[Result], str | None]:
    context = build_context(mode, query, store)
    message = state.get("message")

    if mode == "main" and not query.strip():
        return home_results(context), message

    results: list[Result] = []
    if mode == "main":
        results.extend(calc.search(context, query))
        results.extend(units.search(context, query))
        results.extend(recent.search(context, query, store))
        results.extend(settings.search(context, query))
        results.extend(apps.search(context, query))
        # results.extend(places.search(context, query))  # Disabled for performance
        # results.extend(files.search(context, query))  # Disabled for performance
        results.extend(web.search(context, query))
        results.extend(power.search(context, query))
        results.extend(commands.search(context, query))
    elif mode == "apps":
        results.extend(apps.search(context, query, apps_only=True))
    elif mode == "windows":
        results.extend(windows.search(context, query))
    elif mode == "settings":
        results.extend(settings.search(context, query, settings_only=True))
    elif mode == "power":
        results.extend(power.search(context, query, power_only=True))

    results = dedupe_results(results)
    confirm_digest = state.get("confirm")
    if confirm_digest:
        for result in results:
            if action_digest(result.action) == confirm_digest:
                result.urgent = True
                if "Press Enter again to confirm" not in result.subtitle:
                    result.subtitle = f"{result.subtitle} | Press Enter again to confirm"
                break

    results.sort(key=lambda result: (-result.score, result.title.lower()))
    limit = 80 if mode in {"apps", "windows", "settings", "power"} else 40
    results = results[:limit]

    if query.strip() and not results:
        results = [empty_state_result(mode, query)]

    return results, message


def format_display(result: Result) -> str:
    title = escape_markup(result.title)
    category = escape_markup(result.category)
    subtitle = escape_markup(result.subtitle)
    return f"{title} <span alpha='55%'>[{category}] {subtitle}</span>"


def row_search_text(result: Result) -> str:
    parts = [result.title, result.subtitle, result.category, *result.terms]
    return " ".join(part for part in parts if part).strip()


def emit_rows(mode: str, query: str, store: RecentStore, state: dict) -> None:
    results, message = build_results(mode, query, store, state)
    print(f"\0prompt\x1f{MODE_PROMPTS[mode]}")
    print("\0markup-rows\x1ftrue")
    print("\0use-hot-keys\x1ftrue")
    print("\0keep-filter\x1ftrue")
    print("\0keep-selection\x1ftrue")
    if message:
        print(f"\0message\x1f{escape_markup(message)}")
    state["message"] = message or ""
    print(f"\0data\x1f{json.dumps(state, ensure_ascii=True, separators=(',', ':'))}")

    for result in results:
        row = row_search_text(result)
        options = [f"display\x1f{format_display(result)}", f"info\x1f{serialize_info(result)}"]
        meta_text = " ".join(result.terms)
        if meta_text:
            options.append(f"meta\x1f{meta_text}")
        if result.nonselectable:
            options.append("nonselectable\x1ftrue")
        if result.permanent:
            options.append("permanent\x1ftrue")
        if result.urgent:
            options.append("urgent\x1ftrue")
        if result.active:
            options.append("active\x1ftrue")
        if result.icon:
            options.append(f"icon\x1f{result.icon}")
        print(f"{row}\0" + "\x1f".join(options))


def resolve_custom_selection(mode: str, query: str, entry_text: str, store: RecentStore) -> Result | None:
    fallback_query = query if query.strip() else ""
    results, _ = build_results(mode, fallback_query, store, {})
    if not results and query.strip():
        results, _ = build_results(mode, "", store, {})

    normalized_entry = normalize_text(entry_text)
    normalized_query = normalize_text(query)
    if normalized_entry and normalized_query and normalized_entry == normalized_query:
        for result in results:
            if not result.nonselectable:
                return result

    if normalized_entry:
        direct_matches: list[Result] = []
        row_matches: list[Result] = []
        for result in results:
            if result.nonselectable:
                continue
            title_text = normalize_text(result.title)
            row_text = normalize_text(row_search_text(result))
            if normalized_entry == title_text or normalized_entry == row_text:
                return result
            if title_text and title_text in normalized_entry:
                direct_matches.append(result)
            elif row_text and row_text in normalized_entry:
                row_matches.append(result)

        if len(direct_matches) == 1:
            return direct_matches[0]
        if direct_matches:
            direct_matches.sort(key=lambda result: (-len(result.title), -result.score))
            return direct_matches[0]
        if len(row_matches) == 1:
            return row_matches[0]
        if row_matches:
            row_matches.sort(key=lambda result: (-len(row_search_text(result)), -result.score))
            return row_matches[0]

    for result in results:
        if not result.nonselectable:
            return result
    return None


def maybe_confirm_or_execute(mode: str, result: Result, state: dict, store: RecentStore) -> tuple[bool, dict]:
    digest = action_digest(result.action)
    debug_log(f"selected={result.id} action={json.dumps(result.action, ensure_ascii=True, sort_keys=True)} query={os.environ.get('ROFI_INPUT', '')!r} retv={os.environ.get('ROFI_RETV', '')}")
    requires_confirmation = result.dangerous and mode != "power"
    if requires_confirmation and state.get("confirm") != digest:
        state["confirm"] = digest
        state["message"] = f"Confirm action: {result.title}"
        debug_log(f"confirm-required={digest}")
        return False, state

    state.pop("confirm", None)
    state.pop("message", None)
    outcome = execute_action(result)
    debug_log(
        "outcome="
        + json.dumps(
            {
                "close_rofi": outcome.close_rofi,
                "switch_mode": outcome.switch_mode,
                "message": outcome.message,
                "copied": outcome.copied,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    if outcome.message and not outcome.close_rofi:
        state["message"] = outcome.message
    if outcome.switch_mode:
        print(f"\0switch-mode\x1f{outcome.switch_mode}")
    if outcome.close_rofi:
        store.record(result)
    return outcome.close_rofi, state


def script_mode(mode: str, entry_text: str = "") -> int:
    store = RecentStore()
    retv = int(os.environ.get("ROFI_RETV", "0"))
    raw_query = os.environ.get("ROFI_INPUT", "")
    query = effective_query(raw_query, entry_text)
    state = load_state()
    debug_log(
        f"script mode={mode} retv={retv} raw_query={raw_query!r} query={query!r} "
        f"entry_text={entry_text!r} argv={sys.argv!r} info={os.environ.get('ROFI_INFO', '')!r} "
        f"data={os.environ.get('ROFI_DATA', '')!r}"
    )

    if retv == 10:
        state.pop("confirm", None)
        state.pop("message", None)
        emit_rows(mode, query, store, state)
        return 0

    if retv == 11:
        selected = deserialize_info(os.environ.get("ROFI_INFO"))
        if selected and selected.copy_value:
            copied_result = Result(
                id=selected.id,
                title=selected.title,
                subtitle=selected.subtitle,
                category=selected.category,
                score=0,
                action={"type": "copy", "value": selected.copy_value},
                copy_value=selected.copy_value,
                recent_key=selected.recent_key,
            )
            outcome = execute_action(copied_result)
            state["message"] = outcome.message or ""
        else:
            state["message"] = "Selected result is not copyable."
        emit_rows(mode, query, store, state)
        return 0

    if retv == 2:
        if mode == "power":
            selected = deserialize_info(os.environ.get("ROFI_INFO"))
            if selected is not None:
                should_close, next_state = maybe_confirm_or_execute(mode, selected, state, store)
                if should_close:
                    return 0
                emit_rows(mode, query, store, next_state)
                return 0

            selected = resolve_custom_selection(mode, raw_query, entry_text, store)
            if selected is not None:
                should_close, next_state = maybe_confirm_or_execute(mode, selected, state, store)
                if should_close:
                    return 0
                emit_rows(mode, raw_query, store, next_state)
                return 0

        state.pop("confirm", None)
        state.pop("message", None)
        emit_rows(mode, query, store, state)
        return 0

    if retv == 1:
        selected = deserialize_info(os.environ.get("ROFI_INFO"))
        if selected is None:
            selected = resolve_custom_selection(mode, raw_query, entry_text, store)
        if selected is None:
            emit_rows(mode, query, store, state)
            return 0

        should_close, next_state = maybe_confirm_or_execute(mode, selected, state, store)
        if should_close:
            return 0
        emit_rows(mode, query, store, next_state)
        return 0

    emit_rows(mode, query, store, state)
    return 0


def query_mode(mode: str, query: str) -> int:
    store = RecentStore()
    results, _ = build_results(mode, query, store, {})
    for result in results:
        print(f"{result.category}\t{result.title}\t{result.subtitle}")
    return 0


def builtin_action(name: str) -> int:
    result = builtin_result(name, Path.home())
    execute_action(result)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="kesk_runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    script_parser = subparsers.add_parser("script")
    script_parser.add_argument("--mode", choices=sorted(MODE_NAMES), required=True)
    script_parser.add_argument("--entry-text", default="")

    warm_parser = subparsers.add_parser("warm")
    warm_parser.add_argument("--sync-files", action="store_true")

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("--mode", choices=sorted(MODE_NAMES), default="main")
    query_parser.add_argument("--query", default="")

    action_parser = subparsers.add_parser("action")
    action_parser.add_argument("name", choices=["terminal", "files", "browser"])

    args = parser.parse_args()

    if args.command == "script":
        return script_mode(args.mode, args.entry_text)
    if args.command == "warm":
        warm_caches(sync_files=bool(args.sync_files))
        return 0
    if args.command == "query":
        return query_mode(args.mode, args.query)
    if args.command == "action":
        return builtin_action(args.name)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
