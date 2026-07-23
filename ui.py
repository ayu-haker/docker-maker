#!/usr/bin/env python3
"""
ui.py
-----
Interactive, colored terminal UI for generate_compose.py.
No third-party packages required (pure Python stdlib) — works anywhere.

Usage:
    python3 ui.py
"""

import os
import sys
import time
import shutil

from generate_compose import (
    detect_stack,
    generate_compose,
    generate_dockerfile,
)

# --------------------------------------------------------------------------
# Colors
# --------------------------------------------------------------------------

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLUE = "\033[44m"


def supports_color():
    return sys.stdout.isatty()


if not supports_color():
    for attr in dir(C):
        if not attr.startswith("_"):
            setattr(C, attr, "")

WIDTH = min(shutil.get_terminal_size((80, 20)).columns, 78)


# --------------------------------------------------------------------------
# UI helpers
# --------------------------------------------------------------------------

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    title = "DOCKER COMPOSE AUTO-GENERATOR"
    print(f"{C.CYAN}{'═' * WIDTH}{C.RESET}")
    print(f"{C.CYAN}║{C.RESET}{C.BOLD}{title.center(WIDTH - 2)}{C.RESET}{C.CYAN}║{C.RESET}")
    print(f"{C.CYAN}{'═' * WIDTH}{C.RESET}")
    print()


def box(title, lines, color=C.BLUE):
    print(f"{color}┌─ {C.BOLD}{title}{C.RESET}{color} {'─' * max(0, WIDTH - len(title) - 5)}┐{C.RESET}")
    for line in lines:
        print(f"{color}│{C.RESET} {line}")
    print(f"{color}└{'─' * (WIDTH - 2)}┘{C.RESET}")
    print()


def spinner(message, seconds=0.9):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    steps = int(seconds / 0.08)
    for i in range(steps):
        frame = frames[i % len(frames)]
        sys.stdout.write(f"\r{C.YELLOW}{frame}{C.RESET} {message}")
        sys.stdout.flush()
        time.sleep(0.08)
    sys.stdout.write(f"\r{C.GREEN}✔{C.RESET} {message}{' ' * 10}\n")


def progress_bar(message, seconds=0.7):
    bar_width = 30
    steps = 20
    for i in range(steps + 1):
        filled = int(bar_width * i / steps)
        bar = "█" * filled + "░" * (bar_width - filled)
        pct = int(100 * i / steps)
        sys.stdout.write(f"\r{C.CYAN}{message}{C.RESET} [{C.GREEN}{bar}{C.RESET}] {pct:3d}%")
        sys.stdout.flush()
        time.sleep(seconds / steps)
    print()


def ask(prompt, default=None):
    suffix = f" {C.DIM}(default: {default}){C.RESET}" if default is not None else ""
    val = input(f"{C.MAGENTA}?{C.RESET} {prompt}{suffix}: {C.BOLD}").strip()
    print(C.RESET, end="")
    return val if val else default


def ask_yes_no(prompt, default=True):
    hint = "Y/n" if default else "y/N"
    val = input(f"{C.MAGENTA}?{C.RESET} {prompt} {C.DIM}[{hint}]{C.RESET}: {C.BOLD}").strip().lower()
    print(C.RESET, end="")
    if not val:
        return default
    return val.startswith("y")


SERVICE_LABELS = {
    "postgres": "PostgreSQL  (image: postgres:16-alpine, port 5432)",
    "mysql": "MySQL       (image: mysql:8, port 3306)",
    "mongo": "MongoDB     (image: mongo:7, port 27017)",
    "redis": "Redis       (image: redis:7-alpine, port 6379)",
}

LANGUAGE_LABELS = {
    "node": "Node.js",
    "python-django": "Python (Django)",
    "python-flask": "Python (Flask)",
    "python-fastapi": "Python (FastAPI)",
    "python-generic": "Python (generic)",
    "go": "Go",
    "static": "Static site (HTML/CSS/JS)",
    "unknown": "Could not detect — will fall back to a generic setup",
}


# --------------------------------------------------------------------------
# Main flow
# --------------------------------------------------------------------------

def main():
    clear()
    banner()

    print(f"{C.DIM}Ye tool tumhare project ko scan karke docker-compose.yml khud bana dega.{C.RESET}\n")

    path_input = ask("Project ka path do", default=".")
    root = os.path.abspath(path_input)

    if not os.path.isdir(root):
        print(f"\n{C.RED}✘ '{root}' ek valid directory nahi hai. Dobara try karo.{C.RESET}\n")
        sys.exit(1)

    print()
    spinner(f"Scanning {root} ...", seconds=1.0)
    info = detect_stack(root)

    lang_label = LANGUAGE_LABELS.get(info["language"], info["language"])
    detected_lines = [
        f"{C.BOLD}Stack:{C.RESET}   {C.GREEN}{lang_label}{C.RESET}",
        f"{C.BOLD}Port:{C.RESET}    {info['port']}",
        f"{C.BOLD}Dockerfile:{C.RESET} {'already exists — will be reused' if info['dockerfile_exists'] else 'not found — one will be generated'}",
    ]
    if info["services"]:
        detected_lines.append(f"{C.BOLD}Services:{C.RESET} " + ", ".join(sorted(info["services"])))
    else:
        detected_lines.append(f"{C.BOLD}Services:{C.RESET} none detected")

    box("Detection Result", detected_lines, color=C.BLUE)

    # --- App name & port ---
    default_name = os.path.basename(root.rstrip("/")) or "app"
    default_name = "".join(ch for ch in default_name.lower() if ch.isalnum() or ch in "-_") or "app"
    app_name = ask("App/service ka naam", default=default_name)
    port = ask("App port", default=str(info["port"]))
    try:
        port = int(port)
    except ValueError:
        print(f"{C.YELLOW}⚠ Invalid port, using detected default {info['port']}{C.RESET}")
        port = info["port"]

    # --- Confirm/toggle services ---
    selected_services = set(info["services"])
    if selected_services:
        print()
        print(f"{C.BOLD}Detected services — konse include karne hain?{C.RESET}")
        service_list = sorted(selected_services)
        for i, s in enumerate(service_list, 1):
            print(f"  {C.CYAN}{i}{C.RESET}. {SERVICE_LABELS.get(s, s)}")
        print(f"  {C.DIM}(Enter dabao sab include karne ke liye, ya un-check karne ke liye numbers comma se do, e.g. '2' hatane ke liye){C.RESET}")
        exclude = ask("Exclude karne ke liye numbers", default="")
        if exclude:
            try:
                idxs = {int(x.strip()) for x in exclude.split(",") if x.strip()}
                for i, s in enumerate(service_list, 1):
                    if i in idxs:
                        selected_services.discard(s)
            except ValueError:
                print(f"{C.YELLOW}⚠ Samajh nahi aaya, sab services include kar diya.{C.RESET}")

    include_dockerfile = True
    if info["dockerfile_exists"]:
        include_dockerfile = False
    elif info["language"] == "unknown":
        include_dockerfile = ask_yes_no("Stack detect nahi hua — phir bhi ek basic Dockerfile banau?", default=True)

    out_dir_input = ask("Output kahan likhna hai", default=root)
    out_dir = os.path.abspath(out_dir_input)
    os.makedirs(out_dir, exist_ok=True)

    print()
    info["services"] = selected_services
    progress_bar("Generating docker-compose.yml", seconds=0.8)
    compose_content = generate_compose(info, app_name, port)
    compose_path = os.path.join(out_dir, "docker-compose.yml")
    with open(compose_path, "w") as f:
        f.write(compose_content)

    dockerfile_path = None
    if include_dockerfile:
        progress_bar("Generating Dockerfile", seconds=0.6)
        dockerfile_content = generate_dockerfile(info)
        dockerfile_path = os.path.join(out_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

    print()
    result_lines = [
        f"{C.GREEN}✔{C.RESET} {compose_path}",
    ]
    if dockerfile_path:
        result_lines.append(f"{C.GREEN}✔{C.RESET} {dockerfile_path}")
        result_lines.append(f"{C.YELLOW}⚠ CMD line generated Dockerfile me check kar lena{C.RESET}")
    elif info["dockerfile_exists"]:
        result_lines.append(f"{C.DIM}ℹ Existing Dockerfile ko touch nahi kiya{C.RESET}")

    result_lines.append("")
    result_lines.append(f"{C.BOLD}Ab chalane ke liye:{C.RESET}")
    result_lines.append(f"  {C.CYAN}cd {out_dir}{C.RESET}")
    result_lines.append(f"  {C.CYAN}docker compose up --build{C.RESET}")

    box("Done!", result_lines, color=C.GREEN)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.RED}Cancelled.{C.RESET}")
        sys.exit(1)
