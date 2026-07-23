# Auto Docker Compose Generator

Kisi bhi project folder ko scan karke `docker-compose.yml` (aur zaroorat pade to `Dockerfile`) khud-ba-khud generate karta hai.

## Use kaise karein

```bash
python3 generate_compose.py /path/to/your/project
```

Options:
- `--app-name myapp` — service ka naam custom set karo (default: folder ka naam)
- `--port 8080` — detect hue port ko override karo
- `--out ./somewhere` — output files kahin aur likhne ke liye

Current directory ke liye:
```bash
python3 generate_compose.py .
```

## Ye kya detect karta hai

**Language/Framework:**
- Node.js (`package.json`) — Express, Next.js, React, Vite ka pata lagata hai
- Python — Django (`manage.py`), Flask, FastAPI, ya generic
- Go (`go.mod`)
- Static site (`index.html`)

**Extra services** (dependencies aur `.env` file dekh kar):
- PostgreSQL (`pg`, `psycopg2`, etc.)
- MySQL
- MongoDB
- Redis

Jo bhi mile, unke liye compose file me alag se service + volume add ho jata hai, `depends_on` ke saath.

## Important

- Agar project me pehle se `Dockerfile` hai, use touch nahi karta — sirf `docker-compose.yml` generate karta hai jo `build: .` use karega.
- Agar `Dockerfile` nahi hai, ek basic Dockerfile bhi bana deta hai — **CMD line ek baar zaroor check kar lena**, kyunki start command guess kiya gaya hai.
- DB passwords compose file me plain rakhe hain (`appuser` / `apppassword`) — production me `.env` file se replace karna.

## Interactive Terminal UI (recommended)

Ek colorful, step-by-step interactive UI bhi hai — koi extra library install nahi karni padegi, pure Python hai:

```bash
python3 ui.py
```

Ye tumse pucchega:
1. Project ka path
2. Scan karega (spinner ke saath) aur detected stack + services dikhayega ek box me
3. App ka naam aur port confirm/change karne ka option
4. Detect hui services (Postgres/MySQL/Mongo/Redis) me se konsi include/exclude karni hain
5. Output kahan likhna hai
6. Progress bar ke saath files generate karega aur final "Done!" panel dikhayega with next steps

`ui.py` aur `generate_compose.py` dono ek hi folder me hone chahiye (ye internally usi detection/generation logic ko use karta hai).
