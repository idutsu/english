FROM docker.io/nvidia/cuda:12.1.1-runtime-ubuntu22.04

# ---- 基本セットアップ ----
ENV DEBIAN_FRONTEND=noninteractive TZ=Asia/Tokyo PIP_NO_CACHE_DIR=1
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata python3 python3-pip git curl awscli ca-certificates && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*

# ---- Pythonライブラリ（共通） ----
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir transformers accelerate sentencepiece

WORKDIR /workspace

# ---- entrypoint.sh をコピー ----
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ---- デフォルト環境変数 ----
ENV GIT_REPO="https://github.com/idutsu/english.git" \
    GIT_BRANCH="main" \
    TARGET_SCRIPT="sentence_generate.py" \
    AWS_ENDPOINT_URL="https://s3.isk01.sakurastorage.jp" \
    MODEL_S3_URI="s3://kirikuchikun/Llama-3-ELYZA-JP-8B" \
    MODEL_LOCAL_DIR="/models/Llama-3-ELYZA-JP-8B"

# ---- entrypoint.sh で実行（実際のスクリプトは TARGET_SCRIPT で切替） ----
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
