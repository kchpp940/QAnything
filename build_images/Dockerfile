# 使用官方 Python 3.10.14 镜像作为基础镜像
FROM python:3.10.14-slim
# 安装 vim
RUN apt-get update && apt-get install -y \
    vim \
    wget \
    htop \
    build-essential \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 创建TikToken缓存目录
RUN mkdir /opt/tiktoken_cache

# 下载TikToken模型缓存
ARG TIKTOKEN_URL="https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken"
RUN wget -O /opt/tiktoken_cache/$(echo -n $TIKTOKEN_URL | sha1sum | head -c 40) "$TIKTOKEN_URL"

# 设置环境变量指向TikToken缓存目录
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken_cache

# QAnything 运行时默认环境变量（与 .env.example 对齐，可被外部覆盖）
ENV QANYTHING_HOST=0.0.0.0 \
    QANYTHING_PORT=8777 \
    QANYTHING_WORKERS=4 \
    GPUID=-1 \
    GATEWAY_IP=127.0.0.1 \
    USER_IP=0.0.0.0 \
    MYSQL_HOST=localhost \
    MYSQL_PORT=3316 \
    MYSQL_USER=root \
    MYSQL_PASSWORD=123456 \
    MYSQL_DATABASE=qanything \
    MILVUS_HOST=localhost \
    MILVUS_PORT=19540 \
    ES_HOST=localhost \
    ES_PORT=9210 \
    EMBED_SERVICE_HOST=localhost \
    EMBED_SERVICE_PORT=9001 \
    RERANK_SERVICE_HOST=localhost \
    RERANK_SERVICE_PORT=8001 \
    OCR_SERVICE_HOST=localhost \
    OCR_SERVICE_PORT=7001 \
    PDF_PARSER_SERVICE_HOST=localhost \
    PDF_PARSER_SERVICE_PORT=9009 \
    INSERT_FILES_SERVICE_PORT=8110 \
    STREAMING=true

# 复制 requirements.txt 文件到容器中
COPY requirements.txt /tmp/requirements.txt

# 安装 Python 依赖
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 复制 models 文件夹到 /root 目录
COPY models /root/models
COPY nltk_data /root/nltk_data

# 设置工作目录
WORKDIR /workspace

# 清理 APT 缓存
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# 设置默认命令
CMD ["/bin/bash"]

