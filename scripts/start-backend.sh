#!/usr/bin/env bash
# 启动 SmokeSignal Analytics 后端服务（worktree 通用）
#
# 自动完成三件事，无需手动 source venv 或 .env：
#   1. 通过 git 定位【主仓库】的虚拟环境
#      （worktree 自带的 venv 通常不完整，必须用主仓库的）
#   2. 加载【主仓库】backend/.env（AI key 等密钥就位）
#      （.env 被 .gitignore 忽略，不会出现在 worktree 里）
#   3. 在【当前 worktree】的代码上启动
#
# 用法：./scripts/start-backend.sh

set -euo pipefail

# Preserve explicit shell overrides before backend/.env is loaded.
REQUESTED_API_HOST="${API_HOST-}"
REQUESTED_API_PORT="${API_PORT-}"

# 1. 定位当前 worktree 根（脚本所在 scripts/ 的上一级）
WORKTREE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 2. 通过 git 推导主仓库根
#    worktree:  git-common-dir 返回主仓库 .git 的【绝对路径】
#    普通仓库:  返回【相对路径】 ".git"
#    先 cd 到 WORKTREE_ROOT 再 cd GIT_COMMON，让相对/绝对路径都能正确解析
GIT_COMMON="$(git -C "$WORKTREE_ROOT" rev-parse --git-common-dir 2>/dev/null || true)"
ABS_COMMON="$(cd "$WORKTREE_ROOT" && cd "$GIT_COMMON" 2>/dev/null && pwd)"
if [ -n "$ABS_COMMON" ]; then
    MAIN_ROOT="$(cd "$ABS_COMMON/.." && pwd)"
else
    MAIN_ROOT="$WORKTREE_ROOT"   # git 不可用时兜底
fi

# 3. 主仓库虚拟环境
PYTHON="$MAIN_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    echo "❌ 找不到主仓库虚拟环境: $PYTHON" >&2
    echo "   请先在主仓库创建: cd \"$MAIN_ROOT\" && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

# 4. 加载主仓库 backend/.env（AI key 就位；数据库走 ~/database_config.json 不受影响）
ENV_FILE="$MAIN_ROOT/backend/.env"
if [ -f "$ENV_FILE" ]; then
    set -a; . "$ENV_FILE"; set +a
else
    echo "⚠️  未找到 $ENV_FILE：数据库仍可用，但 AI 分析会降级到规则引擎" >&2
fi

# 5. 启动
HOST="${REQUESTED_API_HOST:-${API_HOST:-0.0.0.0}}"
PORT="${REQUESTED_API_PORT:-${API_PORT:-8000}}"
export API_HOST="$HOST" API_PORT="$PORT"
echo "🚀 SmokeSignal Backend"
echo "   code : $WORKTREE_ROOT"
echo "   venv : $PYTHON ($("$PYTHON" --version 2>&1))"
echo "   url  : http://$HOST:$PORT  (docs: /docs)"
echo ""

cd "$WORKTREE_ROOT"
exec "$PYTHON" -m backend.main
