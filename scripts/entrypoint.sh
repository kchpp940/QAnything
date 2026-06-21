#!/bin/bash

# ============================================================
# QAnything 容器入口脚本
# 所有配置均通过环境变量驱动，默认值见 .env.example
# ============================================================

check_log_errors() {
    local log_file=$1

    if [[ ! -f "$log_file" ]]; then
        echo "指定的日志文件不存在: $log_file"
        return 1
    fi

    local pattern="core dumped|Error|error"
    if grep -E -C 5 "$pattern" "$log_file"; then
        echo "检测到错误信息，请查看上面的输出。"
        exit 1
    else
        echo "$log_file 中未检测到明确的错误信息。请手动排查 $log_file 以获取更多信息。"
    fi
}

start_time=$(date +%s)

# ------------------------------------------------------------
# 环境变量默认值
# ------------------------------------------------------------
export USER_IP=${USER_IP:-0.0.0.0}
export QANYTHING_PORT=${QANYTHING_PORT:-8777}
export QANYTHING_WORKERS=${QANYTHING_WORKERS:-1}
export RERANK_SERVICE_PORT=${RERANK_SERVICE_PORT:-8001}
export EMBED_SERVICE_PORT=${EMBED_SERVICE_PORT:-9001}
export PDF_PARSER_SERVICE_PORT=${PDF_PARSER_SERVICE_PORT:-9009}
export OCR_SERVICE_PORT=${OCR_SERVICE_PORT:-7001}
export INSERT_FILES_SERVICE_PORT=${INSERT_FILES_SERVICE_PORT:-8110}

WORK_DIR="/workspace/QAnything"
LOG_DIR="${WORK_DIR}/logs/debug_logs"

# ------------------------------------------------------------
# 准备工作目录和日志目录
# ------------------------------------------------------------
if [ ! -d "$LOG_DIR" ]; then
  mkdir -p "$LOG_DIR"
  echo "Directory $LOG_DIR created."
else
  echo "Directory $LOG_DIR already exists."
fi

cd "$WORK_DIR" || exit

# ------------------------------------------------------------
# 模型文件软链接
# ------------------------------------------------------------
if [ ! -L "qanything_kernel/dependent_server/embedding_server/embedding_model_configs_v0.0.1" ]; then
  cd qanything_kernel/dependent_server/embedding_server && ln -s /root/models/linux_onnx/embedding_model_configs_v0.0.1 .
  cd "$WORK_DIR"
fi

if [ ! -L "qanything_kernel/dependent_server/rerank_server/rerank_model_configs_v0.0.1" ]; then
  cd qanything_kernel/dependent_server/rerank_server && ln -s /root/models/linux_onnx/rerank_model_configs_v0.0.1 .
  cd "$WORK_DIR"
fi

if [ ! -L "qanything_kernel/dependent_server/ocr_server/ocr_models" ]; then
  cd qanything_kernel/dependent_server/ocr_server && ln -s /root/models/ocr_models .
  cd "$WORK_DIR"
fi

if [ ! -L "qanything_kernel/dependent_server/pdf_parser_server/pdf_to_markdown/checkpoints" ]; then
  cd qanything_kernel/dependent_server/pdf_parser_server/pdf_to_markdown/ && ln -s /root/models/pdf_models checkpoints
  cd "$WORK_DIR"
fi

if [ ! -L "nltk_data" ]; then
  ln -s /root/nltk_data .
fi

cd "$WORK_DIR" || exit

# ------------------------------------------------------------
# 启动各依赖服务
# ------------------------------------------------------------
echo "embedding和rerank服务将在CPU上运行"

nohup python3 -u qanything_kernel/dependent_server/rerank_server/rerank_server.py \
  --port "$RERANK_SERVICE_PORT" \
  > "$LOG_DIR/rerank_server.log" 2>&1 &
PID_RERANK=$!

nohup python3 -u qanything_kernel/dependent_server/embedding_server/embedding_server.py \
  --port "$EMBED_SERVICE_PORT" \
  > "$LOG_DIR/embedding_server.log" 2>&1 &
PID_EMBED=$!

nohup python3 -u qanything_kernel/dependent_server/pdf_parser_server/pdf_parser_server.py \
  --port "$PDF_PARSER_SERVICE_PORT" \
  > "$LOG_DIR/pdf_parser_server.log" 2>&1 &
PID_PDF=$!

nohup python3 -u qanything_kernel/dependent_server/ocr_server/ocr_server.py \
  --port "$OCR_SERVICE_PORT" \
  > "$LOG_DIR/ocr_server.log" 2>&1 &
PID_OCR=$!

nohup python3 -u qanything_kernel/dependent_server/insert_files_serve/insert_files_server.py \
  --port "$INSERT_FILES_SERVICE_PORT" \
  --workers 1 \
  > "$LOG_DIR/insert_files_server.log" 2>&1 &
PID_INSERT=$!

nohup python3 -u qanything_kernel/qanything_server/sanic_api.py \
  --host "$USER_IP" \
  --port "$QANYTHING_PORT" \
  --workers "$QANYTHING_WORKERS" \
  > "$LOG_DIR/main_server.log" 2>&1 &
PID_MAIN=$!

# ------------------------------------------------------------
# 生成 close.sh 脚本
# ------------------------------------------------------------
cat > close.sh <<EOF
#!/bin/bash
kill $PID_RERANK $PID_EMBED $PID_PDF $PID_OCR $PID_INSERT $PID_MAIN
EOF
chmod +x close.sh

# ------------------------------------------------------------
# 等待后端服务启动
# ------------------------------------------------------------
backend_start_time=$(date +%s)

while ! grep -q "Starting worker" "$LOG_DIR/main_server.log"; do
    echo "Waiting for the backend service to start..."
    echo "等待启动后端服务"
    sleep 1

    current_time=$(date +%s)
    elapsed_time=$((current_time - backend_start_time))

    if [ $elapsed_time -ge 180 ]; then
        echo "启动后端服务超时，自动检查日志文件 $LOG_DIR/main_server.log："
        check_log_errors "$LOG_DIR/main_server.log"
        exit 1
    fi
    sleep 5
done

echo "qanything后端服务已就绪!"

# ------------------------------------------------------------
# 输出启动信息
# ------------------------------------------------------------
current_time=$(date +%s)
elapsed=$((current_time - start_time))
echo "Time elapsed: ${elapsed} seconds."
echo "已耗时: ${elapsed} 秒."
echo "请在[http://$USER_IP:$QANYTHING_PORT/qanything/]下访问前端服务来进行问答"
echo "如果前端报错，请在浏览器按F12以获取更多报错信息"

# Keep the container running
while true; do
    sleep 5
done
