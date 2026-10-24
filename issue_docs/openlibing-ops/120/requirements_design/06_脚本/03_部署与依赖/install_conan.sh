#!/usr/bin/env bash
# =====================================================================
# install_conan.sh —— 安装 conan CLI（供 security_gcheck_scan.py 的
# openUBMC PINNED_DEP 特判使用：conan download --only-recipe 拉组件
# recipe、读取 conandata.yml 建组件↔代码仓映射）
#
# 产出：
#   python 环境里的 conan 命令（conan 2.x，entry point 在 python bin 目录）
#   {MARKER} 版本标记文件（幂等判断依据）
#
# 智能化/幂等：
#   - conan 已可用且为 2.x（--version 校验）→ 直接跳过，不重复安装
#   - 不可用 → pip3 安装；优先走离线 wheel 目录（配置中心下发），失败再
#     回退 PyPI 在线安装
#
# 用法：
#   bash install_conan.sh [wheel目录]           # 默认脚本同目录 conan-wheels/
#   bash install_conan.sh /path/to/conan-wheels
#
# 交付说明（worker 可能连不上 PyPI，2026-10 起参照 scorecard 走配置中心）：
#   在任意能连 PyPI 的机器上执行：
#     pip3 download conan --dest conan-wheels     # 连带依赖 wheel 一次下齐
#   把整个 conan-wheels/ 目录上传 DS 配置中心 gcheck/ 文件夹（或共享盘落位
#   /openlibing/gcheck/conan-wheels/），本脚本在同机执行时会自动发现并离线安装。
#   worker 可直连 PyPI 时无需任何前置产物，脚本直接在线安装。
# =====================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEEL_DIR="${1:-${SCRIPT_DIR}/conan-wheels}"
CONAN_SPEC="conan>=2.0,<3"          # conan 1.x 不兼容本脚本调用方式（conan cache path 等 2.x 子命令）
MARKER="/openlibing/gcheck/.conan-installed"

log() { echo "[install_conan] $*"; }

# ---------- 幂等：conan 已可用且为 2.x → 跳过 ----------
installed_version="$(conan --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
if [ -n "${installed_version}" ]; then
    major="${installed_version%%.*}"
    if [ "${major}" = "2" ]; then
        log "[SKIP] conan v${installed_version} already installed: $(command -v conan)"
        mkdir -p "$(dirname "${MARKER}")"
        echo "${installed_version}" > "${MARKER}"
        exit 0
    fi
    log "[WARN] existing conan v${installed_version} (1.x incompatible), re-installing..."
else
    log "conan not found in PATH (若报 Errno 20 说明 PATH 有坏条目，不影响本安装)"
fi

# ---------- 安装：离线 wheel 优先，PyPI 在线兜底 ----------
if [ -d "${WHEEL_DIR}" ] && ls "${WHEEL_DIR}"/conan-*.whl >/dev/null 2>&1; then
    log "[INSTALL] offline from wheels: ${WHEEL_DIR}"
    pip3 install --no-index --find-links "${WHEEL_DIR}" "${CONAN_SPEC}"
else
    log "[INSTALL] online from PyPI: ${CONAN_SPEC}"
    pip3 install --retries 5 --timeout 60 "${CONAN_SPEC}"
fi

# ---------- 安装后校验 ----------
final_version="$(conan --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
if [ -z "${final_version}" ]; then
    log "[FAIL] conan still not executable after install (检查 python bin 目录是否在 PATH)"
    exit 1
fi
major="${final_version%%.*}"
if [ "${major}" != "2" ]; then
    log "[FAIL] conan v${final_version} is not 2.x"
    exit 1
fi
mkdir -p "$(dirname "${MARKER}")"
echo "${final_version}" > "${MARKER}"
log "[OK] conan v${final_version} installed: $(command -v conan)"
