#!/usr/bin/env bash
# =====================================================================
# install_scorecard.sh —— 下载安装 OSSF Scorecard 二进制（Linux amd64）
#
# 产出（供 security_gcheck_scan.py --scorecard-bin 使用）：
#   {BASE_DIR}/scorecard-bin/scorecard            二进制本体
#   {BASE_DIR}/scorecard-bin/.scorecard-version   版本标记（幂等判断依据）
#
# 智能化/幂等：
#   - 已安装且版本一致（标记文件为准，--version 辅助校验）→ 直接跳过，不重复下载
#   - 版本不一致 → 重新下载覆盖
#
# 用法：
#   bash install_scorecard.sh [目标根目录]        # 默认 /openlibing/gcheck
#
# 交付说明（服务器连不上 GitHub，2026-10 起改走配置中心）：
#   在任意能连 GitHub 的机器（有网 Linux 机 / 本地 Git Bash）上执行，
#   产物 {BASE_DIR}/scorecard-bin/scorecard 上传 DS 配置中心 gcheck/ 文件夹
#   （文件名保持 scorecard），security_gcheck_scan.py 自动识别并 chmod +x。
#   若 worker 可达共享盘且目录落位 /openlibing/gcheck，也可整目录部署，
#   py 脚本对两种落位都支持（worker 目录优先）。
# =====================================================================
set -euo pipefail

BASE_DIR="${1:-/openlibing/gcheck}"
VERSION="5.5.0"
SHA256="83b90a05c1540ef1390db1cd5711e5fd04be9c1d8537fb84d39d02092d6a8dff"
BIN_DIR="${BASE_DIR}/scorecard-bin"
BIN="${BIN_DIR}/scorecard"
MARKER="${BIN_DIR}/.scorecard-version"
URL="https://github.com/ossf/scorecard/releases/download/v${VERSION}/scorecard_${VERSION}_linux_amd64.tar.gz"

mkdir -p "${BIN_DIR}"

# ---------- 幂等：已安装且版本一致 → 跳过 ----------
if [ -x "${BIN}" ]; then
    installed_version="$(cat "${MARKER}" 2>/dev/null || true)"
    if [ -z "${installed_version}" ]; then
        # 无标记文件（例如手工放过来的二进制）：用 --version 识别
        installed_version="$("${BIN}" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
    fi
    if [ "${installed_version}" = "${VERSION}" ]; then
        echo "[SKIP] scorecard v${VERSION} already installed: ${BIN}"
        "${BIN}" --version 2>/dev/null || true
        exit 0
    fi
    echo "[WARN] existing scorecard version='${installed_version:-unknown}' != v${VERSION}, re-installing..."
fi

# ---------- 下载 + SHA256 校验 ----------
echo "[DOWNLOAD] scorecard v${VERSION} (linux amd64)..."
TMP_TGZ="$(mktemp /tmp/scorecard_v${VERSION}.XXXXXX.tar.gz)"
trap 'rm -f "${TMP_TGZ}"' EXIT

curl -fSL --retry 5 --retry-delay 3 --connect-timeout 30 -o "${TMP_TGZ}" "${URL}"

echo "[VERIFY] sha256 checksum..."
echo "${SHA256}  ${TMP_TGZ}" | sha256sum -c -

# ---------- 解压安装 ----------
tar -xzf "${TMP_TGZ}" -C "${BIN_DIR}" scorecard
chmod +x "${BIN}"
echo "${VERSION}" > "${MARKER}"

echo "[OK] scorecard v${VERSION} installed: ${BIN}"
"${BIN}" --version 2>/dev/null || echo "(note: --version not supported by this build, marker file used instead)"
