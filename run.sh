#!/bin/bash

# ============================================================
# QAnything 启动脚本
# 自动检测平台并启动 Docker Compose 服务
# 所有配置均通过环境变量驱动，默认值见 .env.example
# ============================================================

set -e

# ------------------------------------------------------------
# 颜色定义
# ------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ------------------------------------------------------------
# 工具函数：更新或追加键值对到 .env 文件
# ------------------------------------------------------------
update_or_append_to_env() {
  local key=$1
  local value=$2
  local env_file=".env"

  if [ ! -f "$env_file" ]; then
    touch "$env_file"
  fi

  sed -i'' -e '$a\' "$env_file"

  if grep -q "^${key}=" "$env_file"; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "/^${key}=/c\\
${key}=${value}" "$env_file"
    else
      sed -i "/^${key}=/c\\${key}=${value}" "$env_file"
    fi
  else
    echo "${key}=${value}" >> "$env_file"
  fi

  sed -i'' -e '$a\' "$env_file"
}

# ------------------------------------------------------------
# 检测 Docker Compose 命令
# ------------------------------------------------------------
if docker compose version &>/dev/null; then
  DOCKER_COMPOSE_CMD="docker compose"
elif docker-compose version &>/dev/null; then
  DOCKER_COMPOSE_CMD="docker-compose"
else
  echo -e "${RED}无法找到 'docker compose' 或 'docker-compose' 命令。${NC}"
  exit 1
fi

# ------------------------------------------------------------
# 检测平台
# ------------------------------------------------------------
if [ -e /proc/version ]; then
  if grep -qi microsoft /proc/version || grep -qi MINGW /proc/version; then
    PLATFORM="win"
  else
    PLATFORM="linux"
  fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
  PLATFORM="mac"
else
  PLATFORM="linux"
fi

echo "检测到平台: $PLATFORM"

# ------------------------------------------------------------
# 解析命令行参数
# ------------------------------------------------------------
device_id="-1"

usage() {
    echo "Usage: $0 [-i <device_id>]"
    echo " -i <device_id>: Specify GPU device_id (-1 for CPU, default: -1)"
    exit 1
}

while getopts "i:" opt; do
    case $opt in
        i) device_id=$OPTARG ;;
        *) usage ;;
    esac
done

if [[ ! $device_id =~ ^[0-9]|-1$ ]]; then
    echo -e "${RED}device_id 必须是0-9或-1${NC}"
    exit 1
fi

echo "device_id=${device_id}"

if [[ $device_id == "-1" ]]; then
    echo "将在CPU上启动服务"
else
    echo "将在GPU $device_id 上启动服务"
fi

update_or_append_to_env "GPUID" "$device_id"

# ------------------------------------------------------------
# 加载 .env 文件
# ------------------------------------------------------------
if [ -f .env ]; then
  source .env
fi

# ------------------------------------------------------------
# 配置 USER_IP
# ------------------------------------------------------------
if [ -z "${USER_IP}" ]; then
    read -p "Are you running the code on a remote server or on your local machine? (remote/local) 您是在云服务器上还是本地机器上启动代码？(remote/local) " answer
    if [[ $answer == "local" || $answer == "本地" ]]; then
        ip="localhost"
    else
        read -p "Please enter the server IP address 请输入服务器公网IP地址(示例：10.234.10.144): " ip
        echo "当前设置的远程服务器IP地址为 $ip, QAnything启动后，本地前端服务位于（浏览器打开[http://$ip:8777/qanything/]），请知悉！"
        sleep 5
    fi
    update_or_append_to_env "USER_IP" "$ip"
else
    ip=$USER_IP
    read -p "Do you want to use the previous ip: $ip? (yes/no) 是否使用上次的ip: $ip ？(yes/no) 回车默认选yes，请输入:" use_previous
    use_previous=${use_previous:-yes}
    if [[ $use_previous != "yes" && $use_previous != "是" ]]; then
        read -p "Are you running the code on a remote server or on your local machine? (remote/local) 您是在远程服务器上还是本地机器上启动代码？(remote/local) " answer
        if [[ $answer == "local" || $answer == "本地" ]]; then
            ip="localhost"
        else
            read -p "Please enter the server IP address 请输入服务器公网IP地址(示例：10.234.10.144): " ip
            echo "当前设置的远程服务器IP地址为 $ip, QAnything启动后，本地前端服务位于（浏览器打开[http://$ip:8777/qanything/]），请知悉！"
            sleep 5
        fi
        update_or_append_to_env "USER_IP" "$ip"
    fi
fi

# ------------------------------------------------------------
# 设置 GATEWAY_IP 默认值（基于平台）
# ------------------------------------------------------------
if [ -z "${GATEWAY_IP}" ]; then
    case $PLATFORM in
        linux)
            default_gateway="127.0.0.1"
            ;;
        mac|win)
            default_gateway="host.docker.internal"
            ;;
        *)
            default_gateway="localhost"
            ;;
    esac
    update_or_append_to_env "GATEWAY_IP" "$default_gateway"
fi

# ------------------------------------------------------------
# 构建 docker compose 命令参数
# ------------------------------------------------------------
COMPOSE_FILES="-f docker-compose.yaml -f docker-compose.${PLATFORM}.yaml"

# ------------------------------------------------------------
# 检查 Docker Compose 版本
# ------------------------------------------------------------
echo "检查 Docker Compose 版本..."
if $DOCKER_COMPOSE_CMD $COMPOSE_FILES config 2>&1 | grep -q "services.qanything_local.deploy.resources.reservations value 'devices' does not match"; then
    echo -e "${RED}检测到 Docker Compose 版本过低，请升级到v2.23.3或更高版本。执行 docker compose version 查看版本。${NC}"
    exit 1
fi

# ------------------------------------------------------------
# 准备卷目录
# ------------------------------------------------------------
if [ ! -d "volumes/es/data" ]; then
    mkdir -p volumes/es/data
    chmod 777 -R volumes/es/data
fi

# ------------------------------------------------------------
# 启动服务
# ------------------------------------------------------------
echo -e "${GREEN}启动 QAnything 服务...${NC}"
$DOCKER_COMPOSE_CMD $COMPOSE_FILES up -d

echo -e "${GREEN}服务启动中，查看 qanything_local 日志...${NC}"
$DOCKER_COMPOSE_CMD $COMPOSE_FILES logs -f qanything_local
