# Changeface

Queue a face swap or a music track, poll the job, download the file.

`POST /api/swap` stores the source image, target video, and a job, then returns. One Celery worker runs inference, writes the output, and records the model and duration. The client polls `GET /api/jobs/{id}`.

| | |
| --- | --- |
| API | [http://localhost:8000](http://localhost:8000) |
| UI | [http://localhost:5173](http://localhost:5173) |
| Backend | `hyperswap` (needs CUDA). Missing CUDA fails the job and writes no video. |
| Jobs | Integer ids. Timestamps are timezone-aware. |
| Media | Jobs point at media ids. The same file can be reused. Thumbnails live in `storage/thumbnails/`. |

## Start

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

The local file mounts `app/`, `migrations/`, and `frontend/` and starts Vite. Open the UI. `/api` is proxied to the API. `uvicorn --reload` and `watchfiles` restart on save; a restart drops a job that is running. Edits under `facefusion/` are not watched:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml restart worker
```

The image in `docker-compose.yml` does not reload. Postgres in that file is for this machine. The worker reserves the GPU.

```bash
docker compose up --build          # API :8000, no live UI
cd frontend && npm install && npm run dev   # UI on the host, API already on :8000
```

`VITE_API_PROXY` overrides the API target. `npm run build` typechecks, then writes `frontend/dist`. `npm run preview` does not proxy `/api`.

## Stack

FastAPI and async SQLAlchemy, managed with [uv](https://docs.astral.sh/uv/). Celery, Redis, solo pool, concurrency 1. Postgres (SQLite in tests). Vue 3, Vue Router, Pinia, Vite. Alembic runs before the API and the worker start.

## API

Signed-in routes use the `session` cookie. `health`, `limits`, `register`, and `login` are public. `kind` is `images`, `videos`, or `outputs`. `q` searches filename, status, model, or id.

| | |
| --- | --- |
| `POST /api/swap` | Queue a face swap |
| `POST /api/v1/music` | Queue a track. Optional prompt, and optional `audio_id` of stored audio |
| `POST /api/v1/text` | Queue Llama text. Required `model`, `prompt`, and `max_new_tokens` |
| `GET /api/jobs` | Face swaps. `GET /api/jobs/{id}` detail, `.../download` the result |
| `GET /api/v1/music/jobs/{id}` | One music job |
| `GET /api/v1/text/jobs/{id}` | One text job |
| `GET /api/files/audios` | Audio media. `GET /api/files/audios/{id}/download` the file |
| `GET /api/files/{kind}` | List. `GET /api/files/{kind}/{id}` one file, `.../download` the original, `.../preview` the JPEG |
| `POST /api/register` `POST /api/login` | Set the cookie. `GET /api/me` `POST /api/logout` |
| `GET /api/health` `GET /api/limits` | Liveness, upload limits, backend |

## Limits

Source image 10 MB. Target video 100 MB, 30 seconds. One GPU job, held by a Redis lock.

## Music

Music is a module of this app (`app/services/music.py`, `app/inference/acestep.py`). It uses the same database, worker, and file layout as a face swap: `storage/_incoming/…`, then `storage/{job id}/`. The request takes a stored `audio_id`, not an upload. The output row is `storage/{job id}/output.flac`. The worker currently records the job and does not run the model.

## Text

Text is a module of this app (`app/services/text_jobs.py`). `POST /api/v1/text` stores a `TextJob` whose `parameters` JSON holds the Llama 3.1 8B Instruct or Llama 3.3 8B settings. `model`, `prompt`, and `max_new_tokens` are required. Sampling fields such as `temperature`, `top_p`, `top_k`, and `stop` are optional. The worker records the job and does not run the model.

## FaceFusion

[FaceFusion](https://github.com/facefusion/facefusion) 3.9.1, OpenRAIL-AS, Copyright (c) 2026 Henry Ruhs. Notice: `LICENSES/FaceFusion-OpenRAIL-AS.txt`. Only `app/inference` calls it.

`facefusion/` is its own checkout. Keep edits there and point this repo at that fork. Do not commit weights, its virtualenv, or sample media (`facefusion/.assets`, `facefusion/.venv`, `facefusion/.jobs`). Set `HYPERSWAP_WEIGHTS` before a real swap. The image is CUDA 13 and uses `onnxruntime-gpu[cuda,cudnn]==1.30.0`.

```bash
./scripts/run-facefusion.sh
```

## Tests

```bash
uv sync --group dev && uv run pytest
```

The canary stays skipped until `tests/canary/fixtures/` has `source.png` and `target.mp4`:

```bash
CHANGEFACE_CANARY=1 INFERENCE_BACKEND=hyperswap HYPERSWAP_WEIGHTS=/path/to/weights \
  uv run pytest -m canary
```
