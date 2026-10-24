#!/usr/bin/env bash
# =====================================================================
# install_scan_deps.sh — P1/P2 扫描脚本依赖安装（DolphinScheduler 前置 SHELL 任务）
# 目标脚本：security_file_scan.py（P1）/ security_license_scan.py（P2）
#
# 依赖清单（2026-09-22 与两脚本源码核实一致）：
#   P1: pyyaml（yaml 为延迟导入，DANGEROUS_WF/TOKEN_PERM/SAST 解析
#       workflow yml 的硬依赖，缺失时这三个指标报错）
#   P2: scancode-toolkit（scancode 命令必须在 PATH，脚本启动即自检）
#   SPDX 清单为三级回退非硬依赖（--spdx-list-file > URL 下载 > work_dir
#       缓存，全失败仅 osi_fsf_ok 置 NULL 不中断），本脚本仍尝试预置一份
#       固定路径清单，提高 10 分档判定准确率
#   自定义许可证规则（2026-10-16）：CANN-V2.0（华为自研协议，不在 scancode
#       官方知识库；driver 仓 LICENSES/ 下与 GPL-V2.0 并存，多协议 AND 口径
#       要求 CANN 可检出）。走 scancode 官方 --additional-directory 机制：
#       本脚本内嵌规则全文 → 固定路径落盘 → 条件 reindex（仅在规则内容或
#       scancode 版本变化时重建全量索引，日常定时触发直接跳过，秒级）
#
# 版本依据：scancode-toolkit 32.5.0 为本机实测版本（2026-09-21，P2 的
#   license_detections/license_expression_spdx 兼容修复按 32.x 实测），
#   锁版本安装；worker Python < 3.10 时降级 31.2.5（脚本对 3.x/32.x
#   输出字段已做双兼容，但 31.x 非实测版本，日志会打 WARN）
#   pluggy 必须锁 <1.7.0（2026-10-20 worker 踩坑）：scancode-toolkit 32.5.0
#   只约束 pluggy>=1.0.0 无上限，pluggy 1.7.0 重写 hookspec 发现机制
#   （_static_hook_attr 仅认函数/classmethod/staticmethod，不再支持类形式
#   hookspec），而 plugincode 的 @pre_scan_spec 标在 PreScanPlugin 类上，
#   导致 scancode 启动即报 ValueError: did not find any 'pre_scan' hooks
#   （pluggy/_manager.py line 366 为 1.7.0 特有行号）。本机实测 1.6.0 正常。
#
# 用法：DS 工作流最前置的 SHELL 任务执行 bash install_scan_deps.sh
#       幂等可重复执行（pip 已装自动跳过；SPDX 已存在不重复下载；
#       自定义规则 hash+scancode 版本 marker 匹配且可检出时跳过 reindex）
# 可用环境变量覆盖默认值（DS 任务"环境变量"或命令行前缀传入）：
#   PYTHON=python3                  Python 解释器
#   PIP_INDEX_URL=<url>             pip 源（默认华为云内网镜像，worker 无外网时必备）
#   SPDX_FILE=/path/to/spdx.json    SPDX 清单预置路径（建议与 P2 任务
#                                   --spdx-list-file 参数保持一致）
#   CUSTOM_LICENSE_DIR=<dir>       自定义许可证规则目录（内含 licenses/*.LICENSE）
# =====================================================================
set -euo pipefail

PYTHON="${PYTHON:-python3}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://repo.huaweicloud.com/repository/pypi/simple}"
SPDX_FILE="${SPDX_FILE:-/opt/openlibing/security_scan/spdx_licenses.json}"
SPDX_URL="https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json"
CUSTOM_LICENSE_DIR="${CUSTOM_LICENSE_DIR:-/opt/openlibing/security_scan/custom-licenses}"
SCANCODE_VER="32.5.0"      # 本机实测版本（锁版本）
SCANCODE_VER_OLD="31.2.5"  # Python<3.10 降级版本

echo "== [1/6] Python 版本检查 =="
"$PYTHON" --version
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' \
  || { echo "ERROR: 需要 Python >= 3.8"; exit 1; }
if "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  INSTALL_SCANCODE="scancode-toolkit==${SCANCODE_VER}"
else
  INSTALL_SCANCODE="scancode-toolkit==${SCANCODE_VER_OLD}"
  echo "WARN: Python < 3.10，降级安装 scancode-toolkit ${SCANCODE_VER_OLD}（脚本双兼容，非实测版本）"
fi

echo "== [2/6] 安装依赖（pip 源：${PIP_INDEX_URL}）=="
# 说明：非 TTY 下 pip 中途无进度输出，scancode-toolkit 依赖树大（40+ 包），
#       内网镜像慢时耗时数分钟属正常；--timeout/--retries 防无限挂死
"$PYTHON" -m pip install -i "$PIP_INDEX_URL" --upgrade \
  --timeout 60 --retries 3 \
  pyyaml "${INSTALL_SCANCODE}" "pluggy>=1.0.0,<1.7.0"

echo "== [3/6] SPDX 许可证清单预置（可选，失败不阻断）=="
if [ -s "$SPDX_FILE" ]; then
  echo "SPDX 清单已存在：${SPDX_FILE}（$("${PYTHON}" -c "import json;print(len(json.load(open('${SPDX_FILE}'))['licenses']))") 项）"
else
  mkdir -p "$(dirname "$SPDX_FILE")"
  # --max-time 必须设置：github raw 常见"连接成功但传输停滞"，否则无限挂死
  if curl -fsSL --connect-timeout 10 --max-time 120 -o "$SPDX_FILE" "$SPDX_URL"; then
    echo "SPDX 清单下载成功：${SPDX_FILE}"
  else
    rm -f "$SPDX_FILE"
    echo "WARN: SPDX 清单下载失败（worker 无外网？）。P2 运行走三级回退，"
    echo "     osi_fsf_ok 将置 NULL（阶梯 10 分档不可判）。"
    echo "     补救：人工下载该文件并拷贝到 ${SPDX_FILE}，P2 任务传 --spdx-list-file ${SPDX_FILE}"
  fi
fi

echo "== [4/6] 自定义许可证规则落盘（CANN-V2.0，幂等覆盖写）=="
# 格式注意（2026-10-16 本机实测踩坑）：frontmatter 必须以 --- 开头；必须带
# spdx_license_key（CANN 不在 SPDX 清单，用 LicenseRef- 前缀自定义引用，
# 否则 reindex 报 'No SPDX license key'）；目录结构必须为 <dir>/licenses/
# *.LICENSE（直接放根目录 reindex 报 No licenses were loaded）
mkdir -p "$CUSTOM_LICENSE_DIR/licenses"
cat > "$CUSTOM_LICENSE_DIR/licenses/cann-v2.0.LICENSE" <<'CANN_LICENSE_EOF'
---
key: cann-v2.0
language: en
short_name: CANN Open Software License 2.0
name: CANN Open Software License Agreement Version 2.0
category: Proprietary Free
owner: Huawei Technologies Co., Ltd.
homepage_url: https://www.hiascend.com/
notes: custom rule for Huawei CANN-V2.0 license
spdx_license_key: LicenseRef-scancode-cann-v2.0
---

CANN Open Software License Agreement Version 2.0

This CANN Open Software License Agreement Version 2.0 (hereinafter referred to as this "Agreement") is a legal agreement between you and Huawei, and it governs your use, modification, or distribution of CANN Open Software (hereinafter referred to as "Software"). Please read this Agreement carefully.

If you are entering into this Agreement on behalf of a company or other legal entity, you represent that you have the legal authority to bind that entity to this Agreement, in which case "you" will mean the entity you represent.

BY DOWNLOADING, INSTALLING, OR USING THE SOFTWARE, YOU AGREE YOU HAVE FULLY UNDERSTOOD AND ACCEPTED THE TERMS CONTAINED HEREIN. IF YOU DO NOT AGREE TO ANY OF THE TERMS OF THIS AGREEMENT, OR IF YOU DO NOT QUALIFY FOR AGREEING TO THIS AGREEMENT, YOU ARE NOT AUTHORIZED TO AND SHALL NOT DOWNLOAD, INSTALL, OR MAKE ANY USE OF THE SOFTWARE.

1. Definition
1.1 Software means the APIs, source code files, binaries, and related documents of Compute Architecture for Neural Networks("CANN") that are licensable by Huawei, and provided and licensed under this Agreement.
1.2 Huawei AI Processors mean AI chipsets (i) branded with "Ascend", "Kirin", "Yueying" or other brands owned or controlled by Huawei; or (ii) manufactured (including have manufactured), supplied (including have supplied) or designed (including have designed) by Huawei.

2. Grant of Intellectual Property Rights
2.1 Subject to the terms and conditions of this Agreement, including your full compliance thereof, Huawei hereby grants you a limited, worldwide, royalty-free, non-transferable, non-sublicensable, and revocable license for you to (i) download, use, modify, integrate, and distribute the Software or its derivative works for the purpose of developing software solely for use in systems with Huawei AI Processors and/or Software, and (ii) distribute any software developed based upon Software and/or its derivative works solely for use in systems with Huawei AI Processors and/or Software.

3. Restrictions
3.1 You are not authorized to, and shall not use, modify, or distribute this Software or its derivative works for any other purposes than those expressly permitted by this Agreement. You shall not make any use of the Software or its derivative works to develop or distribute any software for use in systems with processors other than Huawei AI Processors. All rights not expressly granted herein are expressly reserved by Huawei.
3.2 You are not authorized to, and shall not remove, obscure, or alter any copyright or other notices in this Software or any part of it.
3.3 Distribution Restrictions
You may distribute the Software or its derivative works in any medium, whether in source or executable forms, for the purpose stipulated in Section 2; provided that you provide recipients with a copy of this Agreement, and retain all notices in the Software.

4. Disclaimer of Warranty and Limitation of Liability
THE SOFTWARE IS PROVIDED WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED. IN NO EVENT SHALL HUAWEI OR ANY OTHER COPYRIGHT HOLDER BE LIABLE TO YOU FOR ANY DAMAGES, INCLUDING, BUT NOT LIMITED TO ANY DIRECT, OR INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES ARISING FROM YOUR USE OR INABILITY TO USE THE SOFTWARE, IN WHOLE OR IN PART, NO MATTER HOW IT IS CAUSED OR THE LEGAL THEORY IT IS BASED ON, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

5. Termination
5.1 This Agreement will continue to apply until terminated by either you or Huawei as described below:
a. You may terminate this Agreement by ceasing your use of the Software;
b. Huawei may at any time, terminate this Agreement if: (i) you fail to comply with any term of this Agreement; or (ii) you directly or indirectly initiate any legal proceeding against any individual or entity by alleging that the Software or any part of it infringes your intellectual property rights.
5.2 By termination, all the rights granted to you under this Agreement are terminated, and you shall cease to use and delete this Software or any derivative works immediately. All rights granted to you under this Agreement shall hereby be void ab initio in the event of termination in accordance with Section 5.1. b above. Huawei reserves the right to pursue any and all legal remedies available to enforce the terms and conditions of this Agreement or to protect Huawei’s intellectual property rights for such breach or violation. All provisions shall survive the termination of this Agreement except for Section 2 and Section 3.3.

6. MISCELLANEOUS
If the application of any provision of this Agreement to any particular facts or circumstances is held to be invalid or unenforceable by a court of competent jurisdiction, then (a) the validity and enforceability of such provision as applied to any other particular facts or circumstances and the validity of other provisions of this Agreement shall not in any way be affected or impaired thereby and (b) such provision shall be enforced to the maximum extent possible so as to affect the intent of the you and Huawei and reformed without further action by you and Huawei to the extent necessary to make such provision valid and enforceable.

END OF THE TERMS AND CONDITIONS
CANN_LICENSE_EOF
echo "规则文件已写入：$CUSTOM_LICENSE_DIR/licenses/cann-v2.0.LICENSE（$(wc -c < "$CUSTOM_LICENSE_DIR/licenses/cann-v2.0.LICENSE") 字节）"

echo "== [5/6] scancode 许可证索引条件重建 =="
# reindex 为全量重建（实测数分钟），不能每次定时触发都跑。marker 绑定
# 「规则文件 hash + scancode 完整版本行」：pip 升级 scancode 会覆盖
# site-packages 内索引缓存（自定义规则随之丢失），必须触发重建；
# marker 匹配时仍做一次快速检出验证（扫规则文件本身应检出 cann-v2.0），
# 防止 cache 被意外破坏而 marker 未感知
custom_rule_ok() {
  local out
  out="$(scancode --license --json-pp - "$CUSTOM_LICENSE_DIR/licenses/cann-v2.0.LICENSE" 2>/dev/null || true)"
  case "$out" in *cann-v2.0*) return 0 ;; *) return 1 ;; esac
}
RULES_HASH="$(md5sum "$CUSTOM_LICENSE_DIR"/licenses/*.LICENSE | md5sum | cut -d' ' -f1)"
MARKER_NOW="$(scancode --version | head -1)__${RULES_HASH}"
MARKER_SAVED="$(cat "$CUSTOM_LICENSE_DIR/.reindex_marker" 2>/dev/null || true)"
if [ -n "$MARKER_SAVED" ] && [ "$MARKER_NOW" = "$MARKER_SAVED" ] && custom_rule_ok; then
  echo "索引已是最新（marker 匹配且 cann-v2.0 可检出），跳过重建"
else
  echo "自定义规则/scancode 版本变化或索引失效，重建许可证索引（数分钟）…"
  scancode-reindex-licenses --additional-directory "$CUSTOM_LICENSE_DIR"
  echo "$MARKER_NOW" > "$CUSTOM_LICENSE_DIR/.reindex_marker"
  echo "索引重建完成，marker 已更新"
fi

echo "== [6/6] 自检 =="
"$PYTHON" -c "import yaml; print('pyyaml OK:', yaml.__version__)"
if command -v scancode >/dev/null 2>&1; then
  echo "scancode OK: $(scancode --version | head -1)"
else
  echo "ERROR: scancode 命令不在 PATH（可能 pip 安装到了用户目录）"
  echo "       排查：which pip && python -m pip show scancode-toolkit | grep Location"
  echo "       如装在 ~/.local：export PATH=\$PATH:~/.local/bin 后重试"
  exit 1
fi

# 自定义规则终验（含自愈：[5/6] 跳过分支已验证过，重建分支在此兜底；
# 失败先强制重建一次再验，仍失败则阻断，避免 P2 带病扫描）
if custom_rule_ok; then
  echo "自定义规则 OK: cann-v2.0 可检出（AND 口径多协议判定就绪）"
else
  echo "WARN: 自定义规则终验失败，强制重建索引重试…"
  scancode-reindex-licenses --additional-directory "$CUSTOM_LICENSE_DIR"
  if custom_rule_ok; then
    echo "自定义规则 OK: cann-v2.0 可检出（重建后恢复）"
  else
    echo "ERROR: 自定义 CANN-V2.0 规则重建后仍未检出，阻断执行"
    echo "       排查：scancode --version 是否 ${SCANCODE_VER}；手工跑"
    echo "       scancode-reindex-licenses --additional-directory ${CUSTOM_LICENSE_DIR} 看报错"
    exit 1
  fi
fi

echo "ALL DEPS OK — P1/P2 依赖就绪"
