#!/usr/bin/env python3
"""Рабочие столы i3: последняя выбранная программа, ширина ячейки 160 px.

Запускается как custom/script модуль Polybar. Нужен Xorg, i3-msg и libXft.
Шрифт должен совпадать с font-0 в конфиге Polybar.
"""
import ctypes
import ctypes.util
import argparse
import configparser
import json
import re
import subprocess
import sys
import time
from pathlib import Path

CELL_WIDTH = 160
PADDING = 8
FONT = "Calibri:style=Bold:size=16"
DISPLAY_NAMES = {"sublime_text": "Sublime", "kitty": "Kitty",
                 "chromium": "Chromium", "firefox": "Firefox"}


class GlyphInfo(ctypes.Structure):
    _fields_ = [("width", ctypes.c_ushort), ("height", ctypes.c_ushort),
                ("x", ctypes.c_short), ("y", ctypes.c_short),
                ("xOff", ctypes.c_short), ("yOff", ctypes.c_short)]


class TextWidth:
    def __init__(self, font=None):
        self.x11 = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
        self.xft = ctypes.CDLL(ctypes.util.find_library("Xft") or "libXft.so.2")
        ptr = ctypes.c_void_p
        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x11.XOpenDisplay.restype = ptr
        self.x11.XDefaultScreen.argtypes = [ptr]
        self.x11.XDefaultScreen.restype = ctypes.c_int
        self.x11.XCloseDisplay.argtypes = [ptr]
        self.xft.XftFontOpenName.argtypes = [ptr, ctypes.c_int, ctypes.c_char_p]
        self.xft.XftFontOpenName.restype = ptr
        self.xft.XftFontClose.argtypes = [ptr, ptr]
        self.xft.XftTextExtentsUtf8.argtypes = [ptr, ptr, ctypes.c_char_p,
                                               ctypes.c_int, ctypes.POINTER(GlyphInfo)]
        self.display = self.x11.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("Не удалось подключиться к Xorg")
        # Polybar adds its vertical offset after a semicolon; it is not part
        # of the fontconfig pattern used for measuring horizontal width.
        font = (font or FONT).split(";", 1)[0]
        self.font = self.xft.XftFontOpenName(self.display, self.x11.XDefaultScreen(self.display), font.encode())
        if not self.font:
            self.x11.XCloseDisplay(self.display)
            raise RuntimeError("Не удалось открыть шрифт " + font)

    def __call__(self, text):
        data = text.encode("utf-8")
        metrics = GlyphInfo()
        self.xft.XftTextExtentsUtf8(self.display, self.font, data, len(data), ctypes.byref(metrics))
        return metrics.xOff

    def close(self):
        self.xft.XftFontClose(self.display, self.font)
        self.x11.XCloseDisplay(self.display)


def focused_leaf(node):
    children = node.get("nodes", []) + node.get("floating_nodes", [])
    by_id = {child.get("id"): child for child in children}
    ordered = [by_id[i] for i in node.get("focus", []) if i in by_id]
    ordered.extend(child for child in children if child not in ordered)
    for child in ordered:
        leaf = focused_leaf(child)
        if leaf is not None:
            return leaf
    return node if node.get("window") is not None else None


def get_workspaces(tree):
    found = []
    def visit(node):
        if node.get("type") == "workspace" and not str(node.get("name", "")).startswith("__"):
            found.append(node)
            return
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            visit(child)
    visit(tree)
    return sorted(found, key=lambda ws: (ws.get("num", -1) < 0, ws.get("num", -1), ws.get("name", "")))


def safe_text(value):
    # Недоверенное имя X11 не должно становиться управляющим тегом Polybar.
    return re.sub(r"[^\w .+-]", "", str(value), flags=re.ASCII).strip()


def label(workspace):
    number = workspace.get("num", -1)
    prefix = str(number) + " " if type(number) is int and number >= 0 else ""
    leaf = focused_leaf(workspace)
    if leaf:
        props = leaf.get("window_properties") or {}
        raw = safe_text(props.get("class") or props.get("instance") or "")
        app = DISPLAY_NAMES.get(raw.lower(), raw)
        if app:
            return prefix + app
        return prefix + "Окно"
    return prefix + "Пусто"


def truncate(text, measure, limit):
    if measure(text) <= limit:
        return text
    while text and measure(text + "...") > limit:
        text = text[:-1]
    return text + "..." if measure(text + "...") <= limit else ""


def render(workspaces, measure, focused_bg="#bd2d5e", focused_fg="#000000",
           unfocused_bg="#151419", unfocused_fg="#ed2467"):
    cells = []
    for workspace in workspaces:
        text = truncate(label(workspace), measure, CELL_WIDTH - PADDING * 2)
        remainder = max(0, CELL_WIDTH - PADDING - measure(text))
        def contains_focus(node):
            return bool(node.get("focused")) or any(
                contains_focus(child)
                for child in node.get("nodes", []) + node.get("floating_nodes", [])
            )
        focused = contains_focus(workspace)
        bg, fg = (focused_bg, focused_fg) if focused else (unfocused_bg, unfocused_fg)
        number = workspace.get("num", -1)
        action = f"%{{A1:i3-msg workspace number {number}:}}" if type(number) is int and number >= 0 else ""
        end_action = "%{A}" if action else ""
        cells.append(f"{action}%{{B{bg}}}%{{F{fg}}}%{{O{PADDING}}}{text}%{{O{remainder}}}%{{F-}}%{{B-}}{end_action}")
    return "".join(cells)


def snapshot():
    result = subprocess.run(["i3-msg", "-t", "get_tree"], check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    return get_workspaces(json.loads(result.stdout))


def read_appearance(path):
    """Читаем шрифт и цвета непосредственно из основного конфига Polybar."""
    config = configparser.ConfigParser(interpolation=None)
    with Path(path).open(encoding="utf-8") as file:
        config.read_file(file)

    def value(section, key, seen=None):
        seen = set() if seen is None else seen
        pair = (section, key)
        if pair in seen:
            raise ValueError(f"Циклическая ссылка в конфиге: {section}.{key}")
        seen.add(pair)
        result = config[section][key].strip().strip('"')
        reference = re.fullmatch(r"\$\{([^.}]+)\.([^}]+)\}", result)
        if reference:
            return value(reference.group(1), reference.group(2), seen)
        return result

    return {
        "font": value("bar/main", "font-0"),
        "focused_bg": value("colors", "workspace-selected"),
        "focused_fg": value("colors", "workspace-selected-text"),
        "unfocused_bg": value("colors", "background"),
        "unfocused_fg": value("colors", "foreground"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", default=FONT)
    parser.add_argument("--focused-bg", default="#bd2d5e")
    parser.add_argument("--focused-fg", default="#000000")
    parser.add_argument("--unfocused-bg", default="#151419")
    parser.add_argument("--unfocused-fg", default="#ed2467")
    parser.add_argument("--from-config", action="store_true")
    args = parser.parse_args()
    if args.from_config:
        try:
            appearance = read_appearance(Path.home() / ".config/polybar/config.ini")
            for key, val in appearance.items():
                setattr(args, key, val)
        except (OSError, ValueError, KeyError, configparser.Error) as error:
            parser.error(f"Не удалось прочитать настройки Polybar: {error}")
    for color in (args.focused_bg, args.focused_fg, args.unfocused_bg, args.unfocused_fg):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", color):
            parser.error("Цвет должен иметь вид #RRGGBB или #AARRGGBB")
    colors = dict(focused_bg=args.focused_bg, focused_fg=args.focused_fg,
                  unfocused_bg=args.unfocused_bg, unfocused_fg=args.unfocused_fg)
    width = TextWidth(args.font)
    try:
        while True:
            subscriber = None
            try:
                subscriber = subprocess.Popen(["i3-msg", "-t", "subscribe", "-m", '["workspace","window"]'],
                                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
                print(render(snapshot(), width, **colors), flush=True)
                for _ in subscriber.stdout:
                    print(render(snapshot(), width, **colors), flush=True)
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                print(f"Ошибка рабочих столов: {error}", file=sys.stderr, flush=True)
            finally:
                if subscriber is not None:
                    subscriber.terminate()
                    subscriber.wait()
            time.sleep(1)
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        width.close()


if __name__ == "__main__":
    main()
