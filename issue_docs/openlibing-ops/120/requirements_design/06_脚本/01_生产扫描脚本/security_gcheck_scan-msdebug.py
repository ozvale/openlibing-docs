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

# 处理脚本预 clone 的本地仓根目录（与 DS"[GitCode]扫描代码仓编码风格"任务一致）
DEFAULT_REPO_BASE_DIR = '/openlibing/git'

# detail_json 内路径数组的截断上限（防止千级文件爆行，计数仍是全量）
MAX_DETAIL_PATHS = 200

# metric_code -> gcheck check 名（输出 JSON checks[].check）
METRIC_CHECK_MAP = {
    'PINNED_DEP': 'pinned-deps',
    'FUZZING': 'fuzzing',
    'BINARY_ARTIFACTS': 'binary-artifacts',
}

# 单仓一次 gcheck 调用跑的 check 列表（--check 可重复传）
GCHECK_CHECKS = ['pinned-deps', 'fuzzing', 'binary-artifacts']

# 单仓 gcheck 超时（秒）。常规仓实测三 check 约 30s（repo_400030 22s）；生产批次
# 默认 900s（15 分钟，超时按 NA 处理不阻断批次）；超大仓（如 msdebug 14.7 万文件）
# 900s 跑不完，不走本默认值——单独建 DS 任务用 --repo-ids 圈定仓库、--gcheck-timeout 0
# 不设超时补扫。--gcheck-timeout 可调，传 0 = 不设超时等 gcheck 自然跑完。
DEFAULT_GCHECK_TIMEOUT = 0

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
    parser.add_argument('--repo-ids', default='401712',
                        help='401712')
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
    """Doris 凭证（照抄 security_file_scan.py，DS 内联任务执行前对脚本文本做全局替换）。"""
    return (
        '${openlibing_doris_url}',
        '${openlibing_doris_username}',
        '${openlibing_doris_password}',
    )


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
           "  AND sri.repo_id = '401712' ")
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
    for it in items[:max_paths]:
        verdict = it.get('verdict')
        deps.append({
            'type': it.get('id'),            # 判据：containerImage/pipCommand/...
            'file': it.get('path'),
            'line': it.get('lineStart'),
            'ref': it.get('snippet'),       # 源文件真实那一行
            'pinned': True if verdict == 'compliant' else (False if verdict == 'nonCompliant' else None),
            'signal': it.get('signal'),     # mutableTag/stageAlias/variableRef/localPath/...
            'reason': it.get('detail'),     # gcheck 自带整改路径文案
        })
    detail = {
        'pinned_count': compliant,
        'total_count': denominator,
        'deps': deps,
        'truncated': len(items) > max_paths,
        'unavailable_criteria': _unavailable_criteria(check),
        'warnings': _check_warnings(check),
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
        print("No params from command line, trying DS environment variables...")
        (doris_url, doris_username, doris_password) = get_dolphinscheduler_params()

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

                rows = []
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
