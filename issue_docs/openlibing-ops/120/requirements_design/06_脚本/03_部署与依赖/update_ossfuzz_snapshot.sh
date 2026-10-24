#!/usr/bin/env bash
# =====================================================================
# update_ossfuzz_snapshot.sh —— 生成 OSS-Fuzz 名单快照（文本表）
#
# 产出（供 security_gcheck_scan.py --ossfuzz-status 使用）：
#   {BASE_DIR}/ossfuzz_main_repos.txt   文本表，每行一个 main_repo 仓库地址
#                                        （gcheck 加载时自行归一化/去重，无需预处理）
#   {BASE_DIR}/oss-fuzz/                google/oss-fuzz 浅克隆（~52MB，留作增量更新用）
#
# 智能化/幂等：
#   - 快照文件已存在且非空 → 直接跳过（本次目标只是保证有一个快照）
#   - REFRESH=1 → git pull 增量更新并重新提取（后续改造为每日增量任务时使用）
#
# 用法：
#   bash update_ossfuzz_snapshot.sh [目标根目录]              # 幂等：已有则跳过
#   REFRESH=1 bash update_ossfuzz_snapshot.sh [目标根目录]    # 强制增量刷新
#
# 交付说明（服务器连不上 GitHub，2026-10 起改走配置中心）：
#   在任意能连 GitHub 的机器上执行（每日增量任务也在这类机器上挂），
#   产物 ossfuzz_main_repos.txt 上传 DS 配置中心 gcheck/ 文件夹覆盖，
#   security_gcheck_scan.py 自动识别。worker 目录 /openlibing/gcheck 落位同样支持。
#
# gcheck 名单比对说明：ossfuzz_main_repos.txt 是 projects/*/project.yaml 的
# main_repo 预清洗结果（2026-10 实测 1385 个项目 / 1356 条地址，~54KB），
# 文本表加载毫秒级；等价于把整个 projects/ 目录喂给 gcheck（目录形态每次
# 都要逐个解析 yaml，慢且没必要）。
# =====================================================================
set -euo pipefail

BASE_DIR="${1:-/openlibing/gcheck}"
REFRESH="${REFRESH:-0}"
TXT="${BASE_DIR}/ossfuzz_main_repos.txt"
CLONE_DIR="${BASE_DIR}/oss-fuzz"
REPO_URL="https://github.com/google/oss-fuzz.git"

mkdir -p "${BASE_DIR}"

# ---------- 幂等：已有非空快照且未要求刷新 → 跳过 ----------
if [ "${REFRESH}" != "1" ] && [ -s "${TXT}" ]; then
    echo "[SKIP] snapshot exists: ${TXT} ($(wc -l < "${TXT}") repos)"
    echo "       use REFRESH=1 to force update"
    exit 0
fi

command -v git >/dev/null 2>&1 || { echo "[ERROR] git is required" >&2; exit 1; }

# ---------- 获取 oss-fuzz 仓库（已有则增量 pull，否则浅克隆） ----------
if [ -d "${CLONE_DIR}/.git" ]; then
    echo "[UPDATE] git pull oss-fuzz (${CLONE_DIR})..."
    git -C "${CLONE_DIR}" pull --ff-only
else
    echo "[CLONE] shallow clone google/oss-fuzz (~52MB)..."
    rm -rf "${CLONE_DIR}"
    git clone --depth 1 "${REPO_URL}" "${CLONE_DIR}"
fi

# ---------- 清洗：projects/*/project.yaml 的 main_repo → 每行一个地址 ----------
echo "[EXTRACT] main_repo -> ${TXT} ..."
grep -rh --include=project.yaml -E '^main_repo:' "${CLONE_DIR}/projects" \
  | sed -E "s/^[[:space:]]*main_repo:[[:space:]]*//" \
  | sed -E "s/[[:space:]]+#.*$//" \
  | sed -E "s/^\"(.*)\"$/\1/; s/^'(.*)'$/\1/" \
  | sed -E "s/[[:space:]]+$//" \
  | grep -v -E '^(\||>|-|\+|~|null|none|nil)?$' \
  | sort -u > "${TXT}"

LINES="$(wc -l < "${TXT}")"
if [ "${LINES}" -eq 0 ]; then
    echo "[ERROR] extracted 0 repos — clone failed or projects/ layout changed" >&2
    exit 1
fi

echo "[OK] ${TXT}"
echo "     ${LINES} unique main_repo entries"
