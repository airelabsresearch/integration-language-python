#!/usr/bin/env bash
#
# release.sh — build (and optionally push) the LCOE container-function image to
# the Aire Labs registry.
#
# This is the single source of release heavy-lifting. It runs identically from
# a developer's machine and from the GitHub release workflow — the workflow
# just injects the registry password secret and the target environment as env
# vars; locally those same vars come from your shell (or interactive `docker
# login`). Invoke it via moon so the Python toolchain / `uv sync` are managed:
#
#   moon run lcoe:build      # build only          (RELEASE_PUSH=false)
#   moon run lcoe:release    # build + push         (RELEASE_PUSH=true)
#
# …or directly: `bash scripts/release.sh`. moon and the direct call are
# equivalent — moon only adds the toolchain + cached `uv sync` around it.
#
# ── Configuration (all via env vars) ─────────────────────────────────────────
#   RELEASE_ENV       stage | production         (default: stage)
#   RELEASE_PUSH      true | false               (default: false — build only)
#   RELEASE_VERSION   docker tag to use          (default: exact git tag on HEAD,
#                                                 else "branch-<branch>-<shortsha>",
#                                                 e.g. branch-main-1234567)
#   REGISTRY_HOST     override the registry host (default: derived from
#                                                 RELEASE_ENV — see below)
#   REGISTRY_USERNAME registry push username     (default: badger — the username
#                                                 the Aire Labs registry expects)
#   REGISTRY_PASSWORD registry password          (required only when pushing and
#                                                 not already `docker login`-ed)
#   IMAGE_REPO        repo path under the host    (default: lcoe-python)
#   PLATFORMS         buildx platforms            (default: linux/amd64)
#
# NOTE: the Aire Labs registry enforces IMMUTABLE tags — every tag may be pushed
# exactly once and never overwritten. So there is deliberately no `:latest` (it
# would be rejected on the second push); each build produces one unique tag (the
# git tag, or branch-<branch>-<shortsha> which is unique per commit).
#
set -euo pipefail

cd "$(dirname "$0")/.."

# ── Resolve environment → registry host ──────────────────────────────────────
RELEASE_ENV="${RELEASE_ENV:-stage}"
case "$RELEASE_ENV" in
  stage)      DEFAULT_HOST="badger-registry-stage.airelabs.studio" ;;
  production) DEFAULT_HOST="badger-registry.airelabs.studio" ;;
  *) echo "release.sh: RELEASE_ENV must be 'stage' or 'production', got '$RELEASE_ENV'" >&2; exit 2 ;;
esac

REGISTRY_HOST="${REGISTRY_HOST:-$DEFAULT_HOST}"
# The Aire Labs registry's push username. Override via REGISTRY_USERNAME if the
# registry rotates it; it is NOT a secret (the password is).
REGISTRY_USERNAME="${REGISTRY_USERNAME:-badger}"
IMAGE_REPO="${IMAGE_REPO:-lcoe-python}"
RELEASE_PUSH="${RELEASE_PUSH:-false}"
PLATFORMS="${PLATFORMS:-linux/amd64}"

# ── Resolve the docker tag ───────────────────────────────────────────────────
# Precedence, identical locally and in CI:
#   1. An explicit RELEASE_VERSION (the workflow sets this to the git tag on a
#      tag push, e.g. v2026-06-10-001 — the PREFERRED tag).
#   2. The exact git tag on HEAD, if any (so a local `git checkout v… && release`
#      reproduces the tagged image).
#   3. Otherwise "branch-<branch>-<shortsha>" (e.g. branch-main-1234567) — the
#      merge-to-main and ad-hoc case. The "branch-" prefix marks it as a
#      non-tag build and keeps it from ever colliding with a vDATE release tag.
if [[ -z "${RELEASE_VERSION:-}" ]]; then
  if RELEASE_VERSION="$(git describe --tags --exact-match 2>/dev/null)"; then
    : # exact tag on HEAD
  else
    BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'detached')"
    SHORT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    # Sanitize the branch for a docker tag: only [A-Za-z0-9._-] are legal, and a
    # tag can't start with a separator. Slashes (feature/x) → dashes.
    BRANCH="$(printf '%s' "$BRANCH" | tr '/' '-' | tr -cd 'A-Za-z0-9._-')"
    BRANCH="${BRANCH:-detached}"
    RELEASE_VERSION="branch-${BRANCH}-${SHORT_SHA}"
  fi
fi

IMAGE="${REGISTRY_HOST}/${IMAGE_REPO}"
TAGGED="${IMAGE}:${RELEASE_VERSION}"

echo "── LCOE release ─────────────────────────────────────────────"
echo "  environment : $RELEASE_ENV"
echo "  registry    : $REGISTRY_HOST"
echo "  image       : $TAGGED"
echo "  push        : $RELEASE_PUSH"
echo "  platforms   : $PLATFORMS"
echo "─────────────────────────────────────────────────────────────"

# ── Authenticate BEFORE building (fail fast) ──────────────────────────────────
# When pushing, sort out credentials up front so we don't build the whole image
# only to die at the push with docker's opaque "no basic auth credentials".
#   - REGISTRY_PASSWORD set        → non-interactive login (the CI path; locally
#                                    you can inline it, e.g. from a secrets
#                                    manager, WITHOUT committing anything).
#   - else, existing docker login  → use it.
#   - else                         → exit now with instructions.
if [[ "$RELEASE_PUSH" == "true" ]]; then
  DOCKER_CONFIG_FILE="${DOCKER_CONFIG:-$HOME/.docker}/config.json"
  if [[ -n "${REGISTRY_PASSWORD:-}" ]]; then
    echo "Logging in to $REGISTRY_HOST as $REGISTRY_USERNAME"
    echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY_HOST" -u "$REGISTRY_USERNAME" --password-stdin
  elif [[ -f "$DOCKER_CONFIG_FILE" ]] && grep -q "$REGISTRY_HOST" "$DOCKER_CONFIG_FILE"; then
    # Host appears in docker's config (auths entry or credential helper) — a
    # prior `docker login` is in effect.
    echo "Using existing 'docker login $REGISTRY_HOST' session."
  else
    cat >&2 <<EOF
release.sh: no credentials for $REGISTRY_HOST, and RELEASE_PUSH=true.

Authenticate in one of these ways (neither puts secrets in this repo):

  1. Log in once (credential lives in your Docker keychain):
       docker login $REGISTRY_HOST -u $REGISTRY_USERNAME

  2. Or supply the password inline from your own secrets manager, e.g.:
       REGISTRY_PASSWORD="\$(op read 'op://Shared/NonProduction/SIRO_REGISTRY_STAGE_PASSWORD')" \\
         moon run lcoe:release

Then re-run. (The image build is cached, so the retry is fast.)
EOF
    exit 1
  fi
fi

# ── Build ────────────────────────────────────────────────────────────────────
# Use buildx so the same command can build multi-arch and push in one shot when
# requested. `--load` (single-arch, into the local daemon) when not pushing so
# `docker run` / the build task can use the image locally.
#
# Exactly ONE tag: the Aire Labs registry enforces immutable tags, so there is
# no `:latest`. The tag is the git tag or branch-shortsha (unique per commit).
BUILD_ARGS=(buildx build --platform "$PLATFORMS" -t "$TAGGED")
if [[ "$RELEASE_PUSH" == "true" ]]; then
  BUILD_ARGS+=(--push)
else
  BUILD_ARGS+=(--load)
fi

echo "+ docker ${BUILD_ARGS[*]} ."
docker "${BUILD_ARGS[@]}" .

if [[ "$RELEASE_PUSH" == "true" ]]; then
  echo "✅ Pushed $TAGGED to $REGISTRY_HOST"
else
  echo "✅ Built $TAGGED locally (not pushed). Set RELEASE_PUSH=true to push."
fi
