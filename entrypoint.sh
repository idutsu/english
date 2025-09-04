#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${MODEL_S3_URI:-}" && -n "${MODEL_LOCAL_DIR:-}" ]]; then
  echo "[entrypoint] sync model from ${MODEL_S3_URI} -> ${MODEL_LOCAL_DIR}"
  mkdir -p "${MODEL_LOCAL_DIR}"
  aws --endpoint-url "${AWS_ENDPOINT_URL}" s3 sync "${MODEL_S3_URI}" "${MODEL_LOCAL_DIR}"
else
  echo "[entrypoint] MODEL_S3_URI or MODEL_LOCAL_DIR not set; skipping model sync"
fi

: "${GIT_REPO:?GIT_REPO is required}"
: "${GIT_BRANCH:=main}"
: "${RUN_PY_PATH:=run.py}"

echo "[entrypoint] cloning ${GIT_REPO} (branch=${GIT_BRANCH})"
rm -rf /workspace/code
git clone --depth 1 --branch "${GIT_BRANCH}" "${GIT_REPO}" /workspace/code

if [[ ! -f "/workspace/code/${RUN_PY_PATH}" ]]; then
  echo "[entrypoint] ERROR: /workspace/code/${RUN_PY_PATH} not found" >&2
  exit 1
fi

cp "/workspace/code/${RUN_PY_PATH}" /workspace/run.py

echo "[entrypoint] launch python: /workspace/run.py"
exec python3 /workspace/run.py

