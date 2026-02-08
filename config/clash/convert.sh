#!/bin/bash
#
# Clash 配置转换脚本
# 使用自建的 subconverter 服务将本地/远程配置转换为 Clash 配置
# 支持通过 cloudflared 将本地文件暴露到公网
#

set -e

# 配置参数
SUBCONVERTER_URL="${SUBCONVERTER_URL:-https://sub.hweb.peterchen97.cn}"
DEFAULT_CONFIG="https://raw.githubusercontent.com/PeterChen1997/peter-config/master/config/clash/clash-template.ini"
OUTPUT_FILE="clash_config.yaml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_PORT="${LOCAL_PORT:-58888}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 进程 ID
HTTP_SERVER_PID=""
CLOUDFLARED_PID=""

# 清理函数
cleanup() {
    if [[ -n "$HTTP_SERVER_PID" ]]; then
        kill "$HTTP_SERVER_PID" 2>/dev/null || true
    fi
    if [[ -n "$CLOUDFLARED_PID" ]]; then
        kill "$CLOUDFLARED_PID" 2>/dev/null || true
    fi
    rm -f /tmp/cloudflared_$$.log
}

trap cleanup EXIT

# 帮助信息
show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] <subscription_url_or_file>

将订阅链接或本地配置文件转换为 Clash 配置

OPTIONS:
    -c, --config <url>     自定义配置模板 URL (默认使用 clash-template.ini)
    -o, --output <file>    输出文件名 (默认: clash_config.yaml)
    -t, --target <type>    目标格式 (默认: clash, 可选: surge, quanx, v2ray 等)
    -s, --server <url>     Subconverter 服务器 URL (默认: $SUBCONVERTER_URL)
    -h, --help             显示帮助信息

EXAMPLES:
    # 转换远程订阅链接
    $(basename "$0") "https://example.com/subscribe?token=xxx"

    # 转换本地文件 (自动使用 cloudflared 隧道)
    $(basename "$0") ./config/test.yaml

    # 合并多个订阅
    $(basename "$0") "https://sub1.com/sub|https://sub2.com/sub"

    # 使用自定义配置模板
    $(basename "$0") -c "https://example.com/custom.ini" "https://example.com/sub"

    # 输出到指定文件
    $(basename "$0") -o my-config.yaml "https://example.com/sub"

ENVIRONMENT:
    SUBCONVERTER_URL    Subconverter 服务器地址 (默认: $SUBCONVERTER_URL)
    LOCAL_PORT          本地 HTTP 服务器端口 (默认: 58888)
EOF
}

# URL 编码函数
urlencode() {
    python3 -c "import urllib.parse; print(urllib.parse.quote('$1', safe=''))"
}

# 检查是否为 URL
is_url() {
    [[ "$1" =~ ^https?:// ]]
}

# 启动 cloudflared 隧道
start_cloudflared_tunnel() {
    local dir="$1"
    local file_name="$2"

    echo -e "${BLUE}启动本地 HTTP 服务器 (端口: $LOCAL_PORT)...${NC}"
    (cd "$dir" && python3 -m http.server "$LOCAL_PORT" --bind 0.0.0.0 2>/dev/null) &
    HTTP_SERVER_PID=$!
    sleep 1

    if ! kill -0 "$HTTP_SERVER_PID" 2>/dev/null; then
        echo -e "${RED}✗ HTTP 服务器启动失败${NC}"
        return 1
    fi

    echo -e "${BLUE}启动 cloudflared 隧道...${NC}"
    cloudflared tunnel --url "http://localhost:$LOCAL_PORT" 2>&1 | tee /tmp/cloudflared_$$.log &
    CLOUDFLARED_PID=$!

    # 等待隧道建立并获取 URL
    local max_wait=15
    local tunnel_url=""
    for i in $(seq 1 $max_wait); do
        tunnel_url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /tmp/cloudflared_$$.log 2>/dev/null | head -1)
        if [[ -n "$tunnel_url" ]]; then
            break
        fi
        sleep 1
    done

    if [[ -z "$tunnel_url" ]]; then
        echo -e "${RED}✗ 无法获取 cloudflared 隧道 URL${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ 隧道已建立: $tunnel_url${NC}"
    echo "${tunnel_url}/${file_name}"
}

# 转换配置
convert_config() {
    local source_url="$1"
    local config_url="$2"
    local target="$3"
    local output="$4"

    local encoded_url
    encoded_url=$(urlencode "$source_url")
    local encoded_config
    encoded_config=$(urlencode "$config_url")

    local request_url="${SUBCONVERTER_URL}/sub?target=${target}&url=${encoded_url}&config=${encoded_config}"

    echo -e "${YELLOW}正在转换配置...${NC}"
    echo -e "  订阅源: ${source_url}"
    echo -e "  配置模板: ${config_url}"
    echo -e "  目标格式: ${target}"

    local http_code
    http_code=$(curl -s -w "%{http_code}" -o "$output" --max-time 60 "$request_url")

    if [[ "$http_code" == "200" ]]; then
        local file_size
        file_size=$(wc -c < "$output" | tr -d ' ')
        
        if [[ "$file_size" -gt 100 ]]; then
            echo -e "${GREEN}✓ 转换成功！${NC}"
            echo -e "  输出文件: ${output}"
            echo -e "  文件大小: ${file_size} bytes"
            echo -e "  总行数: $(wc -l < "$output" | tr -d ' ') 行"
        else
            echo -e "${RED}✗ 转换结果异常 (文件过小)${NC}"
            cat "$output"
            rm -f "$output"
            return 1
        fi
    else
        echo -e "${RED}✗ 转换失败 (HTTP $http_code)${NC}"
        [[ -f "$output" ]] && cat "$output" && rm -f "$output"
        return 1
    fi
}

# 处理本地文件
handle_local_file() {
    local file="$1"

    # 转换为绝对路径
    local abs_path
    if [[ "$file" = /* ]]; then
        abs_path="$file"
    else
        abs_path="$(pwd)/$file"
    fi

    if [[ ! -f "$abs_path" ]]; then
        echo -e "${RED}错误: 文件不存在: $abs_path${NC}"
        return 1
    fi

    local file_dir
    file_dir=$(dirname "$abs_path")
    local file_name
    file_name=$(basename "$abs_path")

    echo -e "${YELLOW}检测到本地文件: $abs_path${NC}"

    # 检查 cloudflared 是否可用
    if ! command -v cloudflared &> /dev/null; then
        echo -e "${RED}错误: cloudflared 未安装${NC}"
        echo -e "${YELLOW}安装方法: brew install cloudflared${NC}"
        return 1
    fi

    start_cloudflared_tunnel "$file_dir" "$file_name"
}

# 主函数
main() {
    local config_url="$DEFAULT_CONFIG"
    local target="clash"
    local output="$OUTPUT_FILE"
    local source=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -c|--config)
                config_url="$2"
                shift 2
                ;;
            -o|--output)
                output="$2"
                shift 2
                ;;
            -t|--target)
                target="$2"
                shift 2
                ;;
            -s|--server)
                SUBCONVERTER_URL="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                echo -e "${RED}未知选项: $1${NC}"
                show_help
                exit 1
                ;;
            *)
                source="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$source" ]]; then
        echo -e "${RED}错误: 请提供订阅链接或本地配置文件${NC}"
        echo
        show_help
        exit 1
    fi

    local source_url
    if is_url "$source"; then
        source_url="$source"
    else
        source_url=$(handle_local_file "$source")
        if [[ $? -ne 0 ]]; then
            exit 1
        fi
    fi

    convert_config "$source_url" "$config_url" "$target" "$output"
}

main "$@"
