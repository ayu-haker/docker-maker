#!/usr/bin/env python3
"""
generate_compose.py
--------------------
Scans a project folder, detects its tech stack (language/framework +
databases/services it depends on), and auto-generates:
  - docker-compose.yml
  - Dockerfile (only if one doesn't already exist)

Usage:
    python3 generate_compose.py /path/to/project
    python3 generate_compose.py            # scans current directory
    python3 generate_compose.py /path --app-name myapp --port 8080
"""

import argparse
import json
import os
import re
import sys

# --------------------------------------------------------------------------
# Detection helpers
# --------------------------------------------------------------------------

def read_file(path):
    try:
        with open(path, "r", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def find_files(root, names):
    """Return list of names that exist directly under root."""
    return [n for n in names if os.path.isfile(os.path.join(root, n))]


def detect_stack(root):
    """
    Returns a dict describing the detected stack:
    {
        "language": "node" | "python-django" | "python-flask" | "python-generic"
                    | "go" | "static" | "unknown",
        "port": int,
        "build_context": ".",
        "dockerfile_exists": bool,
        "services": set of extra services e.g. {"postgres", "redis"}
        "package_manager": "npm" | "pip" | None
    }
    """
    info = {
        "language": "unknown",
        "port": 3000,
        "build_context": ".",
        "dockerfile_exists": os.path.isfile(os.path.join(root, "Dockerfile")),
        "services": set(),
        "package_manager": None,
        "start_cmd": None,
    }

    files_here = os.listdir(root) if os.path.isdir(root) else []

    # ---------- Node.js ----------
    pkg_json_path = os.path.join(root, "package.json")
    if os.path.isfile(pkg_json_path):
        info["language"] = "node"
        info["package_manager"] = "npm"
        info["port"] = 3000
        try:
            pkg = json.loads(read_file(pkg_json_path) or "{}")
        except json.JSONDecodeError:
            pkg = {}
        deps = {}
        deps.update(pkg.get("dependencies", {}))
        deps.update(pkg.get("devDependencies", {}))

        if "next" in deps:
            info["port"] = 3000
            info["start_cmd"] = "npm run start"
        elif "express" in deps or "fastify" in deps or "koa" in deps:
            info["port"] = 3000
            info["start_cmd"] = "npm start"
        elif "react-scripts" in deps or "vite" in deps:
            info["port"] = 5173 if "vite" in deps else 3000
            info["start_cmd"] = "npm start"
        else:
            scripts = pkg.get("scripts", {})
            info["start_cmd"] = "npm start" if "start" in scripts else "node index.js"

        _detect_node_services(deps, info)

    # ---------- Python ----------
    elif find_files(root, ["requirements.txt", "Pipfile", "pyproject.toml"]) or \
            os.path.isfile(os.path.join(root, "manage.py")):
        info["package_manager"] = "pip"
        req_text = read_file(os.path.join(root, "requirements.txt"))
        req_text += read_file(os.path.join(root, "Pipfile"))
        req_text += read_file(os.path.join(root, "pyproject.toml"))
        req_lower = req_text.lower()

        if os.path.isfile(os.path.join(root, "manage.py")):
            info["language"] = "python-django"
            info["port"] = 8000
            info["start_cmd"] = "python manage.py runserver 0.0.0.0:8000"
        elif "flask" in req_lower:
            info["language"] = "python-flask"
            info["port"] = 5000
            info["start_cmd"] = "flask run --host=0.0.0.0"
        elif "fastapi" in req_lower:
            info["language"] = "python-fastapi"
            info["port"] = 8000
            info["start_cmd"] = "uvicorn main:app --host 0.0.0.0 --port 8000"
        else:
            info["language"] = "python-generic"
            info["port"] = 8000
            info["start_cmd"] = "python app.py"

        _detect_python_services(req_lower, info)

    # ---------- Go ----------
    elif os.path.isfile(os.path.join(root, "go.mod")):
        info["language"] = "go"
        info["port"] = 8080
        info["start_cmd"] = "go run ."

    # ---------- Static site ----------
    elif "index.html" in files_here:
        info["language"] = "static"
        info["port"] = 80

    # ---------- .env based service hints (works for any stack) ----------
    env_text = read_file(os.path.join(root, ".env")).lower()
    env_text += read_file(os.path.join(root, ".env.example")).lower()
    _detect_env_services(env_text, info)

    return info


def _detect_node_services(deps, info):
    if any(d in deps for d in ["pg", "sequelize", "typeorm", "prisma"]):
        info["services"].add("postgres")
    if any(d in deps for d in ["mysql", "mysql2"]):
        info["services"].add("mysql")
    if any(d in deps for d in ["mongoose", "mongodb"]):
        info["services"].add("mongo")
    if any(d in deps for d in ["redis", "ioredis"]):
        info["services"].add("redis")


def _detect_python_services(req_lower, info):
    if any(k in req_lower for k in ["psycopg2", "asyncpg", "django-postgres"]):
        info["services"].add("postgres")
    if any(k in req_lower for k in ["pymysql", "mysqlclient", "mysql-connector"]):
        info["services"].add("mysql")
    if any(k in req_lower for k in ["pymongo", "mongoengine", "motor"]):
        info["services"].add("mongo")
    if "redis" in req_lower:
        info["services"].add("redis")


def _detect_env_services(env_text, info):
    if re.search(r"postgres", env_text):
        info["services"].add("postgres")
    if re.search(r"mysql", env_text):
        info["services"].add("mysql")
    if re.search(r"mongo", env_text):
        info["services"].add("mongo")
    if re.search(r"redis", env_text):
        info["services"].add("redis")


# --------------------------------------------------------------------------
# Dockerfile generation (only used if project has none)
# --------------------------------------------------------------------------

DOCKERFILE_TEMPLATES = {
    "node": """FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE {port}
CMD [{start_cmd}]
""",
    "python-django": """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {port}
CMD [{start_cmd}]
""",
    "python-flask": """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV FLASK_APP=app.py
EXPOSE {port}
CMD [{start_cmd}]
""",
    "python-fastapi": """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {port}
CMD [{start_cmd}]
""",
    "python-generic": """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {port}
CMD [{start_cmd}]
""",
    "go": """FROM golang:1.22-alpine AS build
WORKDIR /app
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN go build -o server .

FROM alpine:latest
WORKDIR /app
COPY --from=build /app/server .
EXPOSE {port}
CMD ["./server"]
""",
    "static": """FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
""",
}


def cmd_to_json_array(cmd):
    if cmd is None:
        return '"echo", "no start command detected - edit CMD"'
    parts = cmd.split()
    return ", ".join(f'"{p}"' for p in parts)


def generate_dockerfile(info):
    template = DOCKERFILE_TEMPLATES.get(info["language"])
    if not template:
        template = DOCKERFILE_TEMPLATES["python-generic"]
    return template.format(
        port=info["port"],
        start_cmd=cmd_to_json_array(info["start_cmd"]),
    )


# --------------------------------------------------------------------------
# .dockerignore generation
# --------------------------------------------------------------------------

DOCKERIGNORE_COMMON = """.git
.gitignore
.env
.env.*
!.env.example
*.md
.vscode
.idea
docker-compose.yml
docker-compose.override.yml
Dockerfile
.dockerignore
"""

DOCKERIGNORE_EXTRA = {
    "node": "node_modules\nnpm-debug.log*\nyarn-error.log\ndist\nbuild\ncoverage\n",
    "python-django": "__pycache__/\n*.pyc\n*.pyo\nvenv/\n.venv/\n*.sqlite3\nstaticfiles/\n.pytest_cache/\n",
    "python-flask": "__pycache__/\n*.pyc\n*.pyo\nvenv/\n.venv/\n.pytest_cache/\n",
    "python-fastapi": "__pycache__/\n*.pyc\n*.pyo\nvenv/\n.venv/\n.pytest_cache/\n",
    "python-generic": "__pycache__/\n*.pyc\n*.pyo\nvenv/\n.venv/\n.pytest_cache/\n",
    "go": "bin/\n*.exe\nvendor/\n",
    "static": "node_modules\n",
}


def generate_dockerignore(info):
    extra = DOCKERIGNORE_EXTRA.get(info["language"], "")
    return DOCKERIGNORE_COMMON + extra


# --------------------------------------------------------------------------
# .env.example generation
# --------------------------------------------------------------------------

SERVICE_ENV_VARS = {
    "postgres": """# PostgreSQL
POSTGRES_USER=appuser
POSTGRES_PASSWORD=apppassword
POSTGRES_DB=appdb
DATABASE_URL=postgresql://appuser:apppassword@db:5432/appdb
""",
    "mysql": """# MySQL
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=appdb
MYSQL_USER=appuser
MYSQL_PASSWORD=apppassword
DATABASE_URL=mysql://appuser:apppassword@db:3306/appdb
""",
    "mongo": """# MongoDB
MONGO_INITDB_ROOT_USERNAME=appuser
MONGO_INITDB_ROOT_PASSWORD=apppassword
MONGO_URL=mongodb://appuser:apppassword@mongo:27017
""",
    "redis": """# Redis
REDIS_URL=redis://redis:6379
""",
}


def generate_env_example(info, app_name, port):
    lines = [f"# {app_name} — environment variables", f"PORT={port}", ""]
    for s in sorted(info["services"]):
        lines.append(SERVICE_ENV_VARS[s])
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# Backup helper — never silently clobber a file the user already has
# --------------------------------------------------------------------------

def backup_if_exists(path):
    """If `path` already exists, rename it to path.bak (or .bak2, .bak3...)."""
    if not os.path.isfile(path):
        return None
    backup_path = path + ".bak"
    n = 2
    while os.path.isfile(backup_path):
        backup_path = f"{path}.bak{n}"
        n += 1
    os.rename(path, backup_path)
    return backup_path


# --------------------------------------------------------------------------
# docker-compose.yml generation
# --------------------------------------------------------------------------

SERVICE_BLOCKS = {
    "postgres": """  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: apppassword
      POSTGRES_DB: appdb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d appdb"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks:
      - appnet
""",
    "mysql": """  db:
    image: mysql:8
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: appdb
      MYSQL_USER: appuser
      MYSQL_PASSWORD: apppassword
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "appuser", "-papppassword"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks:
      - appnet
""",
    "mongo": """  mongo:
    image: mongo:7
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: appuser
      MONGO_INITDB_ROOT_PASSWORD: apppassword
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks:
      - appnet
""",
    "redis": """  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks:
      - appnet
""",
}

VOLUME_NAMES = {
    "postgres": "postgres_data",
    "mysql": "mysql_data",
    "mongo": "mongo_data",
    "redis": "redis_data",
}

DEPENDS_ON_NAME = {
    "postgres": "db",
    "mysql": "db",
    "mongo": "mongo",
    "redis": "redis",
}


def generate_compose(info, app_name, port_override=None):
    port = port_override or info["port"]
    services = sorted(info["services"])

    lines = []
    lines.append("services:")
    lines.append(f"  {app_name}:")
    lines.append("    build: .")
    lines.append(f"    container_name: {app_name}")
    lines.append("    restart: unless-stopped")
    lines.append("    ports:")
    lines.append(f'      - "{port}:{port}"')

    if services:
        lines.append("    depends_on:")
        seen = set()
        for s in services:
            dep = DEPENDS_ON_NAME[s]
            if dep not in seen:
                lines.append(f"      {dep}:")
                lines.append("        condition: service_healthy")
                seen.add(dep)

    lines.append("    env_file:")
    lines.append("      - .env")
    lines.append("    volumes:")
    lines.append("      - .:/app")
    lines.append("    networks:")
    lines.append("      - appnet")
    lines.append("")

    for s in services:
        lines.append(SERVICE_BLOCKS[s])

    lines.append("networks:")
    lines.append("  appnet:")
    lines.append("    driver: bridge")

    if services:
        lines.append("")
        lines.append("volumes:")
        seen = set()
        for s in services:
            vol = VOLUME_NAMES[s]
            if vol not in seen:
                lines.append(f"  {vol}:")
                seen.add(vol)

    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Auto-generate docker-compose.yml for a project")
    parser.add_argument("path", nargs="?", default=".", help="Path to project folder (default: current directory)")
    parser.add_argument("--app-name", default=None, help="Service name for your app (default: folder name)")
    parser.add_argument("--port", type=int, default=None, help="Override the detected app port")
    parser.add_argument("--out", default=None, help="Output directory (default: same as project path)")
    parser.add_argument("--no-env", action="store_true", help="Skip generating .env.example")
    parser.add_argument("--no-dockerignore", action="store_true", help="Skip generating .dockerignore")
    parser.add_argument("--no-backup", action="store_true", help="Overwrite existing files instead of backing them up to .bak")
    args = parser.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"Error: '{root}' is not a valid directory.")
        sys.exit(1)

    out_dir = os.path.abspath(args.out) if args.out else root
    os.makedirs(out_dir, exist_ok=True)

    app_name = args.app_name or re.sub(r"[^a-z0-9_-]", "", os.path.basename(root).lower()) or "app"

    info = detect_stack(root)
    port = args.port or info["port"]

    print(f"Detected language/framework : {info['language']}")
    print(f"Detected app port            : {info['port']}")
    print(f"Detected extra services      : {', '.join(sorted(info['services'])) or 'none'}")
    print(f"Existing Dockerfile found    : {info['dockerfile_exists']}")
    print()

    def write_with_backup(path, content, label):
        if not args.no_backup:
            backup_path = backup_if_exists(path)
            if backup_path:
                print(f"  (existing {label} backed up to {os.path.basename(backup_path)})")
        with open(path, "w") as f:
            f.write(content)
        print(f"✔ Wrote {path}")

    compose_content = generate_compose(info, app_name, port)
    compose_path = os.path.join(out_dir, "docker-compose.yml")
    write_with_backup(compose_path, compose_content, "docker-compose.yml")

    if not info["dockerfile_exists"] and info["language"] != "unknown":
        dockerfile_content = generate_dockerfile(info)
        dockerfile_path = os.path.join(out_dir, "Dockerfile")
        write_with_backup(dockerfile_path, dockerfile_content, "Dockerfile")
        print("  ⚠ review the CMD line — the start command was guessed")
    elif info["language"] == "unknown":
        print("⚠ Could not confidently detect a stack — docker-compose.yml was still generated with a basic app service. Edit build/ports manually.")
    else:
        print("ℹ Existing Dockerfile detected — left untouched, compose file will use it via 'build: .'")

    if not args.no_dockerignore:
        dockerignore_path = os.path.join(out_dir, ".dockerignore")
        if not os.path.isfile(dockerignore_path):
            with open(dockerignore_path, "w") as f:
                f.write(generate_dockerignore(info))
            print(f"✔ Wrote {dockerignore_path}")
        else:
            print("ℹ .dockerignore already exists — left untouched")

    if not args.no_env:
        env_example_path = os.path.join(out_dir, ".env.example")
        write_with_backup(env_example_path, generate_env_example(info, app_name, port), ".env.example")
        if not os.path.isfile(os.path.join(out_dir, ".env")):
            print("  ⚠ Copy .env.example to .env and fill in real values before running")

    print(f"\nNext steps:\n  cd {out_dir}\n  docker compose up --build")


if __name__ == "__main__":
    main()
