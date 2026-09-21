# Educational Reel Agent

Google ADK agent + FastAPI service that turns a topic into a vertical educational reel.

**Storyboard → Sarvam voiceover render (1080×1920) → YouTube / Instagram / X / LinkedIn copy → optional YouTube upload.**

| | |
| --- | --- |
| Package | `agent` (`root_agent` = `educational_reel_creator`) |
| LLM | LiteLLM + Vercel AI Gateway |
| Agent model | `inclusionai/ling-3.0-flash-fin-free` (free) |
| Eval model | `typesafe-ai/jev` (free) |
| ADK | `google-adk` ≥ 2.9.2 |
| API | FastAPI on port **8080** — [OpenAPI at `/docs`](http://127.0.0.1:8080/docs) |
| Render | `python -m reelgen build` + `SARVAM_API_KEY` |
| Theme | Oracle Red `#E01C24` / Orange `#FF6600` on `#0D0D0D` |
| Handle | `@genai_guru` |
| Version | 1.2.0 |
| Python | 3.11+ |

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4?logo=google&logoColor=white)](https://google.github.io/adk-docs/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Sarvam TTS](https://img.shields.io/badge/TTS-Sarvam-E01C24)](https://www.sarvam.ai/)
[![CI](https://github.com/Yash-Kavaiya/educational-reel-agent/actions/workflows/ci-cd.yaml/badge.svg)](https://github.com/Yash-Kavaiya/educational-reel-agent/actions/workflows/ci-cd.yaml)

Repository: https://github.com/Yash-Kavaiya/educational-reel-agent

---

## Contents

1. [What it does](#what-it-does)
2. [Models (Vercel AI Gateway + LiteLLM)](#models-vercel-ai-gateway--litellm)
3. [Quick start](#quick-start)
3. [Run with Google ADK](#run-with-google-adk)
4. [HTTP API](#http-api)
5. [Storyboard JSON](#storyboard-json)
6. [Environment variables](#environment-variables)
7. [Voices and palette](#voices-and-palette)
8. [YouTube upload](#youtube-upload)
9. [Docker](#docker)
10. [Cloud Run](#cloud-run)
11. [Tests](#tests)
12. [Repository layout](#repository-layout)
13. [Security](#security)
14. [Troubleshooting](#troubleshooting)

---

## What it does

```
topic + content
      │
      ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│ Storyboard  │ ──► │ reelgen      │ ──► │ Social copy │ ──► │ YouTube  │
│ 5 scenes    │     │ 1080×1920    │     │ YT/IG/X/LI  │     │ optional │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────┘
         ADK tools  +  REST  /api/v1/*
```

| Capability | Detail |
| --- | --- |
| Storyboard | 5 scenes: title, concept, steps or diagram, comparison, outro. Saved as JSON under `STORYBOARDS_DIR/<series-slug>/` |
| Render | Calls `reelgen` with Sarvam TTS. HD `1080×1920` or preview `540×960` |
| Batch | One series title + a list of topics → storyboard + render each |
| Social copy | YouTube title/description/tags, Instagram caption, X text, LinkedIn post |
| Pipeline | One POST: storyboards → renders → copy → optional YouTube |
| YouTube | Resumable upload of an `.mp4` that already sits under `OUTPUT_DIR`. No browser OAuth on the server |
| ADK | Chat agent with the same tools as the REST API |
| Health | `GET /health` — no secrets in the body |

Storyboard and social-copy work **without** a Sarvam key. Render and pipeline-with-render return an error until `SARVAM_API_KEY` is set.

---

## Models (Vercel AI Gateway + LiteLLM)

The agent does **not** call Gemini directly. Google ADK 2.9+ uses [`LiteLlm`](https://google.github.io/adk-docs/agents/models/) and LiteLLM talks to [Vercel AI Gateway](https://vercel.com/docs/ai-gateway/ecosystem/framework-integrations/litellm).

| Role | Model id | LiteLLM string | Notes |
| --- | --- | --- | --- |
| Agent (chat + tools) | [`inclusionai/ling-3.0-flash-fin-free`](https://vercel.com/ai-gateway/models/ling-3.0-flash-fin-free) | `vercel_ai_gateway/inclusionai/ling-3.0-flash-fin-free` | Free. Function calling, 256K context |
| Evaluation | [`typesafe-ai/jev`](https://vercel.com/ai-gateway/models/jev) | `vercel_ai_gateway/typesafe-ai/jev` | Free. Structured yes/no / scores via `evaluate_with_jev` |

Jev is an evaluation model, not a tool-calling LLM. Ling creates storyboards and calls tools. Jev scores them.

Auth (either name):

```bash
# https://vercel.com/account/ai-gateway — create a key
export VERCEL_AI_GATEWAY_API_KEY=...   # LiteLLM official env
# or
export AI_GATEWAY_API_KEY=...
```

Python equivalent of the AI SDK `streamText({ model: 'inclusionai/ling-3.0-flash-fin-free' })` snippet:

```python
import litellm

response = litellm.completion(
    model="vercel_ai_gateway/inclusionai/ling-3.0-flash-fin-free",
    messages=[{"role": "user", "content": "Why is the sky blue?"}],
)
print(response.choices[0].message.content)
```

Override with `ADK_MODEL` / `JEV_MODEL` in `.env`.

---

## Quick start

Python 3.11+. No GPU for storyboards or copy.

### Linux / macOS

```bash
git clone https://github.com/Yash-Kavaiya/educational-reel-agent.git
cd educational-reel-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# edit .env and set SARVAM_API_KEY before you render
python -m pytest tests/ -q
python -m agent
```

### Windows (PowerShell)

```powershell
git clone https://github.com/Yash-Kavaiya/educational-reel-agent.git
cd educational-reel-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
python -m pytest tests/ -q
python -m agent
```

Open:

- API docs: http://127.0.0.1:8080/docs
- Health: http://127.0.0.1:8080/health
- Info: http://127.0.0.1:8080/api/v1/info

Runtime (ADK + YouTube client) install:

```bash
pip install -r requirements.txt
```

Optional Manim / ffmpeg Python extras (heavy; used by some render stacks):

```bash
pip install -r requirements-render.txt
```

Render also needs a working **`reelgen`** module on `REELGEN_PYTHON` (defaults to the current interpreter).

---

## Run with Google ADK

```bash
pip install -r requirements.txt
adk web
```

- App package: **`agent`**
- Agent name: **`educational_reel_creator`**
- Definition: `agent/agent.py`
- Instructions: `agent/prompts.py` (no `{placeholder}` identifiers — ADK would crash on those)

Tools registered on the agent:

| Tool | What it does |
| --- | --- |
| `create_storyboard` | Write a 5-scene JSON board |
| `render_reel` | `reelgen build` from a board path |
| `batch_render_reels` | Storyboard + render a list of topics |
| `generate_social_copy` | Platform captions |
| `upload_video_to_youtube` | Upload an mp4 under `OUTPUT_DIR` |
| `evaluate_with_jev` | TypeSafe Jev structured evaluation |

The agent is instructed not to invent file paths and not to claim a video exists if render failed.

---

## HTTP API

Base URL: `http://127.0.0.1:8080`

| Method | Path | Auth on Cloud Run | Notes |
| --- | --- | --- | --- |
| `GET` | `/` | yes | Service name, version, endpoint map |
| `GET` | `/health` | yes | Liveness. `sarvam_configured` is a boolean, not the key |
| `GET` | `/docs` | yes | Swagger UI |
| `GET` | `/redoc` | yes | ReDoc |
| `GET` | `/api/v1/info` | yes | Palette, voices, model, resolutions |
| `POST` | `/api/v1/storyboards` | yes | Create board |
| `GET` | `/api/v1/storyboards` | yes | List. Query `?series=` |
| `GET` | `/api/v1/storyboards/{series}/{file}` | yes | Path-safe read (`.json` only) |
| `POST` | `/api/v1/render` | yes | Render one board |
| `POST` | `/api/v1/batch-render` | yes | Series of topics |
| `POST` | `/api/v1/social-copy` | yes | Captions |
| `POST` | `/api/v1/evaluate` | yes | TypeSafe Jev via LiteLLM |
| `POST` | `/api/v1/pipeline` | yes | Full flow. `upload_youtube` requires `render=true` |
| `POST` | `/api/v1/youtube/upload` | yes | mp4 must be under `OUTPUT_DIR` |
| `GET` | `/api/v1/outputs` | yes | List mp4s. Query `?series=` |
| `GET` | `/api/v1/outputs/{series}/{file}` | yes | Download `.mp4` only |

Unknown voices are **422**. Path traversal on storyboard/output routes is **400/404**. Missing Sarvam key on render is **400**.

### Create a storyboard

```bash
curl -s http://127.0.0.1:8080/api/v1/storyboards \
  -H "Content-Type: application/json" \
  -d "{
    \"topic\": \"ReAct Pattern\",
    \"content\": \"ReAct interleaves reasoning and acting. Tools execute steps. Observations update the plan.\",
    \"voice\": \"arvind\",
    \"series_title\": \"Oracle AI Agents\",
    \"reel_number\": 1,
    \"total_reels\": 6
  }"
```

Example success:

```json
{
  "status": "success",
  "storyboard_path": "storyboards/oracle-ai-agents/01-react-pattern.json",
  "topic": "ReAct Pattern",
  "voice": "arvind",
  "reel_number": 1,
  "total_reels": 6,
  "scenes": 5,
  "estimated_duration": "50-75s"
}
```

### Render

```bash
curl -s http://127.0.0.1:8080/api/v1/render \
  -H "Content-Type: application/json" \
  -d "{
    \"storyboard_path\": \"storyboards/oracle-ai-agents/01-react-pattern.json\",
    \"output_filename\": \"oracle-ai-agents-01-react-pattern-hd.mp4\",
    \"preview\": false
  }"
```

`output_filename` must be a `.mp4` basename (no directories). Preview `true` adds `--preview` (540×960).

### Social copy

```bash
curl -s http://127.0.0.1:8080/api/v1/social-copy \
  -H "Content-Type: application/json" \
  -d "{
    \"topic\": \"ReAct Pattern\",
    \"reel_number\": 1,
    \"total_reels\": 6,
    \"series_title\": \"Oracle AI Agents\",
    \"voice\": \"arvind\",
    \"duration\": \"60s\"
  }"
```

Returns `social_copy.youtube|instagram|twitter|linkedin`.

### Pipeline

```bash
curl -s http://127.0.0.1:8080/api/v1/pipeline \
  -H "Content-Type: application/json" \
  -d "{
    \"series_title\": \"Oracle AI Agents\",
    \"topics\": [
      {\"topic\": \"ReAct Pattern\", \"content\": \"Reason then act. Tools return observations.\", \"voice\": \"arvind\"},
      {\"topic\": \"Guardrails\", \"content\": \"Policy checks sit around the agent loop.\", \"voice\": \"kabir\"}
    ],
    \"render\": true,
    \"generate_social\": true,
    \"upload_youtube\": false,
    \"preview\": true
  }"
```

`upload_youtube: true` with `render: false` is **400**.

---

## Storyboard JSON

Written to `STORYBOARDS_DIR/<slug(series)>/<NN>-<slug(topic)>.json`.

```json
{
  "title": "Oracle AI Agents: ReAct Pattern",
  "handle": "@genai_guru",
  "theme": "oracle",
  "voice": "arvind",
  "tts_provider": "sarvam",
  "scenes": [
    {
      "id": 1,
      "layout": "title",
      "narration": "Welcome to Oracle AI Agents. Today we cover ReAct Pattern. This is reel 1 of 6.",
      "visual": {
        "title": "ReAct Pattern",
        "subtitle": "Oracle AI Agents • Part 1 of 6"
      }
    },
    { "id": 2, "layout": "concept", "narration": "...", "visual": {} },
    { "id": 3, "layout": "steps", "narration": "...", "visual": {} },
    { "id": 4, "layout": "comparison", "narration": "...", "visual": {} },
    { "id": 5, "layout": "outro", "narration": "...", "visual": {} }
  ]
}
```

Scene 3 is `steps` when the content has enough bullet/sentence points; otherwise it is a `diagram` (input → process → output + feedback).

---

## Environment variables

Copy `.env.example` to `.env`. Loaded by `pydantic-settings` in `agent/config.py`.

| Variable | Default | Required | Purpose |
| --- | --- | --- | --- |
| `SARVAM_API_KEY` | empty | for render | Sarvam TTS. Never commit this |
| `VERCEL_AI_GATEWAY_API_KEY` | empty | for ADK chat + Jev | LiteLLM official key name |
| `AI_GATEWAY_API_KEY` | empty | for ADK chat + Jev | Alias if Vercel key unset |
| `GOOGLE_CLOUD_PROJECT` | empty | Cloud Run | GCP project id |
| `GOOGLE_CLOUD_REGION` | `us-central1` | no | Region |
| `ADK_MODEL` | `inclusionai/ling-3.0-flash-fin-free` | no | Agent LLM (LiteLLM / Vercel) |
| `JEV_MODEL` | `typesafe-ai/jev` | no | Evaluation model |
| `ADK_APP_NAME` | `educational-reel-agent` | no | ADK runner app name |
| `PORT` | `8080` | no | Listen port (Cloud Run sets this) |
| `HOST` | `0.0.0.0` | no | Bind address |
| `LOG_LEVEL` | `INFO` | no | uvicorn / app logs |
| `CORS_ORIGINS` | `*` | no | Comma-separated. `*` disables credentialed CORS |
| `OUTPUT_DIR` | `./output` | no | Rendered mp4s |
| `STORYBOARDS_DIR` | `./storyboards` | no | JSON boards |
| `LOGS_DIR` | `./logs` | no | Log directory |
| `REELGEN_PYTHON` | current interpreter | no | Executable for `python -m reelgen` |
| `REELGEN_MODULE` | `reelgen` | no | Module name |
| `RENDER_TIMEOUT_SECONDS` | `600` | no | Per-reel subprocess cap |
| `YOUTUBE_CREDENTIALS_FILE` | `~/.youtube_credentials.json` | for upload | OAuth client secrets |
| `YOUTUBE_TOKEN_FILE` | `~/.youtube_token.json` | for upload | Pre-authorized user token |
| `DEFAULT_SERIES_TITLE` | `Oracle AI Agents` | no | Series slug / titles |
| `DEFAULT_HANDLE` | `@genai_guru` | no | Outro and captions |
| `DEFAULT_THEME` | `oracle` | no | Storyboard theme field |
| `DEFAULT_VOICE` | `anushka` | no | Fallback voice name in settings |

---

## Voices and palette

| Voice | Use |
| --- | --- |
| `anushka` | General tech, announcements |
| `arvind` | Technical tutorials, deep dives |
| `meera` | Educational, warm |
| `kabir` | Serious / architecture |
| `diya` | Energetic social |
| `arya` | Neutral / international |
| `pavithra` | Tamil/English |

Unknown names are rejected (tool `status=error`, HTTP 422).

| Token | Hex |
| --- | --- |
| Background | `#0D0D0D` |
| Background accent | `#1A0A0A` |
| Text | `#F5F0F0` |
| Muted | `#A08080` |
| Accent (Oracle Red) | `#E01C24` |
| Accent 2 (Oracle Orange) | `#FF6600` |
| Highlight | `#FF9900` |

---

## YouTube upload

Cloud Run **cannot** open a browser. Do OAuth once on a laptop, then mount the token.

1. Create an OAuth client (Desktop) in Google Cloud Console with YouTube Data API v3.
2. Save client secrets as `YOUTUBE_CREDENTIALS_FILE`.
3. Produce an authorized user token JSON (`YOUTUBE_TOKEN_FILE`) locally.
4. On Cloud Run, mount those files from Secret Manager (`/secrets/youtube_credentials.json`, `/secrets/youtube_token.json`).

Upload body:

```json
{
  "video_path": "oracle-ai-agents-01-react-pattern-hd.mp4",
  "title": "ReAct Pattern | Oracle AI Agents Part 1/6",
  "description": "...",
  "tags": ["AI Agents", "ReAct"],
  "privacy_status": "unlisted",
  "category_id": "28"
}
```

`privacy_status`: `private` | `unlisted` | `public`. Only `.mp4` files under `OUTPUT_DIR` are accepted.

---

## Docker

```bash
docker build -t educational-reel-agent .
docker build --build-arg INSTALL_RENDER=false -t educational-reel-agent:api .
docker run --rm -p 8080:8080 --env-file .env educational-reel-agent
```

- Multi-stage image, non-root `appuser`
- `HEALTHCHECK` hits `http://127.0.0.1:$PORT/health`
- Entrypoint: `uvicorn agent.main:app --workers 1`
- `INSTALL_RENDER=true` (default) also installs `requirements-render.txt`

---

## Cloud Run

```bash
./scripts/deploy.sh staging YOUR_PROJECT_ID us-central1
./scripts/deploy.sh production YOUR_PROJECT_ID us-central1
```

The script enables APIs, Artifact Registry, the service account, and deploys with:

- `--no-allow-unauthenticated` — grant `roles/run.invoker` to callers
- `--set-secrets=SARVAM_API_KEY=sarvam-api-key:latest`
- 2Gi RAM, 2 CPU, timeout 3600s, concurrency 8
- Staging service name: `educational-reel-agent-staging` (min instances 0)
- Production: `educational-reel-agent` (min instances 1)

Also: `cloudbuild.yaml` (test → build → push → deploy → authenticated health check).

GitHub Actions (`.github/workflows/ci-cd.yaml`): pytest on push/PR; Docker build (no push) on push to `main`/`develop`.

Call a private service:

```bash
TOKEN=$(gcloud auth print-identity-token)
curl -s -H "Authorization: Bearer $TOKEN" "$URL/health"
```

---

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

| File | Covers |
| --- | --- |
| `tests/test_paths.py` | slugify, traversal rejection |
| `tests/test_storyboard.py` | JSON write, voices, missing API key |
| `tests/test_api.py` | health, round-trip, 422 voice, pipeline guard |
| `tests/test_prompts.py` | no ADK `{identifier}` placeholders, no hardcoded keys |
| `tests/test_render_parse.py` | reelgen stdout metadata |

No network and no `reelgen` process in CI.

---

## Repository layout

```
educational-reel-agent/
├── agent/
│   ├── __init__.py          # lazy export of root_agent
│   ├── __main__.py          # python -m agent
│   ├── agent.py             # ADK Agent
│   ├── main.py              # FastAPI app
│   ├── config.py            # pydantic-settings
│   ├── models.py            # requests, Storyboard, voices, palette
│   ├── paths.py             # slugify + safe_under
│   ├── prompts.py           # ADK instruction text
│   └── tools/
│       ├── reel_tools.py    # storyboard, render, batch, social copy
│       └── youtube_tools.py # upload (token file only)
├── tests/
├── scripts/deploy.sh
├── Dockerfile
├── entrypoint.sh
├── healthcheck.py
├── cloudbuild.yaml
├── .github/workflows/ci-cd.yaml
├── .env.example
├── requirements.txt         # API + google-adk + YouTube client
├── requirements-dev.txt     # pytest stack (no ADK required)
└── requirements-render.txt  # manim / pydub extras
```

---

## Security

- No API keys in source. `SARVAM_API_KEY` is environment / Secret Manager only.
- Storyboard and output routes resolve paths under configured roots; `..` is rejected.
- Downloads only serve `.mp4`. Uploads only accept `.mp4` under `OUTPUT_DIR`.
- Cloud Run is private by default.
- YouTube uses a pre-authorized token; `InstalledAppFlow.run_local_server` is not used.
- Rotate any Sarvam key that was ever committed to git history.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `SARVAM_API_KEY is not set` | Put the key in `.env` or Secret Manager |
| `VERCEL_AI_GATEWAY_API_KEY is not set` | Create a key at vercel.com/account/ai-gateway |
| `unknown voice` / HTTP 422 | Use a name from the voice table |
| `Storyboard not found` | Path must be under `STORYBOARDS_DIR` |
| `reelgen executable not found` | Install reelgen or set `REELGEN_PYTHON` |
| Render timeout | Raise `RENDER_TIMEOUT_SECONDS` (default 600) |
| YouTube: token missing/expired | Refresh the token locally; do not expect a browser on Cloud Run |
| ADK `Context variable not found` | Do not put `{identifier}` in `agent/prompts.py` |
| `adk web` import error | `pip install -r requirements.txt` and run from repo root |
| Healthcheck fails in Docker | App must listen on `PORT` (default 8080); probe is HTTP GET `/health` |

---

## License

No `LICENSE` file in this repository yet. All rights reserved unless the owner adds one.
