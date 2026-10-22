# The converter on Linux, with its tests and quality harness. README.md shows
# how to run it, and .github/workflows/ci.yml runs the checks in it.
#
# Nothing is fetched while converting: dependencies and the OCR models are
# downloaded here, at build time.

ARG PYTHON_IMAGE=python:3.13.16-slim-trixie@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

# A Windows working copy can hold CRLF line endings that git never commits.
# Git itself rewrites the files as .gitattributes says, binary files untouched.
# The files are deleted first: checkout-index skips any that look up to date.
FROM ${PYTHON_IMAGE} AS source
RUN apt-get update \
 && apt-get install --yes --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
RUN git init --quiet \
 && git add --all \
 && git ls-files -z | xargs -0 rm \
 && git checkout-index --all \
 && rm -rf .git

FROM ${PYTHON_IMAGE} AS build
COPY --from=ghcr.io/astral-sh/uv:0.9.13@sha256:f07d1bf7b1fb4b983eed2b31320e25a2a76625bdf83d5ff0208fe105d4d8d2f5 /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app
# Dependencies first, so a code change does not reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project
COPY --from=source /src .
RUN uv sync --frozen
# The models, fetched and checked against their pinned hashes.
RUN PDF_TO_DOC_MODELS=/opt/pdf-to-doc/models .venv/bin/pdf-to-doc-models

FROM ${PYTHON_IMAGE}
# OpenCV, which PaddleOCR uses, needs these system libraries, and Paddle needs OpenMP.
RUN apt-get update \
 && apt-get install --yes --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
 && rm -rf /var/lib/apt/lists/*
# Source files are untrusted input, so conversion runs as an ordinary user who
# cannot change the installed code. The web service's launcher listens in
# /run/pdf-to-doc, on a volume it shares with the web app; a new volume takes
# the folder's owner.
RUN useradd --uid 1000 --create-home converter \
 && install -d -o converter -g converter /run/pdf-to-doc
COPY --from=build /app /app
COPY --from=build /opt/pdf-to-doc/models /opt/pdf-to-doc/models
# PyThaiNLP would otherwise create a data folder in the home directory on
# import, and download any corpus it lacks on first use. PaddleX keeps its
# working files in /tmp. /app is read-only for the converter user, so pytest
# keeps no cache and mypy caches in /tmp.
ENV PATH=/app/.venv/bin:$PATH \
    PDF_TO_DOC_MODELS=/opt/pdf-to-doc/models \
    PYTHAINLP_READ_ONLY=1 \
    PYTHAINLP_OFFLINE=1 \
    PADDLE_PDX_CACHE_HOME=/tmp/paddlex \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTEST_ADDOPTS="-p no:cacheprovider" \
    MYPY_CACHE_DIR=/tmp/mypy-cache
WORKDIR /app
USER converter
# The commit the image is built from. Every page of the web service links to
# the source code at it (AGPL), and the public service refuses to start
# without it. The deploy passes it, as
# `--build-arg BUILD_COMMIT=$(git rev-parse HEAD)`. It comes last, so that a
# new commit rebuilds no layer above.
ARG BUILD_COMMIT=""
ENV PDF_TO_DOC_BUILD_COMMIT=${BUILD_COMMIT}
CMD ["pdf-to-doc", "--help"]
