# uv's official image: a slim Python 3.12 base with the `uv` binary baked in.
# This is the same `uv` pinned in .prototools, so the container and a
# developer's `proto install` shell resolve the same toolchain.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Faster, more reproducible installs inside the image.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (cached layer) using only the manifest + lockfile,
# so editing source code doesn't bust the dependency cache. The dev group is
# included so `docker run ... pytest` works, mirroring the R example which runs
# its tests inside the container.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --locked --no-install-project

# Now copy the project and install it into the venv.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Put the project venv on PATH so `python`/`pytest` resolve to it directly.
ENV PATH="/app/.venv/bin:$PATH"

# CMD (not ENTRYPOINT) so you can override with e.g.:
#   docker run lcoe-python pytest tests/test_model.py
CMD ["python", "main.py"]
