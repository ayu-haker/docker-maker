# Auto Docker Compose Generator

Kisi bhi project folder ko scan karke `docker-compose.yml`, `Dockerfile`, `.env.example`, aur `.dockerignore` khud-ba-khud generate karta hai — production-ready settings ke saath (health checks, custom network, service dependencies).

## Example Run (Terminal UI)

Real run — WSL terminal pe ek Node.js project (`compilor`) scan karke:

```bash
python3 ui.py
```

![Terminal UI — scan, detection, config, preview](screenshots/terminal-ui-1.png)

Detection ke baad app name/port set kiya (`compiler-app`, port `3000`), `.env.example` aur `.dockerignore` dono ke liye `y`, phir preview dekh ke files likhne ki confirmation di:

![Terminal UI — generate, done, next steps](screenshots/terminal-ui-2.png)

Generate hone ke baad exact ye output milta hai:

```
Generating docker-compose.yml [████████████████████████████████] 100%
Generating Dockerfile          [████████████████████████████████] 100%
Generating .dockerignore       [████████████████████████████████] 100%
Generating .env.example        [████████████████████████████████] 100%

┌─ Done! ────────────────────────────────────────────────────────┐
│ ✔ .../compilor/docker-compose.yml
│ ✔ .../compilor/Dockerfile
│ ⚠ CMD line generated Dockerfile me check kar lena
│ ✔ .../compilor/.dockerignore
│ ✔ .../compilor/.env.example
│ ⚠ .env.example ko .env me copy karke real values bharo
│
│ Ab chalane ke liye:
│   cd .../compilor
│   cp .env.example .env
│   docker compose up --build
└───────────────────────────────────────────────────────────────┘
```

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

## Streamlit Web UI (modern dashboard)

Ek Streamlit web app bhi hai — clean, modern SaaS-style dashboard design (dark theme, gradient accents, card layout, sidebar stepper, live tabs preview) jo browser me chalta hai.

### Install & run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Browser me `http://localhost:8501` khul jayega.

### Design
- Sidebar me step-by-step progress tracker (1→4)
- Detection result stat-cards me (Stack / Port / Dockerfile / Services count)
- Detected services colored pill-badges ke roop me
- Configure section me checkboxes + live tabs preview (docker-compose.yml, .env.example, .dockerignore, Dockerfile — sab alag tabs me)
- Gradient buttons, rounded cards, Inter font for UI + JetBrains Mono for code

### Do modes
1. **Local folder path** — agar Streamlit usi machine pe chal raha hai jahan project hai, seedha path type karo.
2. **Zip upload** — agar Streamlit kahin aur (server/cloud) chal raha hai, apne project ka `.zip` bana ke upload karo.

### Flow
1. Path/zip do → **Scan**
2. Detection result stat-cards + service badges dikhenge
3. App name/port set karo, services check/uncheck karo, Dockerfile/.env/.dockerignore toggle karo
4. Tabs me live preview — `docker-compose.yml`, `.env.example`, `.dockerignore`, `Dockerfile`
5. **Generate files** → **Download .zip**

Zip ko apne project folder me extract karke `.env.example` ko `.env` bana lo aur `docker compose up --build` chala do.

`app.py` bhi `generate_compose.py` pe hi depend karta hai (same folder me hona chahiye) — teeno interface (CLI, terminal UI, Streamlit) ek hi detection/generation logic use karte hain, to result hamesha consistent rahega.

