#!/usr/bin/env bash
set -euo pipefail

# ===== モデル同期 =====
if [[ -n "${MODEL_S3_URI:-}" && -n "${MODEL_LOCAL_DIR:-}" ]]; then
  echo "[entrypoint] sync model from ${MODEL_S3_URI} -> ${MODEL_LOCAL_DIR}"
  mkdir -p "${MODEL_LOCAL_DIR}"
  aws --endpoint-url "${AWS_ENDPOINT_URL}" s3 sync "${MODEL_S3_URI}" "${MODEL_LOCAL_DIR}"
else
  echo "[entrypoint] MODEL_S3_URI or MODEL_LOCAL_DIR not set; skipping model sync"
fi

# ===== GitHub リポジトリ取得 =====
: "${GIT_REPO:?GIT_REPO is required}"
: "${GIT_BRANCH:=main}"

if [[ ! -d "/workspace/code/.git" ]]; then
  echo "[entrypoint] cloning ${GIT_REPO} (branch=${GIT_BRANCH})"
  rm -rf /workspace/code
  git clone --depth 1 --branch "${GIT_BRANCH}" "${GIT_REPO}" /workspace/code
else
  echo "[entrypoint] updating existing repo (branch=${GIT_BRANCH})"
  cd /workspace/code && git fetch --depth 1 origin "${GIT_BRANCH}" && git reset --hard "origin/${GIT_BRANCH}"
fi

# ===== 実行スクリプト決定 =====
: "${TARGET_SCRIPT:=run.py}"   # ← ここで切り替え可能（デフォルト run.py）

if [[ ! -f "/workspace/code/${TARGET_SCRIPT}" ]]; then
  echo "[entrypoint] ERROR: /workspace/code/${TARGET_SCRIPT} not found" >&2
  exit 1
fi

echo "[entrypoint] launch python: /workspace/code/${TARGET_SCRIPT}"
cd /workspace/code

# exec に "$@" をつけることで GUI から追加した引数を渡せる
exec python3 "${TARGET_SCRIPT}" "$@"
