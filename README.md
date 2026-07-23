# Auto Docker Compose Generator

Kisi bhi project folder ko scan karke `docker-compose.yml`, `Dockerfile`, `.env.example`, aur `.dockerignore` khud-ba-khud generate karta hai — production-ready settings ke saath (health checks, custom network, service dependencies).

## Do tarike se use kar sakte ho

### 1. Interactive Terminal UI (recommended)
Colorful, step-by-step, koi extra install nahi chahiye:
```bash
python3 ui.py
```
Flow: path do → scan animation → detected stack ek box me dikhega → app name/port confirm karo → services include/exclude karo → **preview dekho pura compose file** → confirm karne ke baad hi likhta hai → progress bars ke saath files generate hoti hain → final summary panel with next steps.

### 2. Plain CLI (scripting/automation ke liye)
```bash
python3 generate_compose.py /path/to/your/project
```
Options:
- `--app-name myapp` — service ka naam custom set karo
- `--port 8080` — detect hue port ko override karo
- `--out ./somewhere` — output kahin aur likhne ke liye
- `--no-env` — `.env.example` skip karo
- `--no-dockerignore` — `.dockerignore` skip karo
- `--no-backup` — existing files ko `.bak` me backup kiye bina overwrite karo

## Ye kya detect karta hai

**Language/Framework:**
- Node.js (`package.json`) — Express, Next.js, React, Vite
- Python — Django (`manage.py`), Flask, FastAPI, ya generic
- Go (`go.mod`)
- Static site (`index.html`)

**Extra services** (dependencies aur `.env` file dekh kar):
- PostgreSQL, MySQL, MongoDB, Redis

## Kya-kya generate hota hai

| File | Kab banta hai |
|---|---|
| `docker-compose.yml` | Hamesha |
| `Dockerfile` | Sirf tab jab project me pehle se koi na ho |
| `.dockerignore` | Agar already exist nahi karta |
| `.env.example` | Har baar (backup ke saath agar pehle se hai) |

**Production-grade touches jo automatically add hote hain:**
- Har DB/service (Postgres/MySQL/Mongo/Redis) me proper **healthcheck** hai
- App service un healthchecks pe `depends_on: condition: service_healthy` se wait karta hai — matlab app tabhi start hoga jab DB actually ready ho
- Sab services ek custom `appnet` bridge network pe hain (isolated, best practice)
- Named volumes taaki DB data container restart pe delete na ho
- `.env.example` me har service ke connection strings (`DATABASE_URL`, `REDIS_URL`, etc.) pehle se likhe hote hain

## Safety

- **Kabhi bhi existing file ko silently overwrite nahi karta** — agar `docker-compose.yml` ya `.env.example` pehle se hai, use `.bak` (ya `.bak2`, `.bak3`...) me rename karke naya likhta hai.
- Existing `Dockerfile` aur `.dockerignore` ko kabhi touch nahi karta agar wo already present hain.
- Terminal UI me file likhne se pehle **pura preview dikhata hai** — confirm karne ke baad hi disk pe likhta hai.

## Important

- Generated `Dockerfile` ki `CMD` line kabhi-kabhi guess hoti hai (agar start script clear na ho) — ek baar zaroor check kar lena.
- DB passwords `.env.example` me placeholder hain (`appuser` / `apppassword`) — `.env` me copy karke real/strong values daalna, aur `.env` ko git me commit mat karna (usse `.dockerignore` aur `.gitignore` dono me exclude rakhna).

## Chalane ke baad

```bash
cp .env.example .env      # values fill karo
docker compose up --build
```
