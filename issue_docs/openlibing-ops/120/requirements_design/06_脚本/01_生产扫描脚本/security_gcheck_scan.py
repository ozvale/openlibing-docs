#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全 gcheck 扫描脚本（P1b，代码安全检查评分看板 · design.md v4 §5.5/§5.6/§5.13）

功能（3 个 metric_code，判定引擎 = gcheck，官方 OSSF Scorecard v5.5.0 的 GitCode 离线适配层，
源码 docs/0912/参考/gcheck/gcheck/src，口径源 docs/0912/参考/gcheck使用文档 2.0/ 三份手册）：
  指标5  PINNED_DEP      依赖版本锁定   score = compliant / (compliant+nonCompliant) × 10
                                     （严格口径：镜像@sha256 / pip --require-hashes /
                                     URL 带 40 位提交 SHA；只钉版本号不算锁定）
                                     无依赖（status=not-applicable）→ NA
  指标13 FUZZING         模糊测试       阶梯取最高档：OSS-Fuzz 或 ClusterFuzzLite 命中=10；
                                     原生 fuzz 函数（go-native/c+cpp+swift-libfuzzer/
                                     python-atheris/rust-cargo-fuzz/java-jazzer）=5；
                                     property-testing（8 语言）=3；全 miss=0
  指标6  BINARY_ARTIFACTS 二进制制品     按文件内容魔数识别（ELF/PE/Mach-O/WASM/ar，≥64 字节），
                                     替代 security_file_scan.py 的 22 种后缀清单（.gz/.zip/.pdf
                                     等源码包/文档不再误伤；.jar/.pyc 等非可执行产物不再上报）；
                                     score = max(0, 10 − nonCompliant 数)，clean=10；无 NA

与 security_file_scan.py 的关系（2026-10-08 拆分拍板）：
  - 共表共口径：同写 dwi_rd_efc_security_file_scan（UNIQUE KEY repo_id+metric_code+scan_time，
    同批次重跑自动覆盖，幂等），下游 D4/D6/明细配置引擎不感知行来自哪个脚本；
  - 独立部署：gcheck 源码 + scorecard 二进制（生产 Linux 版）+ OSS-Fuzz 名单快照
    只为本脚本服务，缺失/故障不影响既有 8 指标批次；
  - 所有权移交：BINARY_ARTIFACTS 的后缀清单实现已从 security_file_scan.py 移除，
    两脚本不得同时产出该 metric_code（同 metric_code 不同 scan_time 会造成批次口径错乱）。

打分映射与容错硬规则（docs/0912/gcheck-integration-handover.md §五）：
  - 分母 = summary.compliant + summary.nonCompliant，**不拿判据计数之和当分母**
    （id=null 的 error 条目不归任何判据；notSupported/error 不进分子也不进分母）
  - 退出码 0=跑成功（findings 也是 0）；1=用法错误；3=inconclusive（有分片/CI 源没扫成）
  - check status=inconclusive/error 或判据 unavailable → 该指标 NA（is_na=1），**不是 0 分**
    （"没看成"≠"没问题"，与 DANGEROUS_WF 解析失败整仓 NA 同口径）
  - 退出码 3 不再整仓三指标 NA（2026-10-12 修正）：JSON 可解析时按各 check 自身 status
    分别落分——仅 inconclusive/error 的 check 落 NA，跑出确定结论（findings/clean/
    not-applicable）的 check 照常打分；JSON 不可解析才整仓 NA。
    修正动机：首跑批次 5 仓 exit=3 整仓 NA，丢掉了 fuzzing/binary-artifacts 的确定结论
    （pytorch 等 4 仓 fuzzing=findings、cann-recipes-train binary=findings 均被埋）
  - id=null 的仓库级条目不丢弃（fuzzing 的唯一结论条目、pinned-deps 的 error 条目）
  - fuzzing 的 ossFuzz miss 必须区分：inputs.ossfuzz 非空=比对过名单里没有（确定 miss）；
    warnings 含"未做名单比对"=没能比对（不确定）。后者照常打分（按 miss 走阶梯），
    detail.ossfuzz_uncertain=true 供明细页标注。

流程（与 security_file_scan.py 同构，公共层照抄）：
  1. 从 Doris 读仓库清单：sdi_repo_info WHERE platform='gitcode' AND repo_id IN
     (operate_conf is_operate=1)，JOIN sdi_repo_branch_info 取默认分支（default_branch=true）
  2. 复用"处理脚本"预 clone 的本地仓：{repo-base-dir}/{platform}/{owner}/{repo_name}，
     仅 checkout 默认分支（不 fetch）。三种异常均写 NA 行不丢仓：
       ① 无默认分支 → 3 指标全 NA（reason=no_default_branch）
       ② 本地目录不存在 → 3 指标全 NA（reason=repo_not_found）
       ③ checkout 失败 → 3 指标全 NA（reason=checkout_failed）
  3. 单仓一次 subprocess 跑 3 个 check（--check 可重复传，比分三次省）：
     python -m gcheck run --check pinned-deps --check fuzzing --check binary-artifacts
       --path <本地仓> --offline --repo-uri <repo_url> [--ossfuzz-status <快照>]
       --scorecard-bin <scorecard 二进制> --format json --output <临时文件>
     Windows 本地自动追加 --allow-unsupported-platform（生产 Linux 不加）；
     --repo-uri 用于 OSS-Fuzz 名单比对（gcheck 内部自带归一化：去 https://、
     git@、.git，转小写，repo_url 原样传即可）
  4. 解析 JSON → 按上述打分映射 → detail_json 组装 → 写表

部署三件套与路径解析（优先级：显式 CLI 参数 > worker 生产目录 > 配置中心 gcheck/
文件夹（同 utils/decrypt-tool.jar 的资源引用模式，实际生产落位）> 本地开发目录，
见 resolve_deploy_paths）：
  1. gcheck 源码：配置中心 gcheck/ 文件夹下传 gcheck-src.tar.gz（~67KB），
     运行时自动解压到 <脚本目录>/gcheck/src（_ensure_gcheck_src，幂等）；
     本地开发 → <脚本目录>/参考/gcheck/gcheck/src
  2. scorecard 二进制（Linux v5.5.0）：
     a. worker 目录 /openlibing/gcheck/scorecard-bin/scorecard
        （install_scorecard.sh 产出，仅适用于能连 GitHub 的机器）
     b. 配置中心 gcheck/ 文件夹下传 scorecard（部署时需 chmod +x，
        在 DS 任务前置命令处理）
     本地开发 → <脚本目录>/_test_gcheck/scorecard.exe（Windows v5.5.0）
  3. OSS-Fuzz 名单（文本表，每行一个 main_repo；gcheck 加载时自行归一化/去重）：
     a. worker 目录 /openlibing/gcheck/ossfuzz_main_repos.txt
        （update_ossfuzz_snapshot.sh 产出，仅适用于能连 GitHub 的机器）
     b. 配置中心 gcheck/ 文件夹下传 ossfuzz_main_repos.txt（实际生产落位；
        服务器连不上 GitHub，名单在本地用 _extract_ossfuzz_main_repos.py 生成后上传）
     两处都有时优先 a；都没有则名单比对为"不确定 miss"，不阻断打分
  其余前置：Python3 + pip install pymysql；"处理脚本"已完成预 clone；
  Doris 已建 dwi_rd_efc_security_file_scan 表；
  凭证不落脚本：Doris 认证从参数/环境变量注入，禁止写死

DS（DolphinScheduler）部署：脚本内 DS 占位符由 DS 全局文本替换注入，
本地裸跑时占位符未替换（仍以 $ 开头），自动回退 CLI 参数。

凭证（2026-10-23 起对齐 示例解密的任务.py 的 decrypt-tool.jar 加密模式）：
  - Doris：${openlibing_doris_url} 明文；${openlibing_doris_username_crypto} /
    ${openlibing_doris_password_crypto} 密文，运行时 java -jar utils/decrypt-tool.jar
    --salt ${salt} 解密（本地调试回退 --doris-username/--doris-password）
  - openUBMC conan：用户名明文内置（OPENUBMC_CONAN_USER 常量）；密码走
    ${openubmc_conan_psw_crypto} 密文（decrypt-tool.jar 解密），本地调试回退
    --conan-psw；未配置时仅 openUBMC 社区仓 PINNED_DEP 落 NA，不影响其他仓

openUBMC 社区特判（2026-10-23，gcheck 不识别 conan 生态的补充口径）：
  openUBMC 社区仓（sdi_repo_info.project_id = dm_rd_efc_security_community_conf.project_id
  AND community_name='openUBMC'，现网 10 仓）的 PINNED_DEP 改由 conan/manifest 口径产出：
  浅克隆 openUBMC/manifest 仓 → 解析 build/**/manifest.yml 的 conan 依赖（排除
  action:delete、含嵌套 dependencies）→ build/openubmc.lock + build/sdk/openubmc_sdk.lock
  固化集合 → conan download --only-recipe 读 conandata.yml sources.url 建立组件→代码仓
  映射（仅 gitcode.com/openUBMC/* 归仓，镜像/外部仓过滤）。打分按组件判定：
  被固化=10、未固化=0、未被 manifest 依赖=NA(no_dependency)。FUZZING/BINARY_ARTIFACTS
  仍走 gcheck 照常落分；非 openUBMC 社区仓零影响（钩子按集合相交触发）。
  前置依赖：worker 需 conan CLI（pip install conan>=2）、PyYAML、java（decrypt-tool.jar）、
  可达 conan.openubmc.cn 与 gitcode.com。
"""

import os
import sys
import json
import argparse
import datetime
import subprocess
import tempfile

# Windows 控制台编码保护：强制 UTF-8 输出，避免中文/特殊字符炸掉日志
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("ERROR: pymysql is required. Install: pip install pymysql")
    sys.exit(1)

# =====================================================================
# 常量区（口径源：gcheck 使用手册三份 + gcheck-integration-handover.md §五）
# =====================================================================

# Doris 目标表（与 security_file_scan.py 共表，dwi-dm层建表DDL.sql [4]）
TARGET_TABLE = 'dwi_rd_efc_security_file_scan'

# 依赖锁定全量明细表（PINNED_DEP 依赖条目逐行落库，不截断，分页接口数据源；
# 建表 DDL 见 dwi_rd_efc_security_pinned_dep_detail.sql）
PINNED_DEP_DETAIL_TABLE = 'dwi_rd_efc_security_pinned_dep_detail'

# 处理脚本预 clone 的本地仓根目录（与 DS"[GitCode]扫描代码仓编码风格"任务一致）
DEFAULT_REPO_BASE_DIR = '/openlibing/git'

# detail_json 内路径数组的截断上限（防止千级文件爆行，计数仍是全量）
# 2026-10-23 200→600：现网最大仓（DrivingSDK）依赖条目 555 条，600 可全量覆盖，
# failItems 卡片与判据汇总 qcount 随之变为事实全量；detail_json 最坏 ~240KB/行仍在安全范围
MAX_DETAIL_PATHS = 600

# metric_code -> gcheck check 名（输出 JSON checks[].check）
METRIC_CHECK_MAP = {
    'PINNED_DEP': 'pinned-deps',
    'FUZZING': 'fuzzing',
    'BINARY_ARTIFACTS': 'binary-artifacts',
}

# 单仓一次 gcheck 调用跑的 check 列表（--check 可重复传）
GCHECK_CHECKS = ['pinned-deps', 'fuzzing', 'binary-artifacts']

# 单仓 gcheck 超时（秒）。常规仓实测三 check 约 30s（repo_400030 22s）；生产批次
# 默认 600s（10 分钟，超时按 NA 处理不阻断批次）；超大仓（如 msdebug 14.7 万文件）
# 600s 跑不完，不走本默认值——单独建 DS 任务用 --repo-ids 圈定仓库、--gcheck-timeout 0
# 不设超时补扫。--gcheck-timeout 可调，传 0 = 不设超时等 gcheck 自然跑完。
DEFAULT_GCHECK_TIMEOUT = 600

# fuzzing 打分阶梯判据分组（gcheck checklist[].id，17 项固定顺序，见 manual-fuzzing.md）
# 上游常量名（tool）在 checklist[].tool，判定极性：hit=命中
FUZZ_TIER10 = ('ossFuzz', 'clusterFuzzLite')
FUZZ_TIER5_NATIVE = ('go-native', 'c-libfuzzer', 'cpp-libfuzzer', 'swift-libfuzzer',
                     'python-atheris', 'rust-cargo-fuzz', 'java-jazzer')
FUZZ_TIER3_PROPERTY = ('haskell-property-testing', 'javascript-property-testing',
                       'typescript-property-testing', 'csharp-property-testing',
                       'fsharp-property-testing', 'erlang-property-testing',
                       'elixir-property-testing', 'gleam-property-testing')

# 脚本同级目录（gcheck 源码 / scorecard.exe 的默认相对位置都基于此）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 生产部署目录约定（_deploy_gcheck/install_scorecard.sh 与 update_ossfuzz_snapshot.sh 的产出位置，
# 与既有 /openlibing/git、/openlibing/workflow 同级约定）
PROD_GCHECK_BASE = '/openlibing/gcheck'
PROD_SCORECARD_BIN = os.path.join(PROD_GCHECK_BASE, 'scorecard-bin', 'scorecard')
PROD_OSSFUZZ_TXT = os.path.join(PROD_GCHECK_BASE, 'ossfuzz_main_repos.txt')

# =====================================================================
# 参数与环境
# =====================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Security gcheck scan (P1b): PINNED_DEP/FUZZING/BINARY_ARTIFACTS '
                    '-> dwi_rd_efc_security_file_scan (gcheck engine)')
    parser.add_argument('--doris-url', default=None,
                        help='Doris JDBC URL（本地调试用；DS 运行时由占位符注入，无需传）')
    parser.add_argument('--doris-username', default=None, help='Doris 用户名（本地调试用）')
    parser.add_argument('--doris-password', default=None, help='Doris 密码（本地调试用）')
    parser.add_argument('--conan-user', default=None,
                        help='openUBMC 社区账号明文（可选，缺省用脚本内置 OPENUBMC_CONAN_USER 常量）')
    parser.add_argument('--conan-psw', default=None,
                        help='openUBMC 社区密码明文（本地调试用；DS 运行时走 '
                             '${openubmc_conan_psw_crypto} 解密注入，无需传）')
    parser.add_argument('--repo-ids', default=None,
                        help='逗号分隔的 repo_id 过滤列表（调试单仓用），如 401431；缺省扫全部 is_operate=1')
    parser.add_argument('--repo-base-dir', default=DEFAULT_REPO_BASE_DIR,
                        help='处理脚本预 clone 的本地仓根目录（默认 /openlibing/git），'
                             '仓路径 = {base}/{platform}/{owner}/{repo_name}')
    parser.add_argument('--gcheck-src', default=None,
                        help='gcheck 源码目录（PYTHONPATH 用，含 gcheck 包）。缺省时自动解析：'
                             '优先 <脚本目录>/gcheck/src（不存在则从 gcheck/gcheck-src.tar.gz '
                             '或 gcheck-src.tar.gz 自动解压，DS 配置中心上传模式），'
                             '本地开发回退 <脚本目录>/参考/gcheck/gcheck/src')
    parser.add_argument('--scorecard-bin', default=None,
                        help='scorecard 二进制路径。缺省时自动解析：worker 目录 '
                             '/openlibing/gcheck/scorecard-bin/scorecard 优先，'
                             '其次配置中心 gcheck/ 文件夹下的 scorecard（需 chmod +x），'
                             '本地开发回退 _test_gcheck/scorecard.exe（Windows v5.5.0）')
    parser.add_argument('--ossfuzz-status', default=None,
                        help='OSS-Fuzz 名单快照路径（目录/status.json/文本表均可，'
                             '推荐文本表 ossfuzz_main_repos.txt）。缺省时自动解析：'
                             'worker 目录 /openlibing/gcheck/ossfuzz_main_repos.txt 优先，'
                             '其次配置中心 gcheck/ 文件夹下的 ossfuzz_main_repos.txt；'
                             '都没有则名单比对为"不确定 miss"（detail.ossfuzz_uncertain=true）')
    parser.add_argument('--gcheck-timeout', type=int, default=DEFAULT_GCHECK_TIMEOUT,
                        help=f'单仓 gcheck 超时秒数（默认 {DEFAULT_GCHECK_TIMEOUT}，超时该仓三指标全 NA；'
                             f'传 0 = 不设超时，等 gcheck 自然跑完）')
    parser.add_argument('--max-detail-paths', type=int, default=MAX_DETAIL_PATHS,
                        help='detail_json 路径数组截断上限')
    return parser.parse_args()


def get_dolphinscheduler_params():
    """Doris 凭证（DS 内联任务执行前对脚本文本做全局替换）。

    2026-10-23 起对齐 docs/0912/参考/示例解密的任务.py 的加密模式：
    url 明文占位符；账号/密码改为 *_crypto 加密占位符（DS 侧配密文），
    运行时经 decrypt-tool.jar --salt ${salt} 解出明文（decrypt_token）。
    """
    return (
        '${openlibing_doris_url}',
        '${openlibing_doris_username_crypto}',
        '${openlibing_doris_password_crypto}',
    )


# =====================================================================
# 凭证解密层（与 docs/0912/参考/示例解密的任务.py 同模式：decrypt-tool.jar + salt）
# =====================================================================

# salt 由 DS 占位符注入（与既有 *_crypto 凭证同一把 salt）
DS_SALT = '${salt}'

# decrypt-tool.jar 落位：配置中心 utils/decrypt-tool.jar 资源引用模式
# （与示例解密任务一致：随任务下发到 <脚本目录>/utils/decrypt-tool.jar）
DECRYPT_JAR = os.path.join(SCRIPT_DIR, 'utils', 'decrypt-tool.jar')

# openUBMC conan 凭证（2026-10-23 拍板）：
#   - 用户名非敏感，明文内置常量（本地调试可用 --conan-user 覆盖）
#   - 密码走 DS 加密占位符 ${openubmc_conan_psw_crypto}（密文，decrypt-tool.jar 解密）
OPENUBMC_CONAN_USER = 'openLiBing-ops'
DS_OPENUBMC_CONAN_PSW = '${openubmc_conan_psw_crypto}'

# 解密结果缓存（密文 -> 明文，避免重复起 java 进程）
_decrypt_cache = {}


def _is_unreplaced_placeholder(value):
    """本地裸跑时 DS 占位符未被替换（仍以 ${ 开头）→ 视为"未配置"。"""
    return isinstance(value, str) and value.startswith('${')


def decrypt_token(cipher):
    """调用 decrypt-tool.jar 解密（明文=stdout 末行；失败返回空串，缓存结果）。

    与 示例解密的任务.py 的 decrypt_token 逐行同构（精确复制参考实现）；
    2026-10-23 增强：失败时输出环境自检（jar/java/salt）与命令输出尾段，便于 DS 排障。
    """
    if not cipher:
        return ''
    if cipher in _decrypt_cache:
        return _decrypt_cache[cipher]
    if not os.path.isfile(DECRYPT_JAR):
        print(f"Decrypt failed: decrypt-tool.jar not found: {DECRYPT_JAR} "
              f"(DS 任务需上传 utils/decrypt-tool.jar 资源)", flush=True)
        _decrypt_cache[cipher] = ''
        return ''
    import shutil
    if not shutil.which('java'):
        print("Decrypt failed: java not found in PATH (worker 需安装 java)", flush=True)
        _decrypt_cache[cipher] = ''
        return ''
    if _is_unreplaced_placeholder(DS_SALT):
        print("Decrypt failed: ${salt} placeholder unreplaced "
              "(DS 任务参数未配置 salt)", flush=True)
        _decrypt_cache[cipher] = ''
        return ''
    cmd = ['java', '-jar', DECRYPT_JAR, '--salt', DS_SALT, cipher]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        output = (result.stdout or '') + (result.stderr or '')
        lines = output.strip().split('\n')
        plain = lines[-1] if lines else ''
        if (not plain or 'Exception' in output or 'Error' in output
                or result.returncode != 0):
            print(f"Decrypt failed returncode={result.returncode} "
                  f"output_tail={(output or '')[-300:]!r}", flush=True)
            plain = ''
    except Exception as e:
        print(f"Decrypt failed error={e}", flush=True)
        plain = ''
    _decrypt_cache[cipher] = plain
    return plain


def resolve_credential(raw_value, cli_value, name, decrypt=True):
    """凭证解析统一入口（优先级：CLI 明文 > DS 占位符）。

    - CLI 传了明文（本地调试）→ 原样使用，不走解密；
    - DS 占位符已被替换为密文 → decrypt_token 解出明文；
    - 仍是 '${...'（本地裸跑未替换）或解密失败 → 报错退出（凭证缺失不能静默继续）。
    """
    if cli_value:
        return cli_value
    if _is_unreplaced_placeholder(raw_value):
        print(f"ERROR: credential '{name}' not configured: DS placeholder "
              f"unreplaced and no CLI fallback provided.", flush=True)
        sys.exit(1)
    if not decrypt:
        return raw_value
    plain = decrypt_token(raw_value)
    if not plain:
        print(f"ERROR: credential '{name}' decrypt failed "
              f"(check java / {DECRYPT_JAR} / salt)", flush=True)
        sys.exit(1)
    return plain


def _ensure_gcheck_src():
    """DS 资源中心只支持单文件上传 → gcheck 源码以 gcheck-src.tar.gz 随任务下发，
    运行时自动解压（幂等：目录已存在直接用，不存在且有 tar 才解压）。

    - tar 位置两种落位都支持：配置中心 gcheck/ 文件夹下（同 utils/decrypt-tool.jar
      模式）→ <脚本目录>/gcheck/gcheck-src.tar.gz；或与脚本同目录
    - 目标布局：<脚本目录>/gcheck/src/gcheck/...（tar 根目录为 src/，
      打包：tar -czf gcheck-src.tar.gz --exclude __pycache__ -C <gcheck仓>/gcheck src）
    - DS 任务工作目录若每次执行都重新物化，则每次解压一次（tar ~67KB，秒级，可忽略）
    - 返回 gcheck-src 路径；既无目录又无 tar（本地开发场景）返回 None
    """
    ds_path = os.path.join(SCRIPT_DIR, 'gcheck', 'src')
    if os.path.isdir(os.path.join(ds_path, 'gcheck')):
        return ds_path
    tgz = None
    for cand in (os.path.join(SCRIPT_DIR, 'gcheck', 'gcheck-src.tar.gz'),  # 配置中心 gcheck/ 文件夹
                 os.path.join(SCRIPT_DIR, 'gcheck-src.tar.gz')):          # 与脚本同目录
        if os.path.isfile(cand):
            tgz = cand
            break
    if tgz is None:
        return None
    print(f"unpacking gcheck source: {tgz} -> {os.path.join(SCRIPT_DIR, 'gcheck')}")
    dest = os.path.join(SCRIPT_DIR, 'gcheck')
    os.makedirs(dest, exist_ok=True)
    import tarfile
    with tarfile.open(tgz, 'r:gz') as tf:
        try:
            tf.extractall(dest, filter='data')
        except TypeError:  # Python < 3.11.4 无 filter 参数
            tf.extractall(dest)
    if not os.path.isdir(os.path.join(ds_path, 'gcheck')):
        raise RuntimeError(
            f'gcheck-src.tar.gz 解压后未找到 gcheck 包：期望 {ds_path}/gcheck '
            f'（tar 根目录应为 src/，即解压到 <脚本目录>/gcheck/ 下形成 gcheck/src/gcheck/）')
    print(f"gcheck source ready: {ds_path}")
    return ds_path


def resolve_deploy_paths(args):
    """部署三件套路径智能解析（优先级：显式 CLI 参数 > 生产目录 > 本地开发目录）。

    1. gcheck 源码：DS 配置中心传单文件 gcheck-src.tar.gz（_deploy_gcheck 产出），
       与脚本同目录落地，运行时自动解压到 <脚本目录>/gcheck/src（_ensure_gcheck_src）；
       本地开发回退 <脚本目录>/参考/gcheck/gcheck/src
    2. scorecard 二进制：生产 = install_scorecard.sh 产出；本地 = _test_gcheck/scorecard.exe
    3. OSS-Fuzz 名单：生产 = update_ossfuzz_snapshot.sh 产出的文本表；
       不存在则保持 None（fuzzing 名单比对为"不确定 miss"，不阻断打分）
    """
    if not args.gcheck_src:
        ds_path = _ensure_gcheck_src()
        dev_path = os.path.join(SCRIPT_DIR, '参考', 'gcheck', 'gcheck', 'src')
        args.gcheck_src = ds_path if ds_path else dev_path
    if not args.scorecard_bin:
        if os.path.isfile(PROD_SCORECARD_BIN):
            args.scorecard_bin = PROD_SCORECARD_BIN
        elif os.path.isfile(os.path.join(SCRIPT_DIR, 'gcheck', 'scorecard')):
            # 配置中心 gcheck/ 文件夹模式：scorecard 二进制随任务下发
            args.scorecard_bin = os.path.join(SCRIPT_DIR, 'gcheck', 'scorecard')
        else:
            args.scorecard_bin = os.path.join(SCRIPT_DIR, '_test_gcheck', 'scorecard.exe')
    # DS 配置中心下发的文件不保留可执行权限，Linux 上自动补 chmod +x
    if (os.name == 'posix' and args.scorecard_bin
            and os.path.isfile(args.scorecard_bin)
            and not os.access(args.scorecard_bin, os.X_OK)):
        os.chmod(args.scorecard_bin, 0o755)
        print(f"chmod +x {args.scorecard_bin}")
    if not args.ossfuzz_status:
        if os.path.isfile(PROD_OSSFUZZ_TXT):
            args.ossfuzz_status = PROD_OSSFUZZ_TXT
        else:
            # 配置中心单文件上传模式：ossfuzz_main_repos.txt 落在 gcheck/ 文件夹下
            # （同 utils/decrypt-tool.jar 模式），或与脚本同目录
            for rc_txt in (os.path.join(SCRIPT_DIR, 'gcheck', 'ossfuzz_main_repos.txt'),
                           os.path.join(SCRIPT_DIR, 'ossfuzz_main_repos.txt')):
                if os.path.isfile(rc_txt):
                    args.ossfuzz_status = rc_txt
                    break
    return args


# =====================================================================
# Doris 工具（照抄 security_file_scan.py，口径一致）
# =====================================================================

def parse_doris_url(doris_url):
    """jdbc:mysql://host:port/db -> (host, port, db)，与 commit 扫描脚本同款解析。"""
    if not doris_url or not doris_url.startswith('jdbc:mysql://'):
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    url_part = doris_url[len('jdbc:mysql://'):]
    m = __import__('re').search(r'[^/]+/([^?]+)', url_part)
    if not m:
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    db_database = m.group(1)
    hosts_ports_part = url_part.split('/')[0]
    if not hosts_ports_part:
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    first_host_port = hosts_ports_part.split(',')[0].strip()
    hm = __import__('re').match(r'([^:]+):(\d+)', first_host_port)
    if not hm:
        raise ValueError(f"Invalid host:port format: {doris_url}")
    return hm.group(1), int(hm.group(2)), db_database


def get_db_connection(doris_url, doris_username, doris_password):
    db_host, db_port, db_database = parse_doris_url(doris_url)
    connection = pymysql.connect(
        host=db_host, port=db_port, user=doris_username, password=doris_password,
        database=db_database, cursorclass=pymysql.cursors.DictCursor
    )
    print(f"Connected to database: {db_host}:{db_port}/{db_database}")
    return connection


def load_repo_list(connection, repo_id_filter=None):
    """扫描范围：sdi_rd_efc_repo_operate_conf 且 is_operate=1、platform='gitcode'
    （design.md §3，与 security_file_scan.py 完全同口径）。
    返回行含 repo_id / repo_url / platform / default_branch。"""
    sql = ("SELECT sri.repo_id, sri.repo_url, sri.platform, "
           "ls.branch_name AS default_branch "
           "FROM sdi_repo_info sri "
           "LEFT JOIN (SELECT repo_id, name AS branch_name FROM sdi_repo_branch_info "
           "            WHERE default_branch = true) ls "
           "       ON CAST(sri.repo_id AS VARCHAR) = ls.repo_id "
           "WHERE sri.platform = 'gitcode' "
           "  AND sri.repo_id IN "
           "      (SELECT repo_id FROM sdi_rd_efc_repo_operate_conf WHERE is_operate = 1)")
    params = []
    if repo_id_filter:
        sql += " AND sri.repo_id IN (%s)" % ','.join(['%s'] * len(repo_id_filter))
        params = list(repo_id_filter)
    sql += " ORDER BY sri.repo_id"
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    no_branch_count = 0
    for r in rows:
        if not r.get('default_branch'):
            no_branch_count += 1
    print(f"Loaded {len(rows)} repos (is_operate=1, platform=gitcode), "
          f"{no_branch_count} without default_branch (will be NA)")
    return rows


def insert_metric_rows(rows, connection):
    """按 UNIQUE KEY (repo_id, metric_code, scan_time) 写入，Doris Unique 模型自动覆盖（幂等）。
    失败重试 1 次，仍失败抛出由单仓异常兜底（不中断整体批次）。"""
    if not rows:
        return 0
    sql = (f"INSERT INTO {TARGET_TABLE} "
           "(repo_id, metric_code, scan_time, repo_url, detail_json, score, is_na, etl_time) "
           "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
    last_err = None
    for attempt in (1, 2):
        try:
            batch = [(r['repo_id'], r['metric_code'], r['scan_time'], r['repo_url'],
                      r['detail_json'], r['score'], r['is_na'], r['etl_time']) for r in rows]
            with connection.cursor() as cursor:
                cursor.executemany(sql, batch)
            connection.commit()
            return len(batch)
        except Exception as e:
            last_err = e
            try:
                connection.rollback()
            except Exception:
                pass
            print(f"  insert attempt {attempt} failed: {e}", flush=True)
    raise last_err


def insert_pinned_dep_rows(repo_id, scan_time, etl_time, dep_rows, connection):
    """依赖锁定全量明细写入 dwi_rd_efc_security_pinned_dep_detail（一行一个依赖条目）。

    - dep_rows 来自 score_pinned_deps 的 detail['_dep_rows']：(dep_id, dep_type, file_path,
      line, dep_ref, pinned, signal, reason) 元组列表，全量不截断（已固定 + 未固定）；
    - UNIQUE KEY (repo_id, scan_time, dep_id)，同批次重跑幂等覆盖；
    - 失败重试 1 次，仍失败抛出由单仓异常兜底（不中断整体批次）。
    """
    if not dep_rows:
        return 0
    sql = (f"INSERT INTO {PINNED_DEP_DETAIL_TABLE} "
           "(repo_id, scan_time, dep_id, dep_type, file_path, line, dep_ref, "
           "pinned, signal, reason, etl_time) "
           "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    last_err = None
    for attempt in (1, 2):
        try:
            batch = [(repo_id, scan_time, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
                      etl_time) for r in dep_rows]
            with connection.cursor() as cursor:
                cursor.executemany(sql, batch)
            connection.commit()
            return len(batch)
        except Exception as e:
            last_err = e
            try:
                connection.rollback()
            except Exception:
                pass
            print(f"  pinned_dep_detail insert attempt {attempt} failed: {e}", flush=True)
    raise last_err


# =====================================================================
# git 工具（照抄 security_file_scan.py：本地仓复用模式，不 clone 仅 checkout）
# =====================================================================

def get_platform_from_url(repo_url):
    """从 URL 提取平台名（gitcode/github/gitee/gitlab/bitbucket）。"""
    try:
        url = repo_url
        if '://' in url:
            url = url.split('://', 1)[1]
        if '@' in url:
            url = url.split('@', 1)[1]
        host = url.split('/')[0].lower()
        if ':' in host:
            host = host.split(':')[0]
        if 'gitcode' in host:
            return 'gitcode'
        if 'github' in host:
            return 'github'
        if 'gitee' in host:
            return 'gitee'
        if 'gitlab' in host:
            return 'gitlab'
        if 'bitbucket' in host:
            return 'bitbucket'
        return host or 'unknown'
    except Exception as e:
        print(f"Error extracting platform from URL {repo_url}: {e}")
        return 'unknown'


def parse_repo_identity(repo_url):
    """从 URL 解析 (owner, repo_name)；repo_name 为末段（去 .git）。"""
    try:
        url = repo_url
        if '://' in url:
            url = url.split('://', 1)[1]
        if '@' in url:
            url = url.split('@', 1)[1]
        if url.endswith('.git'):
            url = url[:-4]
        parts = [p for p in url.split('/') if p]
        if len(parts) < 2:
            return 'unknown', (parts[0] if parts else 'unknown')
        repo_name = parts[-1]
        owner_parts = parts[1:-1]
        owner = '/'.join(owner_parts) if owner_parts else 'unknown'
        return owner, repo_name
    except Exception as e:
        print(f"Error parsing repo identity from URL {repo_url}: {e}")
        return 'unknown', 'unknown'


def build_repo_path(base_dir, repo_url):
    """构建本地仓库路径：{base_dir}/{platform}/{owner}/{repo_name}
    与处理脚本.python 完全一致（信任处理脚本已拉最新，本脚本仅 checkout）。"""
    platform = get_platform_from_url(repo_url)
    owner, repo_name = parse_repo_identity(repo_url)
    return os.path.join(base_dir, platform, owner, repo_name)


def checkout_branch(repo_path, branch_name):
    """本地 checkout 指定分支（不 fetch，信任处理脚本已拉最新）。
    已在目标分支时跳过 checkout（零成本，避免对大仓重复 git checkout）；
    -c safe.directory=* 跳过 dubious ownership 检查。"""
    git_safe_args = ['-c', 'safe.directory=*']
    # 短路：当前已在目标分支则不执行 checkout
    try:
        cur = subprocess.run(
            ['git', *git_safe_args, '-C', repo_path, 'branch', '--show-current'],
            capture_output=True, text=True, check=True
        )
        if cur.stdout.strip() == branch_name:
            return True
    except Exception:
        pass  # 检测失败则走正常 checkout 兜底
    try:
        subprocess.run(
            ['git', *git_safe_args, '-C', repo_path, 'checkout', branch_name],
            capture_output=True, text=True, check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        if "could be both a local file and a tracking branch" in (e.stderr or ''):
            try:
                subprocess.run(
                    ['git', *git_safe_args, '-C', repo_path, 'checkout', '--', branch_name],
                    capture_output=True, text=True, check=True
                )
                return True
            except subprocess.CalledProcessError:
                return False
        return False


# =====================================================================
# gcheck 调用层
# =====================================================================

def run_gcheck(repo_dir, repo_url, args):
    """单仓一次 subprocess 跑 3 个 check，返回 (exit_code, parsed_json, stderr_tail, timed_out)。

    - 输出走临时文件（--output），避免 stdout 混入日志污染 JSON；
    - env PYTHONPATH 前插 gcheck 源码目录（python -m gcheck 需要）；
    - Windows（os.name == 'nt'）自动追加 --allow-unsupported-platform
      （gcheck 默认拒绝非 Linux；生产 DS 为 Linux 不加）；
    - JSON 解析失败不抛异常，返回 (rc, None, ...) 由上层按 NA 处理。
    """
    cmd = [sys.executable, '-m', 'gcheck', 'run']
    for check in GCHECK_CHECKS:
        cmd += ['--check', check]
    cmd += ['--path', repo_dir,
            '--offline',
            '--repo-uri', repo_url,
            '--scorecard-bin', args.scorecard_bin,
            '--format', 'json']
    if args.ossfuzz_status:
        cmd += ['--ossfuzz-status', args.ossfuzz_status]
    if os.name == 'nt':
        cmd.append('--allow-unsupported-platform')

    out_fd, out_path = tempfile.mkstemp(prefix='gcheck_', suffix='.json')
    os.close(out_fd)
    cmd += ['--output', out_path]

    env = dict(os.environ)
    gcheck_src = os.path.abspath(args.gcheck_src)
    if not os.path.isdir(os.path.join(gcheck_src, 'gcheck')):
        # 目录里没有 gcheck 包，大概率路径给错；提前报清楚而不是让 subprocess 报模糊错误
        return 1, None, f'gcheck source not found: {gcheck_src} (expect <gcheck-src>/gcheck/)', False
    old_pp = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = gcheck_src + (os.pathsep + old_pp if old_pp else '')

    timed_out = False
    stderr_tail = ''
    # --gcheck-timeout 0 = 不设超时（subprocess timeout=None），等 gcheck 自然跑完
    sub_timeout = args.gcheck_timeout if args.gcheck_timeout > 0 else None
    try:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=sub_timeout, env=env)
            rc = proc.returncode
            stderr_tail = (proc.stderr or '')[-500:]
        except subprocess.TimeoutExpired:
            timed_out = True
            rc = None
            stderr_tail = f'gcheck timeout after {args.gcheck_timeout}s'

        doc = None
        if not timed_out and os.path.isfile(out_path):
            try:
                with open(out_path, 'r', encoding='utf-8') as f:
                    doc = json.load(f)
            except (ValueError, OSError) as e:
                stderr_tail = f'gcheck output parse failed: {e}'
        return rc, doc, stderr_tail, timed_out
    finally:
        try:
            os.remove(out_path)
        except OSError:
            pass


# =====================================================================
# 解析与打分层（口径源：gcheck-integration-handover.md §五）
# =====================================================================

def _find_check(doc, check_name):
    """从 gcheck 输出 doc['checks'] 里找指定 check，找不到返回 None。"""
    for check in (doc.get('checks') or []):
        if check.get('check') == check_name:
            return check
    return None


def _na_result(reason, message):
    """NA 行三元组：score NULL + is_na=1 + 带 reason 的 detail（与主脚本三态 NA 同构）。"""
    return None, 1, {'reason': reason, 'message': message}


def _check_status_na(check):
    """check 级状态兜底：error/inconclusive → NA（"没看成"≠"没问题"）。
    返回 (reason, message) 或 None（状态正常）。
    注意：gcheck diagnostics.errors 的元素是 {scope, message} 字典（与 gcheck
    render.py 取 error.get('scope')/error.get('message') 同构），不是纯字符串。
    2026-10-13 修复：此前按纯字符串 join，遇 dict 抛 TypeError 导致整仓 FAIL
    （exit=3 分 check 落分路径首次触达该结构）。"""
    status = check.get('status')
    if status in ('error', 'inconclusive'):
        diag = check.get('diagnostics') or {}
        parts = []
        for e in (diag.get('errors') or [])[:3]:
            if isinstance(e, dict):
                parts.append(f"{e.get('scope') or check.get('check') or 'check'}: "
                             f"{e.get('message') or '原因未知'}")
            else:
                parts.append(str(e))
        msg = f'gcheck status={status}' + (f': {"; ".join(parts)}' if parts else '')
        return f'gcheck_{status}', msg
    return None


def _unavailable_criteria(check):
    """列出 unavailable（没看成）的判据 id，供 detail 记录；其 counts 不进分子分母。"""
    return [c.get('id') for c in (check.get('checklist') or [])
            if c.get('status') == 'unavailable']


def _check_warnings(check):
    return ((check.get('diagnostics') or {}).get('warnings') or [])


def score_pinned_deps(check, max_paths):
    """指标5 PINNED_DEP：score = compliant / (compliant + nonCompliant) × 10（严格口径）。

    - not-applicable（无依赖）→ NA；
    - 分母 = summary.compliant + summary.nonCompliant（**不拿判据计数之和**：
      id=null 的 error 条目不归任何判据，notSupported/error 不进分子分母）；
    - deps 明细数组截断 max_paths，计数仍是全量；
    - signal 标注无修复路径的条目（stageAlias / variableRef / noRef），明细页可据此
      标注"口径问题，无需整改"（gcheck 手册：不要为这类条目开整改单）。
    """
    na = _check_status_na(check)
    if na:
        return _na_result(*na)
    status = check.get('status')
    if status == 'not-applicable':
        return _na_result('not_applicable', 'gcheck status=not-applicable（未识别到任何依赖）')

    summary = check.get('summary') or {}
    compliant = int(summary.get('compliant') or 0)
    non_compliant = int(summary.get('nonCompliant') or 0)
    denominator = compliant + non_compliant
    if denominator == 0:
        return _na_result('empty_result',
                          f'gcheck summary 无可用条目（compliant={compliant}, '
                          f'nonCompliant={non_compliant}, status={status}）')

    score = round(compliant / denominator * 10, 2)
    items = check.get('items') or []
    deps = []
    dep_rows = []   # 全量明细行（写 dwi_rd_efc_security_pinned_dep_detail，不截断）
    for idx, it in enumerate(items):
        verdict = it.get('verdict')
        if idx < max_paths:  # detail_json 的 deps 保持截断（渲染契约不变）
            deps.append({
                'type': it.get('id'),            # 判据：containerImage/pipCommand/...
                'file': it.get('path'),
                'line': it.get('lineStart'),
                'ref': it.get('snippet'),       # 源文件真实那一行
                'pinned': True if verdict == 'compliant' else (False if verdict == 'nonCompliant' else None),
                'signal': it.get('signal'),     # mutableTag/stageAlias/variableRef/localPath/...
                'reason': it.get('detail'),     # gcheck 自带整改路径文案
            })
        dep_rows.append((
            idx,                                          # dep_id：items 数组下标，批内唯一
            it.get('id') or 'unknown',                     # dep_type
            it.get('path'),                                # file_path
            it.get('lineStart'),                           # line
            it.get('snippet'),                             # dep_ref
            1 if verdict == 'compliant' else (0 if verdict == 'nonCompliant' else None),
            it.get('signal'),                              # signal（仅镜像类条目有值）
            it.get('detail'),                              # reason
        ))
    detail = {
        'pinned_count': compliant,
        'total_count': denominator,
        'deps': deps,
        'truncated': len(items) > max_paths,
        'unavailable_criteria': _unavailable_criteria(check),
        'warnings': _check_warnings(check),
        # 全量明细行：主流程写完 dwi_rd_efc_security_pinned_dep_detail 后 pop 掉，
        # 不进 detail_json（detail_json 的 deps 保持截断，卡片区照旧渲染）
        '_dep_rows': dep_rows,
    }
    return score, 0, detail


def score_fuzzing(check, max_paths):
    """指标13 FUZZING：阶梯取最高档（design.md §5.13 阶梯扩展：property-testing=3）。

    ossFuzz/ClusterFuzzLite 命中=10；原生 fuzz 函数=5；property-testing=3；全 miss=0。
    "未检测到任何 fuzz 集成"是 id=null/scope=repo 的仓库级条目 → 0 分（有效得分，非 NA）。
    ossFuzz miss 的确定性与否见 detail.ossfuzz_uncertain（不影响打分，只做标注）。
    """
    na = _check_status_na(check)
    if na:
        return _na_result(*na)

    checklist = {c.get('id'): c.get('status') for c in (check.get('checklist') or [])}

    def hit(cid):
        return checklist.get(cid) == 'hit'

    in_ossfuzz = hit('ossFuzz')
    has_cflite = hit('clusterFuzzLite')
    native_hit = [cid for cid in FUZZ_TIER5_NATIVE if hit(cid)]
    property_hit = [cid for cid in FUZZ_TIER3_PROPERTY if hit(cid)]

    if in_ossfuzz:
        score, tier = 10, 'oss_fuzz'
    elif has_cflite:
        score, tier = 10, 'clusterfuzzlite'
    elif native_hit:
        score, tier = 5, 'native_fuzz'
    elif property_hit:
        score, tier = 3, 'property_testing'
    else:
        score, tier = 0, 'none'

    # ossFuzz 名单比对确定性：inputs.ossfuzz 非空=比对过（确定 miss）；
    # warnings 含"未做名单比对"=没能比对（不确定，仅标注，不改变打分）
    inputs = check.get('inputs') or {}
    ossfuzz_compared = bool(inputs.get('ossfuzz'))
    warnings = _check_warnings(check)
    ossfuzz_uncertain = (not in_ossfuzz) and (not ossfuzz_compared) and any(
        '未做名单比对' in w for w in warnings)

    # 命中证据（items 里 verdict=compliant 的条目；仓库级 id=null 结论条目不进 signals）
    signals = []
    for it in (check.get('items') or []):
        if it.get('verdict') != 'compliant':
            continue
        if len(signals) >= max_paths:
            break
        signals.append({
            'criterion': it.get('id'),
            'tool': None,  # checklist[].tool 为上游常量名，证据行不重复展开
            'file': it.get('path'),
            'line': it.get('lineStart'),
            'snippet': it.get('snippet'),
        })

    detail = {
        'in_ossfuzz': bool(in_ossfuzz),
        'ossfuzz_project': None,
        'ossfuzz_compared': ossfuzz_compared,
        'ossfuzz_uncertain': ossfuzz_uncertain,
        'has_clusterfuzzlite': bool(has_cflite),
        'native_fuzz': bool(native_hit),
        'tier': tier,
        'hit_criteria': [cid for cid in checklist if checklist[cid] == 'hit'],
        'signals': signals,
        'unavailable_criteria': _unavailable_criteria(check),
        'warnings': warnings,
    }
    return score, 0, detail


def score_binary_artifacts(check, max_paths):
    """指标6 BINARY_ARTIFACTS（口径切换 2026-10-08）：按文件内容魔数识别真可执行产物。

    score = max(0, 10 − nonCompliant 数)；clean（仓库级 compliant 条目）= 10；无 NA。
    .gz/.zip/.pdf/.jar/.pyc 等不再上报（后缀清单口径作废）；
    vendor/node_modules 照报（上游口径，与 Dockerfile 排除规则不同）；
    上游不给 snippet，用 signal 区分产物类型（elf/pe/macho/wasm/archive/other）。
    """
    na = _check_status_na(check)
    if na:
        return _na_result(*na)

    items = check.get('items') or []
    bad_items = [it for it in items if it.get('verdict') == 'nonCompliant']
    binary_count = len(bad_items)
    score = round(max(0.0, 10.0 - binary_count), 2)

    bad_file_paths = [it.get('path') for it in bad_items[:max_paths]]
    artifact_types = [{'path': it.get('path'), 'signal': it.get('signal')}
                      for it in bad_items[:max_paths]]
    detail = {
        'binary_count': binary_count,
        'bad_file_paths': bad_file_paths,
        'artifact_types': artifact_types,
        'truncated': binary_count > max_paths,
        'unavailable_criteria': _unavailable_criteria(check),
        'warnings': _check_warnings(check),
    }
    return score, 0, detail


# 指标打分分派表（check 名 -> 打分函数）
SCORE_FUNCS = {
    'pinned-deps': score_pinned_deps,
    'fuzzing': score_fuzzing,
    'binary-artifacts': score_binary_artifacts,
}


# =====================================================================
# 单仓编排
# =====================================================================

def build_na_results(reason, message):
    """三态异常（无默认分支/本地目录不存在/checkout 失败/gcheck 级故障）时构造
    3 指标全 NA 结果。score NULL + is_na=1 照常写库，detail 记录原因便于排查。"""
    detail = {'reason': reason, 'message': message}
    return {code: (None, 1, dict(detail)) for code in METRIC_CHECK_MAP}


def scan_one_repo(repo, repo_dir, args):
    """单仓 gcheck 扫描，返回 metric_code -> (score, is_na, detail) 字典。

    gcheck 级故障均写 NA 行不丢仓（与主脚本三态异常同口径）：
      - 超时（--gcheck-timeout）→ reason=gcheck_timeout
      - 退出码 1（用法错误，多为环境/参数问题）→ reason=gcheck_usage_error
      - 输出缺失/JSON 解析失败 → reason=gcheck_no_output / gcheck_bad_output
      - 退出码 3（inconclusive：部分分片/CI 源没扫成）→ 按各 check 自身 status 分别落分
        （2026-10-12 修正，原为整仓三指标 NA）：status=inconclusive/error 的 check 落 NA
        （reason=gcheck_inconclusive/gcheck_error）；findings/clean/not-applicable 等确定
        结论照常打分，detail.warnings 标注"批次含未扫成来源"便于审计；
        JSON 不可解析时才整仓 NA，reason=gcheck_inconclusive
      - 输出里缺某 check → 该指标 NA，reason=gcheck_check_missing
    check 级 status=error/inconclusive 由各打分函数自行落 NA。
    """
    rc, doc, err_tail, timed_out = run_gcheck(repo_dir, repo['repo_url'], args)

    if timed_out:
        return build_na_results('gcheck_timeout', err_tail)
    if rc == 1:
        return build_na_results('gcheck_usage_error', err_tail)
    if rc == 3 and doc is None:
        # 退出码 3 且输出不可解析：无法区分哪些 check 有结论，保守整仓 NA
        return build_na_results(
            'gcheck_inconclusive',
            f'gcheck exit=3 (some shards/CI sources not scanned): {err_tail}')
    if doc is None:
        reason = 'gcheck_no_output' if rc in (None, '') else 'gcheck_bad_output'
        return build_na_results(reason, f'gcheck exit={rc}: {err_tail}')

    results = {}
    for metric_code, check_name in METRIC_CHECK_MAP.items():
        check = _find_check(doc, check_name)
        if check is None:
            results[metric_code] = _na_result(
                'gcheck_check_missing', f'gcheck output has no check: {check_name}')
        else:
            results[metric_code] = SCORE_FUNCS[check_name](check, args.max_detail_paths)
    if rc == 3:
        # 退出码 3 但输出可解析：各 check 已按自身 status 分别落分（inconclusive/error
        # 的 check 已落 NA）。有确定结论的指标照常打分，仅在 detail.warnings 标注
        # 批次含未扫成来源（审计可追溯该批次口径）。
        for _score, _is_na, detail in results.values():
            if not _is_na and isinstance(detail, dict):
                detail.setdefault('warnings', []).append(
                    'gcheck exit=3: 部分分片/CI 来源未扫成，本 check 结论自身完整')
    return results


def resolve_optional_credential(raw_value, cli_value, name):
    """可选凭证解析（openUBMC conan 用）：CLI 明文优先；DS 占位符未替换 → None
    （不退出，仅该社区指标落 NA）；密文解密失败 → None + 告警。"""
    if cli_value:
        return cli_value
    if _is_unreplaced_placeholder(raw_value):
        return None
    plain = decrypt_token(raw_value)
    if not plain:
        print(f"WARN: credential '{name}' decrypt failed "
              f"(check java / {DECRYPT_JAR} / salt)", flush=True)
    return plain or None


# =====================================================================
# openUBMC 社区特判（PINNED_DEP 走 conan/manifest 口径，gcheck 主流程不感知）
#
# 背景：gcheck 不识别 conan 生态，openUBMC 社区 10 仓 pinned-deps 恒 NA。
# 口径（2026-10-23 拍板）：扫 openUBMC/manifest 仓（依赖聚合点），组件是否被
# build/openubmc.lock / build/sdk/openubmc_sdk.lock 固化；组件→代码仓映射靠
# conan download --only-recipe 拿 conandata.yml 的 sources.url（权威证据）。
# 打分按组件判定：组件被固化=10、未固化=0；未被 manifest 依赖=NA(no_dependency)。
# =====================================================================

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _yaml = None
    _HAS_YAML = False

# openUBMC 社区归属：sdi_repo_info 无 community 列，经 project_id 关联社区配置表
OPENUBMC_COMMUNITY_NAME = 'openUBMC'
# manifest 仓不在预 clone 清单（openUBMC/manifest 不在 is_operate=1 评估范围），自主浅克隆
OPENUBMC_MANIFEST_URL = 'https://gitcode.com/openUBMC/manifest.git'
OPENUBMC_MANIFEST_DIR = os.path.join(SCRIPT_DIR, '_openubmc_manifest')
# conan 私服（openUBMC 社区自建，强制社区账号认证，自签证书需 --insecure）
CONAN_REMOTE_NAME = 'openubmc_opensource'
CONAN_REMOTE_URL = 'https://conan.openubmc.cn/openubmc_opensource'
CONAN_HOME = os.path.join(SCRIPT_DIR, 'conan_home')
# conan 2 环境变量认证（remote 名大写化；避免密码上命令行/进程列表）
_CONAN_LOGIN_ENV_USER = 'CONAN_LOGIN_USERNAME_' + CONAN_REMOTE_NAME.upper()
_CONAN_LOGIN_ENV_PSW = 'CONAN_PASSWORD_' + CONAN_REMOTE_NAME.upper()


def load_openubmc_repo_ids(connection):
    """openUBMC 社区评估仓集合（独立查询，不碰 load_repo_list）。

    已实测精确圈出 10 个仓（webui/devmon/libmcpp/component_drivers/dcmid/
    libroute_mapper/bcal/sensor_mgmt/event_mgmt/ipmi_mgmt），集合与其他社区不相交，
    非 openUBMC 批次此钩子零触发。
    """
    sql = ("SELECT sri.repo_id FROM sdi_repo_info sri "
           "JOIN dm_rd_efc_security_community_conf c "
           "  ON sri.project_id = c.project_id "
           "WHERE c.community_name = %s AND sri.platform = 'gitcode'")
    with connection.cursor() as cursor:
        cursor.execute(sql, (OPENUBMC_COMMUNITY_NAME,))
        ids = {r['repo_id'] for r in cursor.fetchall()}
    print(f"openUBMC community repos: {sorted(ids)}")
    return ids


def _conan_env(conan_user, conan_psw):
    """conan 子进程环境：隔离 CONAN_HOME + 环境变量认证（密码不落命令行）。"""
    env = dict(os.environ)
    env['CONAN_HOME'] = CONAN_HOME
    if conan_user:
        env[_CONAN_LOGIN_ENV_USER] = conan_user
    if conan_psw:
        env[_CONAN_LOGIN_ENV_PSW] = conan_psw
    return env


def _run_cmd(cmd, env=None, timeout=300):
    """subprocess 封装：返回 (ok, stdout, stderr)。

    OSError 兜底（FileNotFoundError/NotADirectoryError/PermissionError）：
    worker PATH 里有非目录条目时 exec 报 Errno 20，不能让它 FATAL 掉整个批次
    （2026-10-24 DS 实测：conan 未装 + PATH 坏条目 → NotADirectoryError 逃逸）。
    """
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, env=env)
        return proc.returncode == 0, proc.stdout or '', proc.stderr or ''
    except subprocess.TimeoutExpired:
        return False, '', f'timeout after {timeout}s: {" ".join(cmd[:3])}'
    except OSError as e:
        return False, '', f'cannot execute {cmd[0] if cmd else "?"}: {e}'


def _ensure_conan_remote(conan_user, conan_psw):
    """conan CLI 可用性检查 + remote 配置（幂等 --force 覆盖）。"""
    ok, out, err = _run_cmd(['conan', '--version'])
    if not ok:
        return False, (f'conan CLI not available: {err or out} '
                       f'(worker 需 pip3 install conan 且 PATH 正常)').strip()
    ok, out, err = _run_cmd(
        ['conan', 'remote', 'add', CONAN_REMOTE_NAME, CONAN_REMOTE_URL,
         '--insecure', '--force'], env=_conan_env(conan_user, conan_psw))
    if not ok:
        return False, f'conan remote add failed: {err or out}'.strip()
    return True, ''


def _clone_manifest_repo():
    """浅克隆/更新 openUBMC/manifest 仓（幂等）。fetch 失败不静默降级（教训见 ai_memory）。

    用远端默认分支（main，实测 main 上两个 lock 文件均在）。
    """
    if os.path.isdir(os.path.join(OPENUBMC_MANIFEST_DIR, '.git')):
        ok, out, err = _run_cmd(
            ['git', '-C', OPENUBMC_MANIFEST_DIR, 'fetch', '--depth', '1', 'origin'])
        if ok:
            ok2, _, err2 = _run_cmd(
                ['git', '-C', OPENUBMC_MANIFEST_DIR, 'reset', '--hard', 'FETCH_HEAD'])
            if not ok2:
                return False, f'manifest reset failed: {err2}'.strip()
        else:
            return False, f'manifest fetch failed: {err}'.strip()
    else:
        ok, out, err = _run_cmd(
            ['git', 'clone', '--depth', '1', OPENUBMC_MANIFEST_URL,
             OPENUBMC_MANIFEST_DIR], timeout=600)
        if not ok:
            return False, f'manifest clone failed: {(err or out)[-300:]}'.strip()
    return True, ''


def _iter_manifest_files(manifest_dir):
    """manifest.yml 清单：build/sdk/manifest.yml + build/product/BMC/*/manifest.yml。"""
    roots = [os.path.join(manifest_dir, 'build', 'sdk', 'manifest.yml')]
    product_dir = os.path.join(manifest_dir, 'build', 'product', 'BMC')
    if os.path.isdir(product_dir):
        for name in sorted(os.listdir(product_dir)):
            cand = os.path.join(product_dir, name, 'manifest.yml')
            if os.path.isfile(cand):
                roots.append(cand)
    return [p for p in roots if os.path.isfile(p)]


def _collect_conan_deps(obj, out, file_path):
    """递归收集 YAML 树里所有 conan 依赖条目（含嵌套 dependencies，如 tosupporte.qemu），
    排除 action: delete 条目（如 qemu 分支的 bmc_soc/soctrl）。
    条目形状：(组件名, ref原文, manifest相对路径)。"""
    if isinstance(obj, dict):
        if 'conan' in obj and str(obj.get('action') or '').lower() != 'delete':
            ref = str(obj['conan']).strip().strip('"\'')
            out.append((ref.split('/')[0], ref, file_path))
        for v in obj.values():
            _collect_conan_deps(v, out, file_path)
    elif isinstance(obj, list):
        for v in obj:
            _collect_conan_deps(v, out, file_path)


def _parse_lock_component_names(lock_path):
    """conan lock v0.5 JSON：requires/build_requires 的 ref 取 / 前段为组件名。"""
    with open(lock_path, 'r', encoding='utf-8') as f:
        doc = json.load(f)
    names = set()
    for key in ('requires', 'build_requires'):
        for ref in (doc.get(key) or []):
            ref = str(ref).strip().strip('"\'')
            if ref and not ref.endswith(')'):  # 排除 python_requires 等带 () 的条目
                names.add(ref.split('/')[0])
    return names


def _conan_mapping_from_lock_refs(lock_refs, conan_user, conan_psw):
    """组件 → 代码仓名映射（权威证据链：conandata.yml sources.url）。

    对 lock 里的全量 ref（含版本）执行 conan download --only-recipe（只拉 recipe
    不拉二进制，单组件秒级），读缓存目录里 conandata.yml 的 sources.<ver>.url；
    仅保留 gitcode.com/openUBMC/* 的映射（gh_mirrors/grpc-mirror 镜像仓、github
    外部仓、tar 直链天然被过滤，不进任何分子分母）。
    单组件失败仅记 warning（该组件归不了仓），不阻断整批。
    """
    env = _conan_env(conan_user, conan_psw)
    name2repo = {}
    warnings = []
    for ref in sorted(lock_refs):
        comp = ref.split('/')[0]
        ok, out, err = _run_cmd(
            ['conan', 'download', ref, '--only-recipe', '-r', CONAN_REMOTE_NAME],
            env=env, timeout=300)
        if not ok:
            warnings.append(f'conan download failed ref={ref}: {(err or out)[-150:]}'.strip())
            continue
        ok, out, err = _run_cmd(['conan', 'cache', 'path', ref], env=env)
        if not ok:
            warnings.append(f'conan cache path failed ref={ref}: {(err or out)[-150:]}'.strip())
            continue
        cache_dir = out.strip().splitlines()[-1].strip()
        data_file = None
        for root, _dirs, files in os.walk(cache_dir):
            if 'conandata.yml' in files:
                data_file = os.path.join(root, 'conandata.yml')
                break
        if not data_file:
            warnings.append(f'conandata.yml not found ref={ref} cache={cache_dir}')
            continue
        url = None
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                doc = _yaml.safe_load(f) if _HAS_YAML else None
            for ver in ((doc or {}).get('sources') or {}).values():
                if isinstance(ver, dict) and ver.get('url'):
                    url = str(ver['url'])
                    break
                if isinstance(ver, str) and ver.startswith('http'):
                    url = ver
                    break
        except Exception:
            doc = None
        if not url:  # yaml 缺失/解析失败时正则兜底
            m = __import__('re').search(r'url:\s*(\S+)', open(
                data_file, 'r', encoding='utf-8', errors='ignore').read())
            url = m.group(1) if m else None
        if not url:
            warnings.append(f'sources.url not found ref={ref}')
            continue
        um = __import__('re').search(
            r'gitcode\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$', url.strip())
        if not um or um.group(1).lower() != 'openubmc':
            continue  # 镜像/外部仓：不归仓、不进分子分母
        name2repo[comp.lower()] = um.group(2).lower()
    return name2repo, warnings


def build_openubmc_context(args, conan_user, conan_psw):
    """批次级上下文（每批次最多一次，无 openUBMC 仓则不构建）。统一返回 ctx dict，
    失败时 ctx['error'] = (reason, message)。流程：
    manifest 浅克隆 → 解析 manifest.yml 依赖 + lock 固化集合 → conan 下载映射。
    """
    ctx = {
        'dep_entries': [],   # (组件名, ref原文, manifest相对路径)
        'lock_names': set(), # 被 lock 固化的组件名
        'name2repo': {},     # conan组件名(小写) -> 代码仓名(小写)
        'warnings': [],
        'error': None,       # (reason, message) 或 None
    }
    if not _HAS_YAML:
        ctx['error'] = ('pyyaml_missing', 'PyYAML is required for manifest.yml parsing')
        return ctx
    ok, err = _ensure_conan_remote(conan_user, conan_psw)
    if not ok:
        ctx['error'] = ('conan_scan_failed', err)
        return ctx
    ok, err = _clone_manifest_repo()
    if not ok:
        ctx['error'] = ('manifest_unavailable', err)
        return ctx

    # 1. manifest.yml 依赖收集（含嵌套，排除 delete）
    for mf in _iter_manifest_files(OPENUBMC_MANIFEST_DIR):
        try:
            with open(mf, 'r', encoding='utf-8') as f:
                doc = _yaml.safe_load(f)
        except Exception as e:
            ctx['warnings'].append(f'manifest parse failed {mf}: {e}')
            continue
        deps = []
        _collect_conan_deps(doc, deps, os.path.relpath(mf, OPENUBMC_MANIFEST_DIR))
        ctx['dep_entries'].extend(deps)

    # 2. lock 固化集合（产品级 + SDK 级）
    for lock in (os.path.join(OPENUBMC_MANIFEST_DIR, 'build', 'openubmc.lock'),
                 os.path.join(OPENUBMC_MANIFEST_DIR, 'build', 'sdk', 'openubmc_sdk.lock')):
        if os.path.isfile(lock):
            try:
                ctx['lock_names'] |= _parse_lock_component_names(lock)
            except Exception as e:
                ctx['warnings'].append(f'lock parse failed {lock}: {e}')

    # 3. conan 映射：对 lock 里出现的全量 ref 下载 recipe（lock 是全 ref 的可靠来源；
    #    manifest 纯名字依赖的组件若在 lock 中自然被覆盖，未在 lock 的组件归不了仓
    #    也不影响结论——它对应的仓本来就要判未固化）
    lock_refs = set()
    for lock in (os.path.join(OPENUBMC_MANIFEST_DIR, 'build', 'openubmc.lock'),
                 os.path.join(OPENUBMC_MANIFEST_DIR, 'build', 'sdk', 'openubmc_sdk.lock')):
        if os.path.isfile(lock):
            with open(lock, 'r', encoding='utf-8') as f:
                doc = json.load(f)
            for key in ('requires', 'build_requires'):
                for ref in (doc.get(key) or []):
                    ref = str(ref).strip().strip('"\'')
                    if ref and not ref.endswith(')'):
                        lock_refs.add(ref.split('%')[0])  # 去 lock v0.5 的 %ts 时间戳
    name2repo, map_warnings = _conan_mapping_from_lock_refs(lock_refs, conan_user, conan_psw)
    ctx['name2repo'] = name2repo
    ctx['warnings'].extend(map_warnings)
    return ctx


def openubmc_pinned_result(repo, ctx, max_paths):
    """openUBMC 仓 PINNED_DEP 结果（返回形状与 score_pinned_deps 完全兼容：
    (score, is_na, detail)，detail['_dep_rows'] 同构，下游写库/D4/D6 零改动）。"""
    if ctx is None:
        return None, 1, {'reason': 'conan_scan_failed',
                         'message': 'openUBMC context build failed'}
    if ctx.get('error'):
        reason, message = ctx['error']
        return None, 1, {'reason': reason, 'message': message}

    _, repo_name = parse_repo_identity(repo['repo_url'])
    repo_name_l = repo_name.lower()
    if repo_name_l not in ctx['name2repo']:
        return None, 1, {
            'reason': 'no_dependency',
            'message': '仓库未被 openUBMC/manifest.yml 依赖（无 conan 组件映射）',
            'scan_source': 'conan_manifest',
            'community': OPENUBMC_COMMUNITY_NAME,
        }

    entries = [e for e in ctx['dep_entries'] if e[0].lower() == repo_name_l]
    if not entries:
        return None, 1, {
            'reason': 'no_dependency',
            'message': 'conan 组件有映射但未出现在 manifest.yml dependencies（异常，请排查）',
            'scan_source': 'conan_manifest',
            'community': OPENUBMC_COMMUNITY_NAME,
        }

    deps, dep_rows = [], []
    pinned_count = 0
    for idx, (comp, ref, rel_path) in enumerate(entries):
        # 固化判定：组件名在 lock requires/build_requires 中，或 manifest 内嵌完整
        # ref（name/version@user/channel，如 ast2600 产品内嵌写死版本）
        inline_ref = '/' in ref and '@' in ref
        pinned = comp in ctx['lock_names'] or inline_ref
        pinned_count += 1 if pinned else 0
        reason = ('locked in openubmc.lock' if comp in ctx['lock_names']
                  else ('pinned in manifest (inline ref)' if inline_ref
                        else 'not locked in openubmc.lock / openubmc_sdk.lock'))
        if len(deps) < max_paths:
            deps.append({'type': 'conan', 'file': rel_path, 'line': None,
                         'ref': ref, 'pinned': pinned, 'signal': None,
                         'reason': reason})
        dep_rows.append((idx, 'conan', rel_path, None, ref,
                         1 if pinned else 0, None, reason))

    detail = {
        'pinned_count': pinned_count,
        'total_count': len(entries),
        'deps': deps,
        'truncated': len(entries) > max_paths,
        'unavailable_criteria': [],
        'warnings': list(ctx.get('warnings') or []),
        'scan_source': 'conan_manifest',
        'community': OPENUBMC_COMMUNITY_NAME,
        '_dep_rows': dep_rows,
    }
    score = round(pinned_count / len(entries) * 10, 2)
    return score, 0, detail


# =====================================================================
# 主流程
# =====================================================================

def main():
    args = resolve_deploy_paths(parse_arguments())
    print("=== Debug Information ===")
    print(f"Command line arguments: {sys.argv}")
    print(f"Platform: {os.name} (gcheck: --allow-unsupported-platform "
          f"{'auto-applied' if os.name == 'nt' else 'not needed (linux)'})")
    print(f"gcheck src: {args.gcheck_src}")
    print(f"scorecard bin: {args.scorecard_bin}")
    if not os.path.isfile(args.scorecard_bin):
        print(f"WARN: scorecard bin not found: {args.scorecard_bin} "
              f"(pinned-deps/binary-artifacts 依赖官方 scorecard，缺失时相关 check 将不可用)")
    print(f"ossfuzz status: {args.ossfuzz_status or '(none, fuzzing 名单比对将为不确定 miss)'}")
    if args.ossfuzz_status and not os.path.exists(args.ossfuzz_status):
        print(f"WARN: ossfuzz status path not found: {args.ossfuzz_status}")

    doris_url = args.doris_url
    doris_username = args.doris_username
    doris_password = args.doris_password

    if not all([doris_url, doris_username, doris_password]):
        print("No params from command line, trying DS placeholders (crypto)...")
        (ds_url, ds_user, ds_psw) = get_dolphinscheduler_params()
        # 2026-10-23 起 DS 侧账号/密码为 *_crypto 密文占位符，运行时解密（示例解密任务同模式）
        doris_url = ds_url if not _is_unreplaced_placeholder(ds_url) else None
        doris_username = resolve_credential(ds_user, args.doris_username, 'openlibing_doris_username_crypto')
        doris_password = resolve_credential(ds_psw, args.doris_password, 'openlibing_doris_password_crypto')
        if not doris_url:
            print("ERROR: doris url missing (DS placeholder unreplaced and no --doris-url).", flush=True)
            sys.exit(1)

    repo_id_filter = None
    if args.repo_ids:
        repo_id_filter = [int(x) for x in args.repo_ids.split(',') if x.strip()]

    # 复用处理脚本预 clone 的本地仓根目录（不 clone、不删除，共享资源）
    repo_base_dir = args.repo_base_dir
    if not os.path.isdir(repo_base_dir):
        print(f"WARN: repo base dir not found: {repo_base_dir} "
              f"(处理脚本预 clone 根目录；缺失时所有仓将写 NA 行 reason=repo_not_found)")
    print(f"Repo base dir: {repo_base_dir}")

    # 统一批次扫描时间戳（design.md §3：一次扫描所有指标同一 scan_time）
    unified_scan_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    etl_time = unified_scan_time
    print(f"Unified scan time: {unified_scan_time}")

    connection = get_db_connection(doris_url, doris_username, doris_password)
    success_count = 0
    failure_count = 0
    try:
        repos = load_repo_list(connection, repo_id_filter)
        if not repos:
            print("ERROR: empty repo list")
            return 1

        # openUBMC 社区特判（PINNED_DEP 走 conan/manifest 口径；用户名明文内置、
        # 密码经 ${openubmc_conan_psw_crypto} 解密注入，本地调试用 --conan-psw 明文回退；
        # 未配置时仅该社区指标落 NA 不影响其他仓）
        ds_conan_user = args.conan_user or OPENUBMC_CONAN_USER
        ds_conan_psw = resolve_optional_credential(
            DS_OPENUBMC_CONAN_PSW, args.conan_psw, 'openubmc_conan_psw_crypto')

        openubmc_ids = load_openubmc_repo_ids(connection)
        ubmc_ctx = None
        if openubmc_ids & {r['repo_id'] for r in repos}:
            if ds_conan_user and ds_conan_psw:
                print("Building openUBMC conan context (manifest clone + recipe mapping)...")
                ubmc_ctx = build_openubmc_context(args, ds_conan_user, ds_conan_psw)
                if ubmc_ctx.get('error'):
                    print(f"WARN: openUBMC context failed: {ubmc_ctx['error']} "
                          f"(该社区仓 PINNED_DEP 将落 NA)", flush=True)
                else:
                    print(f"openUBMC context ready: deps={len(ubmc_ctx['dep_entries'])} "
                          f"locked={len(ubmc_ctx['lock_names'])} "
                          f"mapped_repos={len(ubmc_ctx['name2repo'])}", flush=True)
            else:
                print("WARN: openUBMC conan password not configured "
                      "(${openubmc_conan_psw_crypto} 未配置，本地调试传 --conan-psw)；"
                      "该社区仓 PINNED_DEP 将落 NA", flush=True)
                ubmc_ctx = {'error': ('conan_scan_failed',
                                      'openUBMC conan credentials not configured'),
                            'warnings': []}

        total = len(repos)
        metric_totals = {}  # 汇总各指标得分均值（便于快速质检）
        na_repo_count = 0   # 三态异常仓（3 指标全 NA 写库，不计失败）
        for i, repo in enumerate(repos):
            repo_id = repo['repo_id']
            repo_url = repo['repo_url']
            default_branch = repo.get('default_branch')
            branch_tag = f"branch={default_branch}" if default_branch else "branch=(NA)"
            print(f"\n[{i + 1}/{total}] repo_id={repo_id} {repo_url} [{branch_tag}]", flush=True)
            try:
                # 本地仓路径 = {repo_base_dir}/{platform}/{owner}/{repo_name}（处理脚本同款）
                repo_dir = build_repo_path(repo_base_dir, repo_url)
                na_reason = None
                na_message = ''
                if not default_branch:
                    na_reason = 'no_default_branch'
                    na_message = 'sdi_repo_branch_info has no default_branch for this repo'
                elif not os.path.isdir(repo_dir):
                    na_reason = 'repo_not_found'
                    na_message = f'local repo directory not found: {repo_dir}'
                elif not checkout_branch(repo_dir, default_branch):
                    na_reason = 'checkout_failed'
                    na_message = f'git checkout {default_branch} failed in {repo_dir}'

                if na_reason:
                    results = build_na_results(na_reason, na_message)
                    na_repo_count += 1
                    print(f"  NA ({na_reason}): {na_message}", flush=True)
                else:
                    results = scan_one_repo(repo, repo_dir, args)
                    # openUBMC 特判：仅替换 PINNED_DEP 结果（FUZZING/BINARY_ARTIFACTS
                    # 仍走 gcheck 照常落分），返回形状与 score_pinned_deps 兼容
                    if repo_id in openubmc_ids and ubmc_ctx is not None:
                        results['PINNED_DEP'] = openubmc_pinned_result(
                            repo, ubmc_ctx, args.max_detail_paths)

                rows = []
                # 依赖锁定全量明细：pop 出来防止进 detail_json（deps 截断版保持渲染契约），
                # 写完全量明细表后再写主表
                pinned_dep_rows = []
                if (not na_reason) and isinstance(results.get('PINNED_DEP', (None, None, None))[2], dict):
                    pinned_dep_rows = results['PINNED_DEP'][2].pop('_dep_rows', []) or []
                for metric_code, (score, is_na, detail) in results.items():
                    metric_totals.setdefault(metric_code, {'sum': 0.0, 'n': 0, 'na': 0})
                    if is_na:
                        metric_totals[metric_code]['na'] += 1
                    else:
                        metric_totals[metric_code]['sum'] += (score or 0)
                        metric_totals[metric_code]['n'] += 1
                    rows.append({
                        'repo_id': repo_id,
                        'metric_code': metric_code,
                        'scan_time': unified_scan_time,
                        'repo_url': repo_url,
                        'detail_json': json.dumps(detail, ensure_ascii=False),
                        'score': score,
                        'is_na': is_na,
                        'etl_time': etl_time,
                    })
                inserted = insert_metric_rows(rows, connection)
                if inserted:
                    success_count += 1
                    scores_desc = ', '.join(
                        f"{m}={'NA' if results[m][1] else results[m][0]}" for m in results)
                    print(f"  inserted {inserted} rows | {scores_desc}", flush=True)
                # 依赖锁定全量明细表（分页接口数据源；NA 仓 pinned_dep_rows 为空自动跳过）
                if pinned_dep_rows:
                    dep_inserted = insert_pinned_dep_rows(
                        repo_id, unified_scan_time, etl_time, pinned_dep_rows, connection)
                    print(f"  pinned_dep_detail inserted {dep_inserted} rows", flush=True)
            except Exception as e:
                failure_count += 1
                print(f"  ERROR processing repo_id={repo_id}: {e}", flush=True)
                import traceback
                traceback.print_exc()
            print(f"Progress: {i + 1}/{total} | OK: {success_count} FAIL: {failure_count} NA: {na_repo_count}", flush=True)
    except Exception as e:
        print(f"FATAL: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            connection.close()
            print("Database connection closed", flush=True)
        except Exception:
            pass

    # 批次汇总
    print("\n" + "=" * 60)
    print(f"Summary: {success_count} successful, {failure_count} failed, "
          f"{na_repo_count} NA repos (3 metrics all-NA), scan_time={unified_scan_time}")
    for m in sorted(metric_totals):
        t = metric_totals[m]
        avg = round(t['sum'] / t['n'], 2) if t['n'] else None
        print(f"  {m:18s} avg_score={avg} scored={t['n']} na={t['na']}")
    if success_count == 0 and failure_count > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
