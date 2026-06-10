# Aire Labs Container Function — Python Example

Computes LCOE (Levelized Cost of Energy) from bundled solar and wind cost data. A working example you can build and run locally with Docker. It is the Python counterpart to the [R example](https://github.com/airelabsresearch/integration-language-r) and produces identical results.

**Full guide:** [Container Functions with Python](https://www.airelabs.com/docs/docker-programming-language-python)

## Quick start

Requires [Docker](https://orbstack.dev/download) (or [Docker Desktop](https://docs.docker.com/desktop/)). Commands below assume macOS or Linux.

```bash
docker build -t lcoe-python .

mkdir -p /tmp/airelabs
cp fixtures/hook-input.json /tmp/airelabs/hook-input.json

docker run --rm \
  -v /tmp/airelabs:/airelabs \
  -e AIRELABS_HOOK_INPUT_PATH=/airelabs/hook-input.json \
  -e AIRELABS_HOOK_OUTPUT_PATH=/airelabs/hook-output.json \
  lcoe-python
```

You should see: `OK — dataset=solar, year=2027, lcoe=43.39 USD/MWh`

Inspect the output: `cat /tmp/airelabs/hook-output.json`

## Run tests

```bash
docker run --rm lcoe-python pytest tests/test_model.py
docker run --rm lcoe-python pytest tests/test_main.py
```

## Try other inputs

```bash
cp fixtures/hook-input-wind.json /tmp/airelabs/hook-input.json            # wind instead of solar
cp fixtures/hook-input-bad-rate.json /tmp/airelabs/hook-input.json        # invalid discount rate (error result)
cp fixtures/hook-input-unknown-dataset.json /tmp/airelabs/hook-input.json # unknown dataset (hard error)
```

## Local development

The toolchain is managed by [proto](https://moonrepo.dev/proto) + [moon](https://moonrepo.dev/moon), with [uv](https://docs.astral.sh/uv/) as the Python package manager. **This repo is a self-contained moon workspace** — clone it on its own and everything works; it is only vendored into the siro monorepo as a git submodule for visibility. The runtime has **no third-party dependencies** (the Hook I/O helpers use only the Python standard library); `pytest` and `ruff` are dev-only tools.

```bash
proto install            # installs moon + python + uv pinned in .prototools
moon run lcoe:test       # moon runs `uv sync` for you (cached), then pytest
moon run lcoe:lint       # ruff check
moon run lcoe:format     # ruff format --check (CI gate)
moon run lcoe:format-fix # apply formatting + lint autofixes in place
moon run lcoe:build      # build the Docker image locally (test + lint first)
```

`moon run` provisions the toolchain and does the `uv sync` itself (hash-cached), so there's no separate install step. If you'd rather drive `uv` directly:

```bash
uv sync                  # creates .venv with the dev tools
uv run pytest            # run the full test suite

# Run the function directly against a fixture:
AIRELABS_HOOK_INPUT_PATH=fixtures/hook-input.json \
AIRELABS_HOOK_OUTPUT_PATH=/tmp/hook-output.json \
  uv run python main.py
```

## Releasing

Images are pushed to the Aire Labs registry, which is **per-org** and **immutable-tagged** — every image gets one unique tag (no `:latest`). The host is `org-<ORG_ID>.<registry-domain>`, derived from your org id.

All the heavy lifting lives in [`scripts/release.sh`](scripts/release.sh), invoked the same way locally and in CI. The login username is `api-key`; the password is your **registry API key**. Pass your org id via `REGISTRY_ORG_ID` (nothing org-specific is committed) and the API key via `REGISTRY_PASSWORD` — **credentials are never committed**:

```bash
# (a) Log in once — the credential lives in your Docker keychain:
docker login org-<ORG_ID>.<registry-domain> --username api-key --password <YOUR_API_KEY>
REGISTRY_ORG_ID=<ORG_ID> moon run lcoe:release

# (b) Or pass the API key inline at run time — it stays in your shell, not the repo:
REGISTRY_ORG_ID=<ORG_ID> REGISTRY_PASSWORD=<YOUR_API_KEY> moon run lcoe:release
```

If you run `lcoe:release` without an org id or credential, the script fails fast **before** building and prints these instructions.

CI does this automatically ([`.github/workflows/release.yaml`](.github/workflows/release.yaml)):
- **push to `main`** (or manual dispatch) → image tagged `branch-<branch>-<shortsha>`
- **push of a `v*` git tag** (e.g. `v2026-06-10-001`) → image tagged with the git tag, plus a matching GitHub Release

It needs, under **Settings → Secrets and variables → Actions**:
- a repo **variable** `REGISTRY_ORG_ID` (your org id — not sensitive), and
- a repo **secret** `REGISTRY_API_KEY` (the registry API key).

## Layout

| Path | Purpose |
|---|---|
| `main.py` | Entry point — reads HookInput, computes LCOE, writes HookOutput. |
| `lcoe/airelabs.py` | Aire Labs Hook I/O helpers (stdlib-only — copy this into your own project). |
| `lcoe/model.py` | Pure LCOE business logic (CRF + LCOE formula), no I/O. |
| `lcoe/data_lookup.py` | Loads cost assumptions from the bundled `data/*.csv`. |
| `data/` | Year-by-year cost projections per technology, built into the image. |
| `fixtures/` | Example HookInput payloads. |
| `tests/` | `pytest` unit + integration tests. |
| `Dockerfile` | uv-based image; runs `python main.py`. |
| `scripts/release.sh` | Build + (optionally) push the image — one entry point for local and CI. |
| `moon.yml`, `.moon/` | moon project + toolchain (python/uv) config; the `lcoe:*` tasks. |
| `.prototools` | Pinned moon / python / uv versions (`proto install`). |
| `.github/workflows/` | `ci` (lint + test) and `release` (build + push the image). |

See the [full guide](https://www.airelabs.com/docs/docker-programming-language-python) for a walkthrough of the code and how to write your own function.
