#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全文件扫描 P1 脚本（代码安全检查评分看板 · design.md v4 §11.3 P1）

功能（7 个 metric_code，规则见 design.md §5；
指标6 BINARY_ARTIFACTS 已于 2026-10-10 移交 security_gcheck_scan.py——gcheck 按文件
内容魔数识别真可执行产物，替代本脚本原 22 种后缀清单口径，两脚本不得同时产出该指标）：
  指标2  COPYRIGHT        版权合规        2026-10-06 v2 模板化改版：根 LICENSE 分流
                                        木兰/印刷/4+1 三路模板比对 + 版权行底线
                                        （双语序三正则，兼容年份区间/无(c)写法），
                                        test/tests 精确段剔除；无 LICENSE 整仓 NA；
                                        规则源 docs/0912/参考/copyright_metric_handoff.md
  指标3  DANGEROUS_WF     危险工作流      发现危险模式=0，未发现=10；无 workflow=10
                                        （2026-10-16 口径更新：原 NA 改满分；
                                        解析失败仍 NA）
  指标4  TOKEN_PERM       令牌权限        2026-09-28 改版：按插件给定权限检查
                                        （13 openlibing 插件基准表 + 未命中按只读），
                                        三层生效权限（job>全局>默认读），
                                        违规插件仓库级 Set 去重扣 1 分/个；无 workflow=10、
                                        无受检插件=10（2026-10-16 口径更新：原 NA 改满分；
                                        解析失败仍 NA）
  指标8  BRANCH_PROTECTION 分支保护      仅存 rebot.yaml 明细（score=NULL/is_na=0），
                                        最终得分由 D7 SQL 结合 /lgtm 评论数据计算（v4.4）
  指标12 PACKAGING        软件包发布      workflow 内存在制品上传插件(uses=obs-upload/upload-artifact)
                                        或仓库名命中 openEuler 包清单=10，否则 NA（2026-10-06 规则）
  指标14 SAST             静态分析        2026-09-30 改版：pre-commit（根目录或 pre-commit/ 目录，
                                        合并扫描）或 workflow 中使用任一 SAST 工具
                                        （clang-tidy/bandit/eslint/gosec/clippy/spotbugs/
                                        gitleaks/luacheck）=10，否则 0 分（含无配置文件，
                                        2026-10-10 口径调整：原 NA 改 0 分）
  指标15 SECURITY_POLICY  安全策略        仓内存在 SECURITY.md=10，否则 0（社区 5 分分支预留）

流程（2026-09-22 改版：复用本地仓，不再 clone，与 DS"[GitCode]扫描代码仓编码风格"
任务同款路径口径）：
  1. 从 Doris 读仓库清单：sdi_repo_info WHERE repo_id IN (operate_conf is_operate=1)，
     JOIN sdi_repo_branch_info 取默认分支（default_branch=true，仅扫默认分支，
     口径与 openlibing-ops PR 看板 repo/branch/all 接口保持一致）
  2. 复用"处理脚本"预 clone 的本地仓：--repo-base-dir（默认 /openlibing/git）下
     {platform}/{owner}/{repo_name}（与处理脚本/编码风格任务的 build_repo_path 完全一致）；
     仅 checkout 默认分支（信任处理脚本已拉最新，不做 fetch）。
     三种异常均写 NA 行不丢仓（与线上编码风格任务"写空记录"口径对齐）：
       ① 本地目录不存在（pre-clone 失败）→ 8 指标全 NA（reason=repo_not_found）
       ② 无默认分支信息 → 8 指标全 NA（reason=no_default_branch）
       ③ checkout 失败 → 8 指标全 NA（reason=checkout_failed）
  3. 8 个 metric_code 各产出一行，写 dwi_rd_efc_security_file_scan
     （UNIQUE KEY repo_id+metric_code+scan_time，同批次重跑自动覆盖，幂等）
  4. 不删除/不改动本地仓目录（共享资源，由处理脚本统一维护）

通用口径（design.md §3）：
  - NA = score NULL + is_na=1（汇聚时分子分母剔除该项权重）
  - 0 分是有效得分，参与汇聚
  - 一批扫描统一 scan_time（脚本启动时间），与 dwi 其他表批次对齐

分支口径（2026-09-20 定版）：
  - 只扫默认分支；默认分支取 sdi_repo_branch_info.default_branch（实时维护）
  - 不用 dwi_code_scan_language.is_default_branch（扫描快照值，存在延迟）
  - 不用 code_repo_branch_config.show_branch（PR 看板展示分支配置，非安全扫描口径）

运行前置：
  - Python3 + pip install pymysql pyyaml
  - 本机 git 可用（仅本地 checkout/ls-files，不联网）
  - "处理脚本"已完成预 clone（--repo-base-dir 下 {platform}/{owner}/{repo_name}）
  - Doris 已执行 dwi-dm层建表DDL.sql（dwi_rd_efc_security_file_scan 表）
  - 凭证不落脚本：Doris 认证从参数/环境变量注入，禁止写死

DS（DolphinScheduler）部署：脚本内 DS 占位符由 DS 全局文本替换注入，
本地裸跑时占位符未替换（仍以 $ 开头），自动回退 CLI 参数 / 环境变量。
"""

import os
import sys
import re
import json
import argparse
import datetime
import subprocess
import urllib.request

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

try:
    import yaml  # PyYAML：解析 workflow yml（DANGEROUS_WF / TOKEN_PERM）
except ImportError:
    yaml = None

# =====================================================================
# 常量区（规则来源：design.md v4 §5，勿随意修改）
# =====================================================================

# 指标2 版权合规（2026-10-06 v2 模板化改版，规则源：参考/copyright_metric_handoff.md）：
# 目标文件后缀 10 种（不变）；单文件读取上限 8MB 沿用（超限/不可读分子分母均不计，
# 2026-09-21 拍板）。模板化检查只看前 64 行头部窗口，读文件头即可（大仓 4 万+文件性能）。
COPYRIGHT_EXTS = {'.go', '.java', '.py', '.js', '.c', '.cpp', '.rs', '.ts', '.sh', '.bat'}
COPYRIGHT_READ_LIMIT = 8 * 1024 * 1024
COPYRIGHT_HEAD_BYTES = 256 * 1024
COPYRIGHT_HEADER_LINES = 64

# LICENSE 文件候选（§4.2：按序探测仓库根目录，大小写敏感逐个试；找不到/不可读 → 整仓 NA）
LICENSE_CANDIDATES = ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENSE.rst',
                      'License', 'COPYING', 'COPYING.txt')
LICENSE_READ_LIMIT = 1024 * 1024

# 木兰识别正则（§4.3：12 条逐字复制自 copyright-tools backend/repo_manager.py:82-101，
# 禁止改动；匹配顺序 v2 优先（负向前瞻防 v1 误判），中文版 LICENSE 靠 coscl URL 兜底）
MULAN_PATTERNS = {
    "MulanPSL-2.0": [
        r"Mulan\s*PSL\s*v?2",
        r"MulanPSL[- ]?2",
        r"license\.coscl\.org\.cn/MulanPSL2",
    ],
    "MulanPSL-1.0": [
        r"Mulan\s*PSL\s*v?1(?!.*2)",
        r"MulanPSL[- ]?1",
        r"license\.coscl\.org\.cn/MulanPSL(?!2)",
    ],
    "MulanPubL-2.0": [
        r"Mulan\s*PubL\s*v?2",
        r"MulanPubL[- ]?2",
        r"license\.coscl\.org\.cn/MulanPubL-2",
    ],
    "MulanPubL-1.0": [
        r"Mulan\s*PubL\s*v?1(?!.*2)",
        r"MulanPubL[- ]?1",
        r"license\.coscl\.org\.cn/MulanPubL-1",
    ],
}
# 木兰 license_id -> 配置表 template_id（§4.3）
MULAN_TEMPLATE_IDS = {
    'MulanPSL-2.0': 'mulan-psl-2.0', 'MulanPSL-1.0': 'mulan-psl-1.0',
    'MulanPubL-2.0': 'mulan-publ-2.0', 'MulanPubL-1.0': 'mulan-publ-1.0',
}

# 版权行底线三正则（§4.5 逐字复制）：年份在前 / owner 在前 / 无 (c)，任一命中即达标；
# 只查 4 位年份格式不查具体值，年份区间（2025-2025）允许，owner 容许 ",Ltd" 缺句点/
# "Co.,Ltd" 无空格写法
RE_COPY_YF = re.compile(
    r'Copyright\s*\(c\)\s*(\d{4})(?:\s*-\s*\d{4})?\s+(Huawei\s+Technologies\s+Co\.?,?\s*Ltd\.?)',
    re.IGNORECASE)
RE_COPY_OF = re.compile(
    r'Copyright\s*\(c\)\s+(Huawei\s+Technologies\s+Co\.?,?\s*Ltd\.?)\s+(\d{4})(?:\s*-\s*\d{4})?',
    re.IGNORECASE)
RE_COPY_NC = re.compile(
    r'Copyright\s+(\d{4})\s+(Huawei\s+Technologies\s+Co\.?,?\s*Ltd\.?)',
    re.IGNORECASE)

# upstream_banner 判定特征（§8.5 最小集：仅 LLVM，命中只打标不改判定）
UPSTREAM_BANNER_MARK = 'part of the llvm project'

# 指标3/4 workflow 目录候选：design.md §5.3 写 .gitcode/workflows、§5.4 写 .gitcode/workflow，
# 两处拼写不一致，为容错两种写法均扫描（仅 gitcode 平台，不扫 .github）
WF_DIR_CANDIDATES = ('.gitcode/workflows', '.gitcode/workflow')
WF_EXTS = {'.yml', '.yaml'}

# 指标3 危险工作流：不可信上下文变量（design.md §5.3 映射表 github→gitcode/atomgit，
# 同时兼容 github 原变量与 gitcode 前缀写法）
UNTRUSTED_CONTEXT_VARS = (
    'github.event.issue.title', 'atomgit.event.issue.title', 'gitcode.event.issue.title',
    'github.event.pull_request.title', 'atomgit.event.pull_request.title', 'gitcode.event.pull_request.title',
    'github.event.pull_request.body', 'atomgit.event.pull_request.body', 'gitcode.event.pull_request.body',
    'github.event.comment.body', 'atomgit.event.comment.body', 'gitcode.event.comment.body',
    'github.event.head_commit.message', 'atomgit.event.commits[].message', 'gitcode.event.commits[].message',
    'github.head_ref', 'atomgit.head_ref', 'gitcode.head_ref',
)
# commits 数组实际按下标引用（如 commits[0].message），子串匹配不上文档写法的 []，
# 该三条按前缀匹配（中括号内任意下标均命中）
UNTRUSTED_CONTEXT_PREFIXES = (
    'github.event.commits[', 'atomgit.event.commits[', 'gitcode.event.commits[',
)
# 指标3：显式放开不可信检出保护的配置键（仅该显式配置视为违规）
UNSAFE_CHECKOUT_KEY = 'allow-unsafe-pr-checkout'

# 指标12 PACKAGING：openEuler 工程比对源表（raw 层数据已到位；S3 sdi 表建成后可切换）
DEFAULT_EULER_TABLE = 'raw_euler_package_info'

# 指标14 SAST（2026-09-30 规则改版）：pre-commit 配置文件候选位置
# （根目录 + pre-commit/ 目录，两处同时存在时合并扫描，工具取并集）
SAST_PRECOMMIT_PATHS = ('.pre-commit-config.yaml', 'pre-commit/.pre-commit-config.yaml')
# SAST 工具基准表：(工具码, 语言, pre-commit 检测 id, workflow 检测词)
# pre-commit 按 hook id 精确匹配（YAML 解析天然兼容 id: xxx / id:xxx 两种写法，
# 解析失败时正则兜底）；workflow 按单词边界匹配（不区分大小写）
SAST_TOOLS = (
    ('clang-tidy', 'C/C++', 'clang-tidy', 'clang-tidy'),
    ('bandit', 'Python', 'bandit', 'bandit'),
    ('eslint', 'JS/TS', 'eslint', 'eslint'),
    ('gosec', 'Go', 'gosec', 'gosec'),
    ('clippy', 'Rust', 'cargo-clippy', 'clippy'),
    ('spotbugs', 'Java', 'mvn-spotbugs', 'spotbugs'),
    ('gitleaks', '通用', 'gitleaks', 'gitleaks'),
    ('luacheck', 'Lua', 'luacheck', 'luacheck'),
)

# 指标15 安全策略：候选文件路径（按优先级）
SECURITY_MD_CANDIDATES = ('.gitcode/SECURITY.md', 'SECURITY.md', 'docs/SECURITY.md', 'security.md')
# 三检测：披露关键词 / 联系链接正则（邮箱、mailto、http(s) URL）
# 2026-10-13 增补中文关键词与 SLO：评估仓以中文 SECURITY.md 为主，纯英文词集漏报严重；
# "反馈/上报"等常用词刻意排除，避免把普通问题反馈渠道误判为漏洞披露。
DISCLOSURE_KEYWORDS = ('report', 'vulnerability', 'disclos', 'exploit', 'cve',
                       '漏洞', '披露', 'slo')
CONTACT_RE = re.compile(r'(mailto:|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|https?://)')
SECURITY_MD_READ_LIMIT = 1024 * 1024

# 指标15 安全策略：社区集中文件例外（2026-10-19）
# boostkit / openeuler 社区的评估仓不扫各自仓内 SECURITY.md，统一扫社区集中
# 安全策略文件（GitCode raw URL 运行时拉取，每批次每社区仅一次，模块级缓存）。
# 拉取失败/超限按 0 分（沿用"无 SECURITY.md = 0"口径），detail 标 reason 便于排查。
COMMUNITY_SECURITY_POLICY_FILES = {
    'boostkit': {
        'file_label': 'boostkit/community:docs/security-Committee/SecureRelease.md',
        'url': 'https://raw.gitcode.com/boostkit/community/raw/master/docs/security-Committee/SecureRelease.md',
    },
    'openeuler': {
        'file_label': 'openeuler/security-committee:security-strategy-overview.md',
        'url': 'https://raw.gitcode.com/openeuler/security-committee/raw/master/security-strategy-overview.md',
    },
}
_COMMUNITY_POLICY_CONTENT_CACHE = {}  # owner -> (content or None, error or None)
COMMUNITY_POLICY_URL_TIMEOUT = 30  # 秒

# 指标8 分支保护：机器人个性化配置文件路径（v4.4，2026-09-28 规则更新）
REBOT_YAML_PATH = '.infra_self_service/rebot.yaml'
REBOT_YAML_READ_LIMIT = 1024 * 1024

# detail_json 内路径数组的截断上限（防止千级文件爆行，计数仍是全量）
MAX_DETAIL_PATHS = 200

# Doris 目标表（dwi-dm层建表DDL.sql [4]）
TARGET_TABLE = 'dwi_rd_efc_security_file_scan'

# 版权合规逐文件明细表（dwi-dm层建表DDL.sql [11]，明细试验新增）：
# 全量落不合格文件（不受 MAX_DETAIL_PATHS 截断），看板走分页查询。
# 大仓可达万级行（repo_401712 实测 1.2 万+），分批 executemany 防 Doris 单批过大。
COPYRIGHT_FILE_TABLE = 'dwi_rd_efc_security_copyright_file_detail'
COPYRIGHT_FILE_INSERT_BATCH = 2000

# 处理脚本预 clone 的本地仓根目录（与 DS"[GitCode]扫描代码仓编码风格"任务一致）
DEFAULT_REPO_BASE_DIR = '/openlibing/git'


# =====================================================================
# 参数与环境
# =====================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Security file scan (P1): 8 metric_code -> dwi_rd_efc_security_file_scan')
    parser.add_argument('--doris-url', default=None,
                        help='Doris JDBC URL（本地调试用；DS 运行时由占位符注入，无需传）')
    parser.add_argument('--doris-username', default=None, help='Doris 用户名（本地调试用）')
    parser.add_argument('--doris-password', default=None, help='Doris 密码（本地调试用）')
    parser.add_argument('--repo-ids', default=None,
                        help='逗号分隔的 repo_id 过滤列表（调试单仓用），如 401431；缺省扫全部 is_operate=1')
    parser.add_argument('--repo-base-dir', default=DEFAULT_REPO_BASE_DIR,
                        help='处理脚本预 clone 的本地仓根目录（默认 /openlibing/git），'
                             '仓路径 = {base}/{platform}/{owner}/{repo_name}')
    parser.add_argument('--euler-table', default=DEFAULT_EULER_TABLE,
                        help='openEuler 包清单表（默认 raw_euler_package_info，S3 建成后可改 sdi_rd_efc_euler_package）')
    parser.add_argument('--max-detail-paths', type=int, default=MAX_DETAIL_PATHS,
                        help='detail_json 路径数组截断上限')
    parser.add_argument('--plugin-baseline-file', default=None,
                        help='TOKEN_PERM 插件权限基准表 JSON（单一配置源，追加插件只改该文件）。'
                             '缺省加载脚本同目录 token_perm_plugin_baseline.json；'
                             '文件缺失时报错退出')
    return parser.parse_args()


def get_dolphinscheduler_params():
    """Doris 凭证（照抄生产编码风格任务 get_dolphinscheduler_params，2026-09-22）：
    占位符裸写在返回值字面量里，DS 内联任务执行前对脚本文本做全局替换。"""
    return (
        '${openlibing_doris_url}',
        '${openlibing_doris_username}',
        '${openlibing_doris_password}',
    )


# =====================================================================
# Doris 工具
# =====================================================================

def parse_doris_url(doris_url):
    """jdbc:mysql://host:port/db -> (host, port, db)，与 commit 扫描脚本同款解析。"""
    if not doris_url or not doris_url.startswith('jdbc:mysql://'):
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    url_part = doris_url[len('jdbc:mysql://'):]
    m = re.search(r'[^/]+/([^?]+)', url_part)
    if not m:
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    db_database = m.group(1)
    hosts_ports_part = url_part.split('/')[0]
    if not hosts_ports_part:
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    first_host_port = hosts_ports_part.split(',')[0].strip()
    hm = re.match(r'([^:]+):(\d+)', first_host_port)
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
    """扫描范围：sdi_rd_efc_repo_operate_conf 且 is_operate=1（design.md §3）。
    清单口径（2026-09-20 定版，与 ops PR 看板 repo/branch/all 分支口径一致）：
      - 只扫默认分支：default_branch 取 sdi_repo_branch_info.default_branch（实时维护；
        原 dwi_code_scan_language.is_default_branch 是扫描快照值，存在延迟）
      - 2026-09-22 起复用本地仓不再 clone，凭证 JOIN 已删除（platform 仍需，
        用于拼本地路径 {base}/{platform}/{owner}/{repo_name}）
    返回行含 repo_id / repo_url / platform / default_branch。
    2026-10-06 起加 platform='gitcode' 过滤（安全指标仅评估 GitCode 仓，
    与 SeaTunnel 接口收集层同口径；github 等其他平台仓不进扫描全集）。"""
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


def load_euler_manifest(connection, euler_table):
    """加载 openEuler 包工程清单：包名(小写) -> [os_project...]。
    包名由 spec_url 尾段反解（去 .git，与 sdi 层 DDL package_name 口径一致），
    raw_euler_package_info / sdi_rd_efc_euler_package 均可作为数据源。
    表不存在/查询失败时返回 None（PACKAGING 仅按 workflow 判定，不阻断整体）。"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT spec_url, os_project FROM {euler_table}")
            rows = cursor.fetchall()
    except Exception as e:
        print(f"WARN: load euler manifest from {euler_table} failed: {e}")
        print(f"      PACKAGING will be judged by workflow only (in_openeuler_project=NULL)")
        return None
    manifest = {}
    for r in rows:
        _, package_name = parse_repo_identity(r['spec_url'])
        if package_name and package_name != 'unknown':
            manifest.setdefault(package_name.lower(), []).append(r['os_project'])
    print(f"Loaded euler manifest: {len(manifest)} package names from {len(rows)} rows")
    return manifest


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


def insert_copyright_file_rows(repo_id, scan_time, file_rows, connection, etl_time):
    """版权合规逐文件明细 → dwi_rd_efc_security_copyright_file_detail（明细试验新增）。

    全量落不合格文件（file_rows = scan_copyright 第 4 返回值，不受截断限制）；
    UNIQUE KEY (repo_id, scan_time, file_path) 幂等覆盖；按 2000 行分批。
    设计取舍：明细表属辅助数据，失败仅告警不抛出——主表 metric 行已先行落库，
    明细缺失不应让整仓计为失败（与 insert_metric_rows 的失败语义不同）。
    返回成功写入行数。"""
    if not file_rows:
        return 0
    sql = (f"INSERT INTO {COPYRIGHT_FILE_TABLE} "
           "(repo_id, scan_time, file_path, ext, reason, is_banner, etl_time) "
           "VALUES (%s, %s, %s, %s, %s, %s, %s)")
    inserted = 0
    for start in range(0, len(file_rows), COPYRIGHT_FILE_INSERT_BATCH):
        chunk = file_rows[start:start + COPYRIGHT_FILE_INSERT_BATCH]
        batch = [(repo_id, scan_time, r['file_path'], r['ext'], r['reason'],
                  r['is_banner'], etl_time) for r in chunk]
        ok = False
        for attempt in (1, 2):
            try:
                with connection.cursor() as cursor:
                    cursor.executemany(sql, batch)
                connection.commit()
                inserted += len(batch)
                ok = True
                break
            except Exception as e:
                try:
                    connection.rollback()
                except Exception:
                    pass
                print(f"  copyright file detail insert attempt {attempt} "
                      f"failed (rows {start}-{start + len(batch)}): {e}", flush=True)
        if not ok:
            print(f"  ERROR: copyright file detail chunk dropped for repo_id={repo_id} "
                  f"(rows {start}-{start + len(batch)}), metric rows unaffected", flush=True)
    return inserted


# =====================================================================
# git 工具（本地仓复用模式：不 clone，复用处理脚本预 clone 的本地仓）
# 路径规则与 DS"[GitCode]扫描代码仓编码风格"任务的 build_repo_path 完全一致
# =====================================================================

def get_platform_from_url(repo_url):
    """从 URL 提取平台名（gitcode/github/gitee/gitlab/bitbucket）。
    复刻自处理脚本.python（编码风格任务同款）。"""
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
    """从 URL 解析 (owner, repo_name)。
    owner 是 host 与 repo_name 之间的路径段（可能含子组，如 group/subgroup）；
    repo_name 是末段（去掉 .git 后缀）。复刻自处理脚本.python。"""
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
    复刻自编码风格任务同款（含 '--' 消歧义 fallback）；
    -c safe.directory=* 跳过 dubious ownership 检查（处理脚本 clone 的仓所有权可能不同）。
    已在目标分支时跳过 checkout（处理脚本预 clone 已在默认分支时命中，零成本，
    2026-09-26：避免对大仓重复执行 git checkout）。"""
    git_safe_args = ['-c', 'safe.directory=*']
    # 短路：当前已在目标分支则不执行 checkout
    try:
        cur = subprocess.run(
            ['git', *git_safe_args, '-C', repo_path, 'branch', '--show-current'],
            capture_output=True, text=True, check=True
        )
        if cur.stdout.strip() == branch_name:
            print(f"  Already on branch: {branch_name} (skip checkout)")
            return True
    except Exception:
        pass  # 检测失败则走正常 checkout 兜底
    try:
        result = subprocess.run(
            ['git', *git_safe_args, '-C', repo_path, 'checkout', branch_name],
            capture_output=True, text=True, check=True
        )
        print(f"  Checked out branch: {branch_name}")
        return True
    except subprocess.CalledProcessError as e:
        if "could be both a local file and a tracking branch" in (e.stderr or ''):
            try:
                result = subprocess.run(
                    ['git', *git_safe_args, '-C', repo_path, 'checkout', '--', branch_name],
                    capture_output=True, text=True, check=True
                )
                print(f"  Checked out branch (with --): {branch_name}")
                return True
            except subprocess.CalledProcessError as e2:
                print(f"  Error checking out {branch_name}: {(e2.stderr or '').strip()[-300:]}")
                return False
        else:
            print(f"  Error checking out {branch_name}: {(e.stderr or '').strip()[-300:]}")
            return False
    except Exception as e:
        print(f"  Unexpected error during checkout: {e}")
        return False


def list_tracked_files(repo_path):
    """git ls-files 列 tracked 文件（自动排除 .git 与未跟踪文件），\0 分隔防文件名歧义。"""
    cmd = ['git', '-c', 'safe.directory=*', '-C', repo_path, 'ls-files', '-z']
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {(result.stderr or b'').decode('utf-8', 'replace')[:300]}")
    names = [n.decode('utf-8', 'replace') for n in result.stdout.split(b'\x00') if n]
    return names


def read_text_file(path, limit):
    """读文本文件（errors=ignore 容错任意编码），超限返回 None。"""
    try:
        size = os.path.getsize(path)
        if size > limit:
            return None
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except OSError:
        return None


# =====================================================================
# URL 归一化（指标12 PACKAGING 比对口径）
# =====================================================================

def normalize_repo_url(url):
    """归一化：去协议、去 .git 后缀、host 小写、atomgit.com -> gitcode.com（design.md §5.12）。
    返回 'host/owner/repo'，异常返回 None。"""
    try:
        u = (url or '').strip()
        if '://' in u:
            u = u.split('://', 1)[1]
        if u.endswith('.git'):
            u = u[:-4]
        parts = [p for p in u.split('/') if p]
        if len(parts) < 3:
            return None
        host = parts[0].lower().replace('atomgit.com', 'gitcode.com')
        return '/'.join([host] + parts[1:])
    except Exception:
        return None


# =====================================================================
# 文件树辅助（大小写精确匹配，保证 Windows 本地跑与 Linux 调度结果一致）
# =====================================================================

def list_dir_exact(dir_path):
    """列目录条目集合（精确文件名，大小写敏感语义）。"""
    try:
        return set(os.listdir(dir_path))
    except OSError:
        return set()


def find_workflow_files(repo_path):
    """找 .gitcode/workflows 与 .gitcode/workflow 下的 yml/yaml 文件（相对路径列表）。"""
    found = []
    for wf_dir in WF_DIR_CANDIDATES:
        abs_dir = os.path.join(repo_path, wf_dir)
        for name in sorted(list_dir_exact(abs_dir)):
            _, ext = os.path.splitext(name)
            if ext.lower() in WF_EXTS:
                found.append((wf_dir + '/' + name, os.path.join(abs_dir, name)))
    return found


# =====================================================================
# 指标2 COPYRIGHT（2026-10-06 v2 模板化改版）
# 算法照搬参考/validate_tpl_match_v2.py（113 仓实测原型）；
# 规则语义以参考/copyright_metric_handoff.md 为唯一需求源。
# =====================================================================

# 版权模板配置表（单一数据源：mulan 4 条官方模板 + builtin 5 条 + custom 业务模板）
COPYRIGHT_TEMPLATE_TABLE = 'dim_copyright_template_config'

# 印刷模板识别（§4.4）："如何应用"附录的两种判定特征
# 2026-10-15 锚点放宽（问题2 拍板）：占位符风格从字面 [yyyy]+[name of copyright owner]
# 放宽到"Copyright 行含任意方括号占位符"（覆盖木兰附录的 [Year]/[name of copyright
# holder]/华为 [Year of First Publication]-[Year of Latest Update] 等写法）；
# 附录措辞从 licensed under the 放宽到 licensed under（覆盖木兰的无 the 写法）
_PRINTED_COPY_LINE_RE = re.compile(r'^\s*Copyright\b', re.I)
_PRINTED_PLACEHOLDER_RE = re.compile(
    r'Copyright.*\[[^\]\d][^\]]*\]', re.I)
# 注意 (\(c\))? 必须整体分组：裸写 \(c\)? 时 ? 只作用于最后的 \)，
# 语义变成"必须有(和c、)可选"，导致 'Copyright 2025 ...'（无(c)）全部漏配（2026-10-06 实测根因）
_PRINTED_FILLED_LINE_RE = re.compile(
    r'Copyright\s*(\(c\))?\s*\d{4}', re.I)
_APPENDIX_HINT_RE = re.compile(r'licensed under', re.I)
# 版权行括号组分类改写（2026-10-15）：[Year]/[yyyy]/[date] → {year}，
# 其余占位符（[name of copyright holder] 等）→ {owner}；版权行其余文字按字面保留
# （形态B 华为定制行的 owner "Huawei Technologies Co., Ltd." 与 "All Rights Reserved."
# 均严格比对，2026-10-15 拍板"版权行严格判"）
_BRACKET_GROUP_RE = re.compile(r'\[([^\]]*)\]')
_BRACKET_YEAR_WORDS = ('year', 'yyyy', 'date')
# 软件名行通配（2026-10-15 拍板）：'X is licensed under ...' 的 X 只验有内容、
# 不比对写什么（仓库软件名不规范不归版权合规指标管）；[Software Name] 占位符同语义
_SWNAME_DECL_RE = re.compile(r'^(.+?)\s+is licensed under\b', re.I)
# 代码围栏（2026-10-15）：附录模板以 ```text 代码块呈现时，闭合围栏即模板块终点
# （否则会吞进围栏后的中文注释行与正文标题，如 AgentSDK L69 "注意：模板中的[Year...]"）
_CODE_FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
# 注意 ^\s*：Apache 附录版权行自带缩进（如 3 空格），match() 锚定行首时缺它会漏配
_PRINTED_LINE_FILLED_RE = re.compile(
    r'^\s*Copyright\s*(\(c\))?\s*(\d{4})(?:\s*-\s*\d{4})?\s+(.+)$', re.I)
_SECTION_HEADER_RE = re.compile(r"^[A-Z][A-Z \d',:.]{8,}$")
# 条款主体结束标记（仅英文；木兰中文"条款结束"不计——木兰官方 LICENSE 为中英双全文，
# 计中文会把 45 个木兰仓全部误判多协议，2026-10-15 拍板）
_MULTI_LICENSE_END_RE = re.compile(r'END OF (?:THE )?TERMS AND CONDITIONS', re.I)


def load_copyright_templates(connection):
    """从 dim_copyright_template_config 加载 status=1 模板（启动时一次，逐仓查内存）。
    返回 {'mulan': {license_id: {template_id, pattern, pattern_the}},
          'set41': [(template_id, pattern), ...]}（set41 按 match_priority 升序，
          4+1 匹配集 = builtin + custom，符合任一即过）。
    表无有效行直接抛错退出（禁止静默降级，同 TOKEN_PERM 基准表模式）。"""
    sql = (f"SELECT template_id, template_type, license_ids, content, match_priority "
           f"FROM {COPYRIGHT_TEMPLATE_TABLE} WHERE status = 1")
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    if not rows:
        raise RuntimeError(f'{COPYRIGHT_TEMPLATE_TABLE} has no enabled rows (status=1)')
    mulan, set41 = {}, []
    for r in rows:
        content = r['content'] or ''
        if r['template_type'] == 'mulan':
            lic_ids = r.get('license_ids') or []
            if isinstance(lic_ids, str):  # Doris array<string> 兼容字符串返回
                try:
                    lic_ids = json.loads(lic_ids)
                except ValueError:
                    lic_ids = []
            entry = {
                'template_id': r['template_id'],
                'pattern': _tpl_pattern(content),
                # "去 the"变体容差（§4.6）：a copy of the Mulan PSL v2（官方原文无 the，
                # 实测 2 个文件）——主模板未中时重试一次
                'pattern_the': _tpl_pattern(content.replace('copy of Mulan', 'copy of the Mulan')),
            }
            for lid in lic_ids:
                mulan[lid] = entry
        elif r['template_type'] in ('builtin', 'custom'):
            set41.append((r['template_id'], _tpl_pattern(content), r['match_priority'] or 100))
    set41.sort(key=lambda x: (x[2], x[0]))
    return {'mulan': mulan, 'set41': [(t, p) for t, p, _ in set41]}


# =====================================================================
# 多协议判定（2026-10-15 问题5 拍板：LICENSE 存在多协议 → 整仓 NA）
# 信号1：license 扫描表现成结果（spdx AND/OR 表达式 + LICENSES/ 目录逐文件识别）
# 信号2：LICENSE 文本含 ≥2 处英文条款结束标记（兜 scancode 漏识别，如 403209
#        CANN 条款+Apache 全文只被识别出 Apache-2.0；木兰中文"条款结束"不计，
#        否则 45 个中英双全文木兰仓全部误判多协议）
# =====================================================================

LICENSE_SCAN_TABLE = 'dwi_rd_efc_security_license_scan'

# 木兰中英文版是同一协议（用户拍板）：mulanpsl-2.0-en / MulanPSL-2.0 / mulanpsl-2.0
# 统一映射；scancode 会把英文版拆成 LicenseRef-scancode-mulanpsl-2.0-en 伪 ID
_MULAN_ID_CANON = {
    'mulanpsl-2.0': 'MulanPSL-2.0', 'mulanpsl-1.0': 'MulanPSL-1.0',
    'mulanpubl-2.0': 'MulanPubL-2.0', 'mulanpubl-1.0': 'MulanPubL-1.0',
}


def _norm_license_id(raw):
    """协议 ID 归一：去 scancode LicenseRef-scancode- 前缀与 -en 后缀，
    木兰变体映射到规范 ID（中英文同协议）；其余原样返回。"""
    s = (raw or '').strip()
    low = re.sub(r'^licenseref-scancode-', '', s.lower())
    low = re.sub(r'-en$', '', low)
    return _MULAN_ID_CANON.get(low, s)


def _collect_license_protocols(lic_scan_entry):
    """信号1：从 license 扫描表现成结果提取协议 ID 集合。
    spdx 表达式按 AND/OR/括号拆分；LICENSES/ 目录逐文件识别结果并入
    （unknown-license-reference 记为'未识别协议'，与其他协议并存时参与 NA 判定）。
    无数据返回空集合（仅信号2生效）。"""
    if not lic_scan_entry:
        return set()
    ids = set()
    spdx = lic_scan_entry.get('spdx')
    if spdx:
        for tok in re.split(r'\s+(?:AND|OR)\s+|[()]', spdx):
            tok = tok.strip()
            if tok:
                nid = _norm_license_id(tok)
                ids.add('未识别协议' if nid.lower() == 'unknown-license-reference'
                        else nid)
    for f in lic_scan_entry.get('folder_files') or []:
        s = (f.get('spdx') or '').strip()
        if not s:
            continue
        nid = _norm_license_id(s)
        ids.add('未识别协议' if nid.lower() == 'unknown-license-reference' else nid)
    ids.discard('')
    return ids


def load_license_scan_results(connection):
    """加载 license 扫描表现成结果（每仓最新批次）：{repo_id: {'spdx','folder_files'}}。
    多协议判定信号1 数据源（2026-10-15）；依赖 DS 工作流中 license 扫描任务先于
    版权扫描执行。查询失败不阻断版权扫描（返回 {}，仅信号2 生效，记 WARN）。"""
    sql = ("SELECT t.repo_id, t.spdx, "
           "json_extract(t.detail, '$.folder_files_scanned') AS ff "
           f"FROM {LICENSE_SCAN_TABLE} t INNER JOIN ("
           f"SELECT repo_id, MAX(scan_time) AS mt FROM {LICENSE_SCAN_TABLE} "
           "GROUP BY repo_id) m ON t.repo_id = m.repo_id AND t.scan_time = m.mt")
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
    except Exception as e:
        print(f"WARN: load {LICENSE_SCAN_TABLE} failed ({e}); "
              f"multi-license signal-1 disabled", flush=True)
        return {}
    out = {}
    for r in rows:
        ff = r.get('ff')
        if isinstance(ff, str) and ff.strip():
            try:
                ff = json.loads(ff)
            except ValueError:
                ff = None
        if not isinstance(ff, list):
            ff = []
        out[r['repo_id']] = {'spdx': r.get('spdx'), 'folder_files': ff}
    return out


def find_license_file(repo_path):
    """LICENSE 文件定位（§4.2）：按序探测仓库根目录候选名（大小写敏感逐个试，
    list_dir_exact 保证 Windows 本地跑与 Linux 调度结果一致）。
    返回 (文件名, 文本)；找不到或不可读（含超 1MB）返回 (None, None) → 整仓 NA。"""
    entries = list_dir_exact(repo_path)
    for name in LICENSE_CANDIDATES:
        if name in entries:
            text = read_text_file(os.path.join(repo_path, name), LICENSE_READ_LIMIT)
            # 命中候选但不可读 → 无法确定模板，同 NA 处理
            return (name, text) if text is not None else (None, None)
    return None, None


def detect_mulan(lic_text):
    """木兰识别（§4.3：只判身份，不看字面有没有印模板）：
    12 条正则任一命中即木兰仓；匹配顺序 MulanPSL-2.0 → MulanPSL-1.0 →
    MulanPubL-2.0 → MulanPubL-1.0（v2 优先，负向前瞻防误判）。
    注意：对原文匹配、不做小写化——正则含大写 URL（license.coscl.org.cn/MulanPSL2），
    小写化会破坏大小写导致全漏（2026-10-06 实测 35 仓全漏的根因）。"""
    for lic_id in ('MulanPSL-2.0', 'MulanPSL-1.0', 'MulanPubL-2.0', 'MulanPubL-1.0'):
        for pat in MULAN_PATTERNS[lic_id]:
            if re.search(pat, lic_text):
                return lic_id
    return None


def extract_printed_template(lic_text):
    """印刷模板识别与提取（§4.4，2026-10-15 问题2 改版）：在 LICENSE 中找"如何应用"
    附录，判定特征满足其一：
      ① 占位符风格：Copyright 行含任意方括号占位符（[yyyy]/[Year]/
         [name of copyright owner]/[Year of First Publication] 等）
      ② 已填值风格：Copyright 行含 4 位年份，且其后 10 行内出现附录样板措辞
         （Licensed under ...，兼容木兰的无 the 写法）
    命中则提取连续非空行块（容忍块内单个空行；至连续空行/新章节标题/代码围栏闭合/
    EOF 止，上限 40 行）。改写规则（2026-10-15 拍板）：
      - 版权行：方括号占位符分类变量化（含 year/yyyy/date → {year}，其余 → {owner}），
        行内其余文字（owner 实名/All Rights Reserved. 等）按字面保留、严格比对；
        已填值风格年份整体变量化为 {year} {owner}
      - 软件名行：'X is licensed under ...' 的 X 一律通配（只验有内容不比对写什么）
    其余文字按字面保留（写错也照查，不做纠正）。返回编译后模板正则；
    找不到特征返回 None（走兜底集）。"""
    lines = lic_text.split('\n')
    start = None
    for i, ln in enumerate(lines):
        if not _PRINTED_COPY_LINE_RE.search(ln):
            continue
        if _PRINTED_PLACEHOLDER_RE.search(ln):
            start = i
            break
        if _PRINTED_FILLED_LINE_RE.search(ln):
            window = '\n'.join(lines[i + 1:i + 11])
            if _APPENDIX_HINT_RE.search(window):
                start = i
                break
    if start is None:
        return None
    block = [lines[start]]
    prev_blank = False
    for ln in lines[start + 1:start + 41]:
        s = ln.strip()
        if _CODE_FENCE_RE.match(s):
            break  # 附录模板代码块闭合（```text 围栏）→ 块结束
        if not s:
            if prev_blank:
                break  # 连续空行 → 块结束
            prev_blank = True
            continue
        prev_blank = False
        if _SECTION_HEADER_RE.match(s):
            break  # 明显的新章节标题（如 END OF TERMS AND CONDITIONS）
        block.append(ln)
    # --- 版权行改写（block[0]）---
    first = block[0]
    if _PRINTED_LINE_FILLED_RE.match(first):
        # 已填值风格：版权行整体变量化（年份+owner 均无法严格比对，沿用 v2 行为）
        block[0] = 'Copyright (c) {year} {owner}'
    elif _BRACKET_GROUP_RE.search(first):
        # 占位符风格：仅方括号占位符变量化，行内其余文字（owner 实名/
        # All Rights Reserved.）字面保留严格比对（2026-10-15 拍板"版权行严格判"）
        def _bracket_repl(m):
            inner = m.group(1).strip().lower()
            if any(w in inner for w in _BRACKET_YEAR_WORDS):
                return '{year}'
            return '{owner}'
        block[0] = _BRACKET_GROUP_RE.sub(_bracket_repl, first)
    # --- 软件名行通配（非版权行，'X is licensed under ...' → X 通配）---
    for j in range(1, len(block)):
        s = block[j].strip()
        m = _SWNAME_DECL_RE.match(s)
        if m:
            block[j] = '{software_name}' + s[m.end(1):]
    return _tpl_pattern('\n'.join(block))


def extract_header(content, ext):
    """头部提取（照搬 validate_tpl_match_v2.extract_header + §4.6.1 的 64 行窗口）：
    跳过 shebang/编码声明/空行，按扩展名取连续注释块（# 或 /* */ 或 //）。"""
    lines = content.split('\n')[:COPYRIGHT_HEADER_LINES]
    out, i = [], 0
    while i < len(lines) and (lines[i].startswith('#!') or 'coding' in lines[i][:40]
                              or not lines[i].strip()):
        i += 1
    if ext in ('.py', '.sh', '.bat'):
        while i < len(lines) and lines[i].lstrip().startswith('#'):
            out.append(lines[i])
            i += 1
    else:
        if i < len(lines) and lines[i].lstrip().startswith('/*'):
            out.append(lines[i])
            i += 1
            while i < len(lines):
                out.append(lines[i])
                if '*/' in lines[i]:
                    break
                i += 1
        elif i < len(lines) and lines[i].lstrip().startswith('//'):
            while i < len(lines) and lines[i].lstrip().startswith('//'):
                out.append(lines[i])
                i += 1
    return '\n'.join(out)


def extract_docstring_header(content):
    """.py docstring 兜底（§4.6.3，业务拍板：宽松处理）：常规注释头找不到版权行时，
    若 shebang/编码声明之后以 \"\"\" 或 ''' 开头，提取 docstring 内容作为头部。
    2026-10-13 修复：docstring 前的普通 # 注释行（如 pylint 指令）也跳过——
    对齐 copyright-tools header_engine._extract_block_header 的行为（# 注释不阻断
    block 起点搜索）；此前 ascendv1_distributed.py 因 # pylint 行导致木兰 docstring
    头读不到，被误判 no_copyright_line。"""
    lines = content.split('\n')[:COPYRIGHT_HEADER_LINES]
    i = 0
    while i < len(lines) and (lines[i].startswith('#!') or 'coding' in lines[i][:40]
                              or lines[i].lstrip().startswith('#')
                              or not lines[i].strip()):
        i += 1
    if i >= len(lines):
        return ''
    s = lines[i].lstrip()
    quote = next((q for q in ('"""', "'''") if s.startswith(q)), None)
    if quote is None:
        return ''
    rest = s[len(quote):]
    if quote in rest:  # 单行 docstring
        return rest.split(quote)[0]
    buf = [rest]
    for ln in lines[i + 1:]:
        if quote in ln:
            buf.append(ln.split(quote)[0])
            break
        buf.append(ln)
    return '\n'.join(buf)


def _clean_header_lines(header_text):
    """注释剥离（照搬 validate_tpl_match_v2.strip_lines）：去注释符（// # /* * rem
    <!-- -->）、丢弃装饰行，返回净行列表（每行内空白已折叠）。"""
    out = []
    for ln in header_text.split('\n'):
        s = ln.strip()
        s = re.sub(r'<!---?|-?-->', '', s).strip()  # HTML 注释（§4.6.2）
        s = re.sub(r'^/\*+|\*+/$', '', s).strip()
        s = re.sub(r'^//+|^#+|^\*', '', s).strip()
        s = re.sub(r'^rem\b', '', s, flags=re.I).strip()
        s = re.sub(r'\s+', ' ', s)
        if s and not re.fullmatch(r'[-=~_*#]+', s):
            out.append(s)
    return out


def _norm_text(text):
    """归一化（§4.6.4，两侧同规则）：丢弃装饰行与 This file is part of 前导行 →
    小写 → 去标点（保留逗号/句号，2026-10-07 对齐内部版权工具的标点级粒度）→
    (c) 归一去掉 → 折行合并（所有行拼成单字符串，空白折叠单空格）。"""
    kept = []
    for ln in text.split('\n'):
        s = re.sub(r'\s+', ' ', ln.strip())
        if not s or re.fullmatch(r'[-=~_*#]+', s):
            continue
        if s.lower().startswith('this file is part of'):
            continue
        kept.append(s)
    t = ' '.join(kept).lower()
    t = re.sub(r'[^a-z0-9,. ]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = t.replace('copyright c ', 'copyright ')
    # URL scheme 归一（2026-10-15 拍板，问题1）：xla-npu 等仓文件头写 https:// 而
    # LICENSE 模板写 http://（'/'':' 归一化中已剥为空格，只剩 https/http 词差异），
    # 两侧统一按 http 处理，协议文本一致性不受 scheme 写法影响
    t = re.sub(r'\bhttps\b', 'http', t)
    # 标点贴紧归一（2026-10-16）：模板侧占位符/连字符紧邻的标点归一后成"空格+标点"
    # （[Year]-[Year]. → year year .），而文件侧实写为紧贴（2026-2026. → 2026 2026.），
    # 一个空格之差导致按模板合法填写的文件全灭（MindIE-SD 350 文件误杀根因）；
    # 两侧同规则对称折叠，等价变换不影响既有匹配
    t = re.sub(r' +([.,;])', r'\1', t)
    return t


def _pattern_from_norm(joined):
    """归一化模板串（占位符已替换为 \x00 哨兵）→ 首锚定正则。
    2026-10-15 问题4 拍板：去 $ 尾锚定——文件头模板块之后允许附加说明行
    （如 ops-transformer graph_convert_moe_distribute_dispatch.py 尾部
    '# GE Converter for Graph Mode'，此前 $ 全锚定导致整模板误判不匹配）。"""
    pat = ''
    for seg in joined.split('\x00'):
        if seg == 'Y':
            pat += r'\d{4}'
        elif seg == 'V':
            pat += r'.+?'
        elif seg:
            pat += re.escape(seg)
    return re.compile('^' + pat, re.S)


def _tpl_pattern(tpl_text):
    r"""模板文本 → 正则（照搬 validate_tpl_match_v2.tpl_pattern）：
    归一化后占位符 {year}→\d{4}（年份只在底线检查，此处宽松），
    {owner}/{software_name}/{license_url}/{license_name}/{license_id}→.+?
    （有意不做协议一致性检查；software_name 只验占位不验内容，2026-10-06 拍板）。"""
    joined = _norm_text('\n'.join(tpl_text.strip().split('\n')))
    joined = joined.replace('year', '\x00Y\x00')
    # 2026-10-15 防御性补充：copyright-tools 官方原文用 {filename} 占位符
    # （生产种子为 {software_name}），一并通配，防止用原文初始化 dim 表时翻车
    for w in ('software name', 'filename', 'license url', 'license name', 'license id', 'owner'):
        joined = joined.replace(w, '\x00V\x00')
    return _pattern_from_norm(joined)


def read_head_text(path):
    """读文件头（模板化检查只看前 64 行头部窗口，读 256KB 头即可）：
    文件超 8MB 或不可读返回 None（分子分母均不计，沿用 2026-09-21 拍板）。"""
    try:
        if os.path.getsize(path) > COPYRIGHT_READ_LIMIT:
            return None
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(COPYRIGHT_HEAD_BYTES)
    except OSError:
        return None


def _find_copyright_line(clean_lines):
    """版权行底线检查（§4.5）：三正则任一命中返回该行文本，否则 None。"""
    for ln in clean_lines:
        if (RE_COPY_YF.search(ln) or RE_COPY_OF.search(ln) or RE_COPY_NC.search(ln)):
            return ln
    return None


def check_copyright_file(content, ext, branch, tpl_config):
    r"""单文件检查（§5）：返回 (matched, reason, template_id, copyright_line, banner)。
    检查链：头部提取（.py docstring 兜底）→ 版权行底线 → 模板正文全匹配。
    注意：版权行保留在归一化文本中、由模板占位符 \d{4}/.+? 吸收（原型 113 仓实测口径；
    版权行的年份/owner 严格校验由底线三正则把关，两者职责分离）。"""
    lines = _clean_header_lines(extract_header(content, ext))
    copyright_line = _find_copyright_line(lines) if lines else None
    if copyright_line is None and ext == '.py':
        # docstring 兜底：常规注释头找不到版权行时提取 docstring 作为头部
        ds_lines = _clean_header_lines(extract_docstring_header(content))
        if ds_lines:
            copyright_line = _find_copyright_line(ds_lines)
            lines = ds_lines
    if not lines:
        return False, 'no_header', None, None, False
    if copyright_line is None:
        # 有头部但三条版权行正则都不命中：含 copyright 字样 → owner_mismatch，
        # 完全没有 → no_copyright_line
        has_copyright_word = any(re.search(r'copyright', ln, re.I) for ln in lines)
        reason = 'owner_mismatch' if has_copyright_word else 'no_copyright_line'
        joined = _norm_text('\n'.join(lines))
        return False, reason, None, None, UPSTREAM_BANNER_MARK in joined
    joined = _norm_text('\n'.join(lines))
    banner = UPSTREAM_BANNER_MARK in joined
    if branch[0] == 'printed':
        if branch[1].search(joined):
            return True, None, 'license-printed', copyright_line, banner
        return False, 'template_mismatch', None, copyright_line, banner
    # 兜底集分支（2026-10-15 问题2 改版）：匹配集 = 4+1 + 木兰预置模板
    # （由 scan_copyright 按仓合成后经 branch[1] 传入），任一命中即过
    for tid, pat in branch[1]:
        if pat.search(joined):
            return True, None, tid, copyright_line, banner
    return False, 'template_mismatch', None, copyright_line, banner


def scan_copyright(repo_path, tracked_files, max_paths, tpl_config, lic_scan_entry=None):
    """版权合规 v2（design.md §5.2 + handoff §3，2026-10-15 五问题改版）：
    分支判定链：
      ① 无/不可读 LICENSE → 整仓 NA（missing）
      ② 多协议 → 整仓 NA（multi_license，问题5 拍板：信号1 license 扫描表现成
         结果 + 信号2 文本结构，木兰中英文归一为同一协议）
      ③ LICENSE 含"如何应用"声明模板（锚点放宽后）→ printed 严格匹配
         （版权行字面严格判；软件名行通配只验有内容，问题2 拍板）
      ④ 其余 → 兜底集 = 4+1 + 木兰预置模板，任一命中即过
    打分（问题3 拍板）：目标文件数 ≥50 → 扣分制 max(0, 10 − 0.2×不合格数)；
    <50 → 比例制 round(10×matched/total, 2)；detail 记 score_mode 区分。
    目标文件数=0 → NA；超限/不可读文件分子分母均不计（2026-09-21 拍板）。

    明细试验新增（2026-10-07）：第 4 返回值 unmatched_files，全量不合格文件清单
    [{file_path, ext, reason, is_banner}]，不受 max_paths 截断，落
    dwi_rd_efc_security_copyright_file_detail；NA 分支返回空清单。"""
    # --- 目标文件圈定：后缀过滤 + test/tests 精确段剔除（§4.1，不匹配 testing 等） ---
    excluded_test = 0
    target_files = []
    for rel in tracked_files:
        _, ext = os.path.splitext(rel)
        if ext.lower() not in COPYRIGHT_EXTS:
            continue
        segments = rel.split('/')
        if 'test' in segments or 'tests' in segments:
            excluded_test += 1
            continue
        target_files.append(rel)

    # --- LICENSE 定位（§4.2） ---
    license_name, license_text = find_license_file(repo_path)
    if license_text is None:
        return None, 1, {
            'target_file_count': len(target_files), 'matched_count': 0, 'by_ext': [],
            'license_file': None, 'license_type': 'missing',
            'excluded_test_file_count': excluded_test,
        }, []

    # --- 多协议判定（问题5，2026-10-15 拍板：整仓 NA） ---
    protocols = _collect_license_protocols(lic_scan_entry)
    struct_multi = len(_MULTI_LICENSE_END_RE.findall(license_text)) >= 2
    if len(protocols) >= 2 or struct_multi:
        licenses = set(protocols)
        if struct_multi:
            # 信号2：结构上检出多套正文但识别不全（如 403209 的 CANN 条款）
            licenses.add('未识别协议(条款结构)')
        return None, 1, {
            'target_file_count': len(target_files), 'matched_count': 0, 'by_ext': [],
            'license_file': license_name, 'license_type': 'multi',
            'na_reason': 'multi_license', 'licenses': sorted(licenses),
            'excluded_test_file_count': excluded_test,
        }, []

    # --- 分支判定（问题2 改版：去木兰优先，printed 优先 → 兜底集合并入木兰） ---
    lic_id = detect_mulan(license_text)
    printed_pat = extract_printed_template(license_text)
    if printed_pat is not None:
        branch = ('printed', printed_pat)
        lic_type = 'printed'
    else:
        patterns = list(tpl_config['set41'])
        if lic_id is not None:
            m = tpl_config['mulan'].get(lic_id)
            if m:
                # 木兰预置模板进兜底集（含"去 the"变体容差），软件名为占位符通配
                patterns.append((m['template_id'], m['pattern']))
                patterns.append((m['template_id'], m['pattern_the']))
        branch = ('set41', patterns)
        lic_type = 'mulan' if lic_id is not None else 'none'

    # --- 逐文件检查（§5） ---
    total = matched = oversize = 0
    by_ext = {}
    sample = None
    reasons = {}
    reason_samples = {}
    template_hits = {}
    unmatched_files = []   # 全量不合格清单（明细试验：不受 max_paths 截断）
    for rel in target_files:
        _, ext = os.path.splitext(rel)
        ext = ext.lower()
        content = read_head_text(os.path.join(repo_path, rel))
        if content is None:
            oversize += 1
            continue
        total += 1
        stat = by_ext.setdefault(ext, {'ext': ext, 'file_count': 0, 'matched_count': 0,
                                       'matched_files': []})
        stat['file_count'] += 1
        ok, reason, tpl_id, copy_line, banner = check_copyright_file(
            content, ext, branch, tpl_config)
        if ok:
            matched += 1
            stat['matched_count'] += 1
            if len(stat['matched_files']) < max_paths:
                stat['matched_files'].append(rel)
            if sample is None:
                sample = copy_line
            template_hits[tpl_id] = template_hits.get(tpl_id, 0) + 1
        else:
            reasons[reason] = reasons.get(reason, 0) + 1
            reason_samples.setdefault(reason, [])
            if len(reason_samples[reason]) < max_paths:
                reason_samples[reason].append(rel)
            # 全量记录不合格文件（明细试验）
            unmatched_files.append({'file_path': rel, 'ext': ext, 'reason': reason,
                                    'is_banner': 1 if banner else 0})
            if banner:
                # upstream_banner 仅标注分类，不改判定（§5：以主 reason 计不合格）
                reasons['upstream_banner'] = reasons.get('upstream_banner', 0) + 1
                reason_samples.setdefault('upstream_banner', [])
                if len(reason_samples['upstream_banner']) < max_paths:
                    reason_samples['upstream_banner'].append(rel)
    if total == 0:
        return None, 1, {
            'target_file_count': 0, 'matched_count': 0, 'by_ext': [],
            'license_file': license_name, 'license_type': lic_type,
            'mulan_license_id': lic_id, 'matched_template_id': None,
            'excluded_test_file_count': excluded_test,
        }, []
    # 双模式打分（2026-10-15 问题3 拍板）：
    #   ≥50 目标文件 → 扣分制（2026-10-08）：每个不合格文件扣 0.2 分，扣完为止
    #   <50 目标文件 → 比例制：round(10 × matched/total, 2)（小仓扣分制过严）
    # detail 记 score_mode 供明细页文案分叉
    if total < 50:
        score = round(10.0 * matched / total, 2)
        score_mode = 'ratio'
    else:
        score = round(max(0.0, 10.0 - 0.2 * (total - matched)), 2)
        score_mode = 'deduct'
    detail = {
        # 已有字段（语义不变）
        'target_file_count': total,
        'matched_count': matched,
        'by_ext': [by_ext[e] for e in sorted(by_ext)],
        'sample': sample,
        'oversize_file_count': oversize,
        # v2 新增（§7）
        'license_file': license_name,
        'license_type': lic_type,
        'mulan_license_id': lic_id,
        'matched_template_id': (max(template_hits, key=template_hits.get)
                                if template_hits else None),
        'excluded_test_file_count': excluded_test,
        'unmatched_reasons': reasons,
        'unmatched_samples': reason_samples,
        # 2026-10-15 问题3 新增：打分模式（ratio=比例制 deduct=扣分制）
        'score_mode': score_mode,
    }
    return score, 0, detail, unmatched_files


# =====================================================================
# 指标3 DANGEROUS_WF
# =====================================================================

def _collect_strings(obj, out):
    """递归收集 dict/list 中的字符串叶子值。"""
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_strings(v, out)


def _find_unsafe_checkout(obj):
    """递归查找 allow-unsafe-pr-checkout: true（布尔或 'true' 字符串均算）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() == UNSAFE_CHECKOUT_KEY:
                if v is True or str(v).strip().lower() == 'true':
                    return True
            if _find_unsafe_checkout(v):
                return True
    elif isinstance(obj, list):
        for it in obj:
            if _find_unsafe_checkout(it):
                return True
    return False


def scan_dangerous_wf(workflow_files, max_paths):
    """危险工作流：发现任一危险模式=0，未发现=10；无 workflow -> 10 分
    （2026-10-16 口径更新：原 NA 改满分）；
    解析失败文件 -> 整指标 NA（2026-09-21 拍板，结论不完整）（design.md §5.3）。
    检测项：① allow-unsafe-pr-checkout: true；② 不可信上下文变量直接使用或经 env 洗白。
    检测2 扫描范围（2026-10-10 漏检修复：ops-cv kirin_pre_smoke_action.yml 顶层
    env 引用 atomgit.head_ref 未检出）：job.steps + job.env + job.if + workflow 顶层 env。
    口径：env 中定义即算违规（严格口径，防"先注入 env 再引用"的洗白绕过，
    不做定义+使用数据流追踪）。"""
    if not workflow_files:
        return 10, 0, {'wf_file_count': 0, 'findings': [],
                       'full_score_reason': 'no_workflow_file'}
    if yaml is None:
        print("ERROR: PyYAML required for DANGEROUS_WF/TOKEN_PERM. pip install pyyaml", flush=True)
        raise RuntimeError('PyYAML missing')
    findings = []
    has_danger = False
    for rel, abs_path in workflow_files:
        finding = {'path': rel, 'unsafe_checkout': False, 'untrusted_context': [],
                   'untrusted_locations': [], 'reason': ''}
        findings.append(finding)
        content = read_text_file(abs_path, COPYRIGHT_READ_LIMIT)
        if content is None:
            finding['reason'] = 'parse_error: unreadable/oversize'
            continue
        try:
            doc = yaml.safe_load(content)
            if not isinstance(doc, dict):
                finding['reason'] = 'parse_error: not a yaml mapping'
                continue
        except yaml.YAMLError as e:
            finding['reason'] = f'parse_error: {str(e)[:200]}'
            continue
        # 检测1：不可信代码检出
        if _find_unsafe_checkout(doc):
            finding['unsafe_checkout'] = True
            has_danger = True
        # 检测2：不可信上下文变量（直接使用或 env 洗白）
        # 收集 (文本, 出处) 对：job steps 全量字符串 + job 级 env/if + workflow 顶层 env
        # job 提取复用 _extract_wf_jobs：覆盖 jobs 平铺 / stages.<stage>.jobs /
        # post|pre.jobs 三种结构（2026-09-29 盲区分析：原 doc.get('jobs') 漏检 39 处命中）
        text_locs = []

        def _collect(obj, where):
            strings = []
            _collect_strings(obj, strings)
            for s in strings:
                text_locs.append((s, where))

        top_env = doc.get('env')
        if isinstance(top_env, dict):
            _collect(top_env, 'env')
        for _jid, job in _extract_wf_jobs(doc):
            if isinstance(job.get('steps'), list):
                for i, step in enumerate(job['steps']):
                    _collect(step, f'steps[{i}]')
            if isinstance(job.get('env'), dict):
                _collect(job.get('env'), f'{_jid}.env')
            if isinstance(job.get('if'), (str, dict, list)):
                _collect(job.get('if'), f'{_jid}.if')
        hit_vars = []
        for t, where in text_locs:
            for v in UNTRUSTED_CONTEXT_VARS:
                if v in t:
                    entry = f'{v} @ {where}'
                    if v not in hit_vars:
                        hit_vars.append(v)
                    if entry not in finding['untrusted_locations']:
                        finding['untrusted_locations'].append(entry)
            for p in UNTRUSTED_CONTEXT_PREFIXES:
                if p in t:
                    entry = f'{p}...] @ {where}'
                    if p not in hit_vars:
                        hit_vars.append(p)
                    if entry not in finding['untrusted_locations']:
                        finding['untrusted_locations'].append(entry)
        if hit_vars:
            finding['untrusted_context'] = hit_vars[:max_paths]
            finding['untrusted_locations'] = finding['untrusted_locations'][:max_paths]
            has_danger = True
        elif finding['untrusted_locations']:
            finding['untrusted_locations'] = []
        if not finding['unsafe_checkout'] and not hit_vars:
            finding['reason'] = 'ok'
    # 解析失败文件 -> 整指标 NA（2026-09-21 拍板）：结论不完整不参与汇聚，
    # 不当 0 分（冤枉）也不当 10 分（漏检）
    parse_errors = [f for f in findings if str(f.get('reason', '')).startswith('parse_error')]
    if parse_errors:
        return None, 1, {
            'wf_file_count': len(workflow_files), 'findings': findings,
            'na_reason': 'parse_error files: ' + '; '.join(f['path'] for f in parse_errors[:10])}
    score = 0 if has_danger else 10
    return score, 0, {'wf_file_count': len(workflow_files), 'findings': findings}


# =====================================================================
# 指标4 TOKEN_PERM（2026-09-28 规则改版：按插件给定权限检查，取代 C5 五条规则）
# =====================================================================

# 插件权限基准表（单一配置源，Doris 配置表 sdi_sec_token_perm_plugin）：
#   official_path = uses 值截掉 @tag/sha/branch 后的完整路径（唯一键）
#   aliases 逗号分隔，兼容裸名历史写法（如 openlibing-pre-commit-action）
#   perm_project/perm_pr/perm_issue/perm_note/perm_repository = 各 scope 给定权限
#   is_active=0 停用（不参与检查，保留审计）
# 基准不含的 scope（如 id-token）一律视为 none：任何插件在该 scope 配 write 均算超权。
# 未命中本表的 uses 引用（codearts 插件/marketplace action/仓内 action）一律按只读
# 基准检查；.gitcode/workflows 相对路径的 workflow 复用引用不是插件，跳过。
# 追加/停用插件只改表数据（INSERT/UPDATE），不动脚本。
TOKEN_PERM_PLUGIN_TABLE = 'sdi_sec_token_perm_plugin'
# 豁免 scope（2026-10-10 拍板）：id-token:write 是 OIDC 联邦身份声明，不授予仓库资源
# 写权限，且平台 PR-pipeline 标准模板默认携带，不计入超权判定（write-all 仍直接违规，
# 因其覆盖 repository 等全部 scope）；detail_json 的 write_scopes 仍如实展示，仅不计违规。
TOKEN_PERM_EXEMPT_SCOPES = {'id-token'}
# 兜底默认基准：仅用于表里 perm_* 列为 NULL 的场景（正常 Insert 全量赋值，不走兜底）
TOKEN_PERM_FALLBACK_DEFAULT_BASELINE = {
    'project': 'none', 'pr': 'none', 'issue': 'none', 'note': 'none', 'repository': 'read',
}
TOKEN_PERM_PERM_COLUMNS = ('perm_project', 'perm_pr', 'perm_issue', 'perm_note',
                           'perm_repository')


def load_token_perm_baseline(connection):
    """从 Doris 配置表 sdi_sec_token_perm_plugin 构建匹配表。
    返回 (match_map, default_baseline)：match_map 含 official_path 与全部别名
    （is_active=0 跳过）；表无有效行直接抛错退出（禁止静默降级）。"""
    sql = (f"SELECT official_path, aliases, {', '.join(TOKEN_PERM_PERM_COLUMNS)}, is_active "
           f"FROM {TOKEN_PERM_PLUGIN_TABLE}")
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    fallback = TOKEN_PERM_FALLBACK_DEFAULT_BASELINE
    match_map = {}
    active_count = 0
    for row in rows:
        if not row.get('is_active', 1):
            continue
        active_count += 1
        scope_map = {
            'project': 'perm_project', 'pr': 'perm_pr', 'issue': 'perm_issue',
            'note': 'perm_note', 'repository': 'perm_repository',
        }
        baseline = {}
        for scope, col in scope_map.items():
            v = row.get(col)
            baseline[scope] = str(v).strip().lower() if v else fallback[scope]
        match_map[row['official_path']] = baseline
        for a in (row.get('aliases') or '').split(','):
            a = a.strip()
            if a:
                match_map[a] = baseline
    if active_count == 0:
        raise ValueError(
            f'{TOKEN_PERM_PLUGIN_TABLE} 无 is_active=1 的插件条目，'
            f'请先 INSERT 插件基准数据（见 docs/0912 建表与 Insert SQL）')
    return match_map, dict(fallback)


def _perm_to_str(p):
    """permissions 原值序列化为紧凑字符串（detail_json 展示用）。"""
    if p is None:
        return None
    if isinstance(p, str):
        return p
    if isinstance(p, dict):
        return ','.join(f'{k}:{v}' for k, v in sorted(p.items(), key=lambda x: str(x[0]))) or None
    return str(p)


def _parse_perm_block(p):
    """permissions 块 -> {scope: 权限值(小写)}。'read-all'/'write-all' 展开为 __all__ 键；
    未声明/空 -> None（None 表示走下层 fallback，最终落到默认全读）。"""
    if p is None:
        return None
    if isinstance(p, str):
        s = p.strip().lower()
        return {'__all__': s} if s else None
    if isinstance(p, dict) and p:
        return {str(k).strip().lower(): str(v).strip().lower() for k, v in p.items()}
    return None


def _perm_write_scopes(perm):
    """生效权限中值为 write 的 scope 集合（__all__ 保留原样，表示全 scope 写）。"""
    if not perm:
        return set()
    return {k for k, v in perm.items() if v == 'write'}


def _exceeds_baseline(write_scopes, baseline):
    """违规判定：任一 write scope 超出基准（基准 none->read 不罚，只罚 write；
    write-all 直接违规；豁免 scope（id-token）不计违规）。"""
    for s in write_scopes:
        if s == '__all__':
            return True
        if s in TOKEN_PERM_EXEMPT_SCOPES:
            continue
        if baseline.get(s, 'none') != 'write':
            return True
    return False


def _extract_wf_jobs(doc):
    """提取 job 列表 [(job_id, job_dict)]，兼容三种结构：
    ① jobs: 平铺；② stages.<stage>.jobs 嵌套；③ post.jobs（.gitcode 独有，
    现网 80 个文件使用，如 DrivingSDK 的 query_pipeline job）。"""
    jobs = []
    for container in (doc, doc.get('post') if isinstance(doc.get('post'), dict) else None,
                      doc.get('pre') if isinstance(doc.get('pre'), dict) else None):
        if not isinstance(container, dict):
            continue
        top_jobs = container.get('jobs')
        if isinstance(top_jobs, dict):
            for jid, j in top_jobs.items():
                if isinstance(j, dict):
                    jobs.append((str(jid), j))
        stages = container.get('stages')
        if isinstance(stages, dict):
            for st in stages.values():
                if not isinstance(st, dict):
                    continue
                st_jobs = st.get('jobs')
                if isinstance(st_jobs, dict):
                    for jid, j in st_jobs.items():
                        if isinstance(j, dict):
                            jobs.append((str(jid), j))
    return jobs


def _iter_step_uses(job):
    """job steps 下所有 uses 引用（插件识别只看 steps.uses）。"""
    out = []
    steps = job.get('steps')
    if isinstance(steps, list):
        for st in steps:
            if isinstance(st, dict) and isinstance(st.get('uses'), str):
                u = st['uses'].strip()
                if u:
                    out.append(u)
    return out


def _is_workflow_reuse(uses):
    """workflow_call 复用引用（.gitcode/workflows/*.yml 相对路径），不是插件，跳过。"""
    p = uses.split('@', 1)[0]
    return p.startswith('.') or p.endswith(('.yml', '.yaml'))


def scan_token_perm(workflow_files, baseline_map, max_paths):
    """令牌权限（design.md §5.4，2026-09-28 规则改版）：
      - 生效权限三层 fallback：job 级 > 顶层 > 默认（全读，不构成违规）
      - 违规判定：受检插件所在 job 的生效权限中任一 scope 为 write 且超出该插件
        给定基准（基准 none->read 不罚，只罚 write；豁免 scope id-token 不计违规，
        2026-10-10 拍板）。读写分离由此天然成立：
        job 为任一需要 write 的步骤配了 write，该 job 下所有基准不含 write 的
        受检插件全部违规（正确做法是拆 job 收窄）
      - 受检对象：命中基准表（官方路径/别名）的插件按给定基准检查；未命中名单的
        uses 引用一律按只读基准检查；workflow 复用引用（.yml 相对路径）跳过
      - 打分：违规插件按仓库级 Set 去重，score = max(0, 10 − 违规插件数)
      - 满分（2026-10-16 口径更新，原 NA 改满分）：无 workflow 文件 /
        有 workflow 但无任何受检插件引用（仅复用引用/纯脚本 job）
      - NA：全部文件解析失败（对齐 DANGEROUS_WF 2026-09-21
        拍板：结论不完整不参与汇聚）
    """
    if not workflow_files:
        return 10, 0, {'wf_file_count': 0, 'files': [],
                       'full_score_reason': 'no_workflow_file'}
    if yaml is None:
        raise RuntimeError('PyYAML missing')
    files_detail = []
    checked_set = set()
    violation_set = set()
    for rel, abs_path in workflow_files:
        item = {'path': rel, 'top_perm': None, 'jobs': {}}
        files_detail.append(item)
        content = read_text_file(abs_path, COPYRIGHT_READ_LIMIT)
        if content is None:
            item['parse_error'] = 'unreadable/oversize'
            continue
        try:
            doc = yaml.safe_load(content)
            if not isinstance(doc, dict):
                item['parse_error'] = 'not a yaml mapping'
                continue
        except yaml.YAMLError as e:
            item['parse_error'] = str(e)[:200]
            continue
        top_perm = _parse_perm_block(doc.get('permissions'))
        item['top_perm'] = _perm_to_str(doc.get('permissions'))
        for jid, job in _extract_wf_jobs(doc):
            job_perm = _parse_perm_block(job.get('permissions'))
            if job_perm is not None:
                effective, source = job_perm, 'job'
            elif top_perm is not None:
                effective, source = top_perm, 'top'
            else:
                effective, source = None, 'default'  # 默认全读
            write_scopes = _perm_write_scopes(effective)
            job_violations = []
            job_plugins = []
            for uses in _iter_step_uses(job):
                if _is_workflow_reuse(uses):
                    continue
                plugin_key = uses.split('@', 1)[0].strip()
                baseline = baseline_map.get(plugin_key)
                if baseline is None:
                    # 未命中名单：按只读基准（任何 write 均超权）
                    baseline = {}
                checked_set.add(plugin_key)
                if len(job_plugins) < max_paths:
                    job_plugins.append(plugin_key)
                if write_scopes and _exceeds_baseline(write_scopes, baseline):
                    violation_set.add(plugin_key)
                    if len(job_violations) < max_paths:
                        job_violations.append(plugin_key)
            if job_plugins:
                item['jobs'][jid] = {
                    'perm': _perm_to_str(effective if effective is not None
                                         else job.get('permissions')),
                    'perm_source': source,
                    'has_write': bool(write_scopes),
                    'write_scopes': sorted(write_scopes)[:max_paths],
                    'plugins': job_plugins,
                    'violations': job_violations,
                }
    parse_errors = [f for f in files_detail if 'parse_error' in f]
    if parse_errors:
        # 解析失败文件 -> 整指标 NA（对齐 DANGEROUS_WF 2026-09-21 拍板：结论不完整）
        return None, 1, {
            'wf_file_count': len(workflow_files), 'files': files_detail[:max_paths],
            'na_reason': 'parse_error files: ' + '; '.join(
                f['path'] for f in parse_errors[:10])}
    if not checked_set:
        # 有 workflow 但未引用任何受检插件（仅复用引用/纯脚本 job）
        # 2026-10-16 口径更新：原 NA 改满分
        return 10, 0, {'wf_file_count': len(workflow_files),
                       'files': files_detail[:max_paths],
                       'full_score_reason': 'no_checked_plugin'}
    score = max(0, 10 - len(violation_set))
    detail = {
        'wf_file_count': len(workflow_files),
        'files': files_detail[:max_paths],
        'stat': {'checked_count': len(checked_set),
                 'checked_plugins': sorted(checked_set)[:max_paths],
                 'violation_count': len(violation_set),
                 'violations': sorted(violation_set)},
    }
    return score, 0, detail


# =====================================================================
# 指标8 BRANCH_PROTECTION（v4.4，2026-09-28：仅采集 rebot.yaml 明细，得分由 D7 算）
# =====================================================================

def _find_yaml_key(obj, key):
    """在 yaml 解析结果中递归查找 key（lgtm_need_num 可能在嵌套层级），未命中返回 None。"""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = _find_yaml_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_yaml_key(v, key)
            if found is not None:
                return found
    return None


def scan_branch_protection(repo_path):
    """分支保护（design.md §5.8 v4.4）：平台默认管控，本脚本只读 rebot.yaml 明细——
    has_rebot_yaml / yaml_lgtm_config（连名带值）/ lgtm_need_num（数值化）。
    score=NULL + is_na=0 占位，最终 8/10 二元得分由 D7 SQL 结合 /lgtm 评论数据计算。"""
    yaml_path = os.path.join(repo_path, REBOT_YAML_PATH)
    if not os.path.isfile(yaml_path):
        return None, 0, {'has_rebot_yaml': 0, 'yaml_lgtm_config': None, 'lgtm_need_num': None}
    detail = {'has_rebot_yaml': 1, 'yaml_lgtm_config': None, 'lgtm_need_num': None}
    content = read_text_file(yaml_path, REBOT_YAML_READ_LIMIT)
    if content is None:
        detail['parse_error'] = 'read_failed'
        return None, 0, detail
    if yaml is None:
        detail['parse_error'] = 'pyyaml_missing'
        return None, 0, detail
    try:
        doc = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        detail['parse_error'] = 'yaml_parse_failed'
        detail['parse_message'] = str(exc)[:200]
        return None, 0, detail
    if doc is None:
        detail['parse_error'] = 'empty_yaml'
        return None, 0, detail
    raw_value = _find_yaml_key(doc, 'lgtm_need_num')
    if raw_value is None:
        return None, 0, detail  # yaml 存在但无该配置项，按默认 1 处理
    try:
        num = int(raw_value)
    except (TypeError, ValueError):
        detail['yaml_lgtm_config'] = f'lgtm_need_num={raw_value}'
        detail['parse_error'] = 'non_int_value'
        return None, 0, detail
    detail['yaml_lgtm_config'] = f'lgtm_need_num={num}'
    detail['lgtm_need_num'] = num
    return None, 0, detail


# =====================================================================
# 指标12 PACKAGING
# =====================================================================

# 指标12 PACKAGING 制品上传插件白名单（2026-10-06 规则：uses 值精确等于即命中）
PACKAGING_PLUGIN_USES = ('obs-upload', 'upload-artifact')


def _iter_uses_values(node):
    """递归遍历 YAML 节点，产出所有键名为 'uses' 的字符串值。

    workflow 结构：jobs.<job>.steps[].uses；支持 stages / pre / post 等任意嵌套。"""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'uses' and isinstance(v, str):
                yield v
            else:
                yield from _iter_uses_values(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_uses_values(item)


def scan_packaging(repo_url, workflow_files, euler_manifest, scan_failed_reason=None):
    """软件包发布（design.md §5.12 + 2026-10-08 规则）：workflow 内存在制品上传插件=10
    （YAML 键 uses 值精确等于 obs-upload / upload-artifact）；或仓库名命中 openEuler 包清单=10；
    均未命中=0 分（2026-10-08 口径调整：原 NA 改 0 分，视为未建立自动发包流程）。
    euler 清单不可用时 in_openeuler_project=NULL，仅按 workflow 判定。
    解析失败/不可读的 workflow 跳过并在 detail 记录 parse_errors。
    scan_failed_reason：仓级扫描失败原因（三态 repo_not_found/no_default_branch/
    checkout_failed，2026-10-19）。此时本地 workflow 不可读，插件分支无法验证
    （2选1只剩 euler 分支）：euler 命中 → 照常 10 分（匹配只依赖 repo_url 与
    DB 清单，不依赖本地仓）；euler 未命中 → 维持 NA（不能证伪插件分支，
    0 分口径以两分支都验证过为前提），detail 记录 scan_failed_reason。"""
    if yaml is None:
        print("ERROR: PyYAML required for PACKAGING. pip install pyyaml", flush=True)
        raise RuntimeError('PyYAML missing')
    publish_plugins = []
    parse_errors = []
    for rel, abs_path in workflow_files:
        content = read_text_file(abs_path, COPYRIGHT_READ_LIMIT)
        if content is None:
            parse_errors.append(f'{rel}: unreadable/oversize')
            continue
        try:
            doc = yaml.safe_load(content)
        except yaml.YAMLError as e:
            parse_errors.append(f'{rel}: {str(e)[:80]}')
            continue
        if not isinstance(doc, dict):
            parse_errors.append(f'{rel}: not a yaml mapping')
            continue
        for val in _iter_uses_values(doc):
            if val in PACKAGING_PLUGIN_USES:
                publish_plugins.append({'workflow': rel, 'uses': val})
    has_publish = len(publish_plugins) > 0
    in_euler = None
    euler_projects = None
    if euler_manifest is not None:
        _, repo_name = parse_repo_identity(repo_url)
        key = repo_name.lower() if repo_name and repo_name != 'unknown' else None
        if key and key in euler_manifest:
            in_euler = True
            euler_projects = sorted(set(euler_manifest[key]))
        else:
            in_euler = False
    if has_publish or in_euler:
        score, is_na = 10.0, 0
    elif scan_failed_reason:
        # 2026-10-19：仓扫描失败（三态）且 euler 未命中，插件分支不可验证 → 维持 NA
        detail = {
            'reason': scan_failed_reason,
            'message': (f'repo scan failed ({scan_failed_reason}); '
                        + ('euler manifest checked and unmatched' if in_euler is False
                           else 'euler manifest unavailable' if in_euler is None
                           else 'workflow branch unverifiable')),
            'in_openeuler_project': False if in_euler is not None else None,
            'scan_failed_reason': scan_failed_reason,
        }
        return None, 1, detail
    else:
        # 2026-10-08 口径调整：未检出制品上传插件且未命中 openEuler 包清单 -> 0 分（原 NA）
        score, is_na = 0.0, 0
    detail = {
        'has_workflow': len(workflow_files) > 0,
        'workflow_paths': [rel for rel, _ in workflow_files],
        'has_publish_plugin': has_publish,
        'publish_plugins': publish_plugins,
        'in_openeuler_project': in_euler,
        'openeuler_project': euler_projects,
        'parse_errors': parse_errors,
        'nightly': 'unsupported',  # Nightly 场景无法确定使用仓库，暂不支持（design.md §5.12）
    }
    if scan_failed_reason:
        # 扫描失败但 euler 命中得 10 分：detail 标注失败原因与判定来源，便于前端区分
        detail['scan_failed_reason'] = scan_failed_reason
        if not has_publish:
            detail['scored_via'] = 'euler_manifest_only'
    return score, is_na, detail


# =====================================================================
# 指标14 SAST（2026-09-30 规则改版）
# =====================================================================

def _scan_sast_precommit(repo_path):
    r"""扫描两处 pre-commit 配置，返回 (存在路径列表, {工具码: 证据路径})。
    hook id 采集 = YAML 解析 ∪ 逐行正则，始终并集：
    - YAML 解析覆盖标准写法（id: xxx，含 flow 映射 {id: xxx}）；
    - 正则兜底覆盖无空格写法 id:xxx（块级场景 PyYAML 会将其解析为纯字符串，
      解析"成功"但取不到 id，故不能只在解析失败时兜底）。"""
    found_paths = []
    hit_tools = {}
    for rel in SAST_PRECOMMIT_PATHS:
        abs_path = os.path.join(repo_path, rel)
        content = read_text_file(abs_path, COPYRIGHT_READ_LIMIT)
        if content is None:
            continue
        found_paths.append(rel)
        ids = set()
        if yaml is not None:
            try:
                doc = yaml.safe_load(content)
                if isinstance(doc, dict) and isinstance(doc.get('repos'), list):
                    for repo in doc['repos']:
                        if isinstance(repo, dict) and isinstance(repo.get('hooks'), list):
                            for h in repo['hooks']:
                                if isinstance(h, dict) and h.get('id') is not None:
                                    ids.add(str(h['id']).strip())
            except yaml.YAMLError:
                pass
        # 正则兜底：适配 id: xxx（有空格）与 id:xxx（无空格）两种写法
        for m in re.finditer(r'^\s*-?\s*id:\s*[\'"]?([^\s\'"]+)[\'"]?\s*$', content, re.M):
            ids.add(m.group(1))
        for code, _lang, pc_id, _wf_word in SAST_TOOLS:
            if pc_id in ids:
                hit_tools.setdefault(code, rel)
    return found_paths, hit_tools


def _scan_sast_workflow(workflow_files):
    """扫描 workflow 文件，返回 {工具码: (路径, 命中词)}，按单词边界匹配（不区分大小写）。"""
    hit_tools = {}
    if not workflow_files:
        return hit_tools
    word_res = [(code, wf_word, re.compile(rf'(?i)\b{re.escape(wf_word)}\b'))
                for code, _lang, _pc_id, wf_word in SAST_TOOLS]
    for rel, abs_path in workflow_files:
        content = read_text_file(abs_path, COPYRIGHT_READ_LIMIT)
        if content is None:
            continue
        for code, wf_word, wr in word_res:
            if code not in hit_tools and wr.search(content):
                hit_tools[code] = (rel, wf_word)
    return hit_tools


def scan_sast(repo_path, workflow_files):
    """SAST（2026-09-30 规则改版，design.md §5.14；2026-10-10 口径调整）：
    检查 pre-commit 配置（根目录或 pre-commit/ 目录，合并扫描）或 workflow 文件中
    是否使用 SAST 工具（8 种，不区分语言）。命中任一工具 = 10 分（多命中仍 10 分），
    未命中（含无 pre-commit 配置且无 workflow 文件）= 0 分（原 NA，2026-10-10 改 0 分）。"""
    precommit_paths, pc_hits = _scan_sast_precommit(repo_path)
    wf_hits = _scan_sast_workflow(workflow_files)
    has_precommit = bool(precommit_paths)
    has_workflow = bool(workflow_files)

    # 8 工具逐项检测结果（pre-commit / workflow 两个来源 + 汇总命中）
    tools = []
    for code, lang, _pc_id, _wf_word in SAST_TOOLS:
        in_pc = code in pc_hits
        in_wf = code in wf_hits
        tools.append({'tool': code, 'lang': lang,
                      'precommit': in_pc, 'workflow': in_wf, 'hit': in_pc or in_wf})
    # 命中证据（工具 × 来源，一条一证据）
    hits = []
    for code, path in pc_hits.items():
        lang = next(t[1] for t in SAST_TOOLS if t[0] == code)
        pc_id = next(t[2] for t in SAST_TOOLS if t[0] == code)
        hits.append({'tool': code, 'lang': lang, 'source': 'pre-commit',
                     'path': path, 'evidence': f'id: {pc_id}'})
    for code, (path, wf_word) in wf_hits.items():
        lang = next(t[1] for t in SAST_TOOLS if t[0] == code)
        hits.append({'tool': code, 'lang': lang, 'source': 'workflow',
                     'path': path, 'evidence': wf_word})
    hit_tools = sorted(set(pc_hits) | set(wf_hits))
    detail = {'has_precommit': has_precommit,
              'precommit_paths': precommit_paths,
              'wf_file_count': len(workflow_files),
              'tool_count': len(hit_tools),
              'hit_tools': hit_tools,
              'tools': tools,
              'hits': hits}
    return (10.0 if hit_tools else 0.0), 0, detail


# =====================================================================
# 指标15 SECURITY_POLICY
# =====================================================================

def _is_substantial_line(line):
    """实质性内容行：非空、非标题（# 开头）、非纯分隔线/符号。"""
    s = line.strip()
    if not s:
        return False
    if s.startswith('#'):
        return False
    if re.fullmatch(r'[-=_*~`|>+]+', s):
        return False
    return True


def fetch_community_security_policy_content(owner):
    """拉取社区集中安全策略文件内容（模块级缓存，每批次每社区仅一次网络请求）。
    返回 (content, error)：成功 content 为文件文本且 error=None；
    失败 content=None，error 为错误描述（含超限/网络异常）。"""
    if owner in _COMMUNITY_POLICY_CONTENT_CACHE:
        return _COMMUNITY_POLICY_CONTENT_CACHE[owner]
    conf = COMMUNITY_SECURITY_POLICY_FILES[owner]
    content, error = None, None
    try:
        req = urllib.request.Request(
            conf['url'], headers={'User-Agent': 'openlibing-security-scan'})
        with urllib.request.urlopen(req, timeout=COMMUNITY_POLICY_URL_TIMEOUT) as resp:
            raw = resp.read(SECURITY_MD_READ_LIMIT + 1)
        if len(raw) > SECURITY_MD_READ_LIMIT:
            error = f'community file exceeds read limit {SECURITY_MD_READ_LIMIT}'
        else:
            content = raw.decode('utf-8', errors='ignore')
    except Exception as e:  # 网络/超时/HTTP 错误统一降级为 0 分，不中断整批扫描
        error = f'{type(e).__name__}: {e}'
    _COMMUNITY_POLICY_CONTENT_CACHE[owner] = (content, error)
    return content, error


def _scan_community_security_policy(owner):
    """社区集中文件口径的 SECURITY_POLICY 扫描（三项加分逻辑与仓内 SECURITY.md 一致）。"""
    conf = COMMUNITY_SECURITY_POLICY_FILES[owner]
    content, error = fetch_community_security_policy_content(owner)
    if content is None:
        return 0.0, 0, {
            'file_path': conf['file_label'], 'source': 'community',
            'disclosure': False, 'link': False, 'free_text': False,
            'reason': 'community_file_fetch_failed', 'fetch_error': error,
        }
    lower = content.lower()
    disclosure = any(kw in lower for kw in DISCLOSURE_KEYWORDS)
    link = bool(CONTACT_RE.search(content))
    free_text = any(_is_substantial_line(line) for line in content.splitlines())
    detail = {'file_path': conf['file_label'], 'source': 'community',
              'disclosure': disclosure, 'link': link, 'free_text': free_text}
    score = float((1 if disclosure else 0) + (6 if link else 0) + (3 if free_text else 0))
    return score, 0, detail


def scan_security_policy(repo_path, root_entries, docs_entries, community_key=None):
    """安全策略（2026-10-12 B 口径，与明细展示配置一致）：
    无 SECURITY.md = 0；有 SECURITY.md 时三项独立加分：
    漏洞披露信息 +1、联系链接 +6、自由文本说明 +3。
    社区分支本期无数据源，已废弃；C3 旧口径（存在即 10 分）作废。
    2026-10-19 社区集中文件例外：community_key 非 None（owner 为 boostkit/openeuler）
    时不扫仓内 SECURITY.md，统一扫社区集中安全策略文件（URL 拉取 + 模块级缓存），
    拉取失败按 0 分并标 reason。"""
    if community_key:
        return _scan_community_security_policy(community_key)
    # 候选路径按优先级精确匹配（.gitcode/ 与 docs/ 目录单独列目录）
    gitcode_entries = list_dir_exact(os.path.join(repo_path, '.gitcode'))
    candidates = [
        ('.gitcode/SECURITY.md', 'SECURITY.md' in gitcode_entries, None),
        ('SECURITY.md', 'SECURITY.md' in root_entries, ''),
        ('docs/SECURITY.md', 'SECURITY.md' in docs_entries, 'docs'),
        ('security.md', 'security.md' in root_entries, ''),
    ]
    file_path = None
    for rel, hit, _sub in candidates:
        if hit:
            file_path = rel
            break
    if file_path is None:
        return 0.0, 0, {'file_path': None, 'disclosure': False, 'link': False, 'free_text': False}
    content = read_text_file(os.path.join(repo_path, file_path), SECURITY_MD_READ_LIMIT) or ''
    lower = content.lower()
    disclosure = any(kw in lower for kw in DISCLOSURE_KEYWORDS)
    link = bool(CONTACT_RE.search(content))
    free_text = any(_is_substantial_line(line) for line in content.splitlines())
    detail = {'file_path': file_path, 'disclosure': disclosure, 'link': link, 'free_text': free_text}
    score = float((1 if disclosure else 0) + (6 if link else 0) + (3 if free_text else 0))
    return score, 0, detail


# =====================================================================
# 主流程
# =====================================================================

def scan_one_repo(repo, repo_path, euler_manifest, max_paths, baseline_map, tpl_config,
                  lic_scan=None):
    """单仓 8 项扫描，返回 (metric_code -> (score, is_na, detail) 字典, 版权不合格文件全量清单)。

    明细试验（2026-10-07）：第 2 返回值 = scan_copyright 的 unmatched_files，
    供 main 落 dwi_rd_efc_security_copyright_file_detail。
    lic_scan：license 扫描表现成结果（{repo_id: {...}}，多协议判定信号1，
    2026-10-15 问题5；None/空时版权扫描仅用文本结构信号）。"""
    tracked_files = list_tracked_files(repo_path)
    root_entries = {f for f in tracked_files if '/' not in f}
    docs_entries = {f.split('/', 1)[1] for f in tracked_files if f.startswith('docs/')}
    workflow_files = find_workflow_files(repo_path)

    results = {}
    # scan_copyright 返回 4 元组 (score, is_na, detail, unmatched_files)，
    # 拆开装配：前 3 项进 results 字典，第 4 项作为本函数第 2 返回值
    cr_score, cr_na, cr_detail, unmatched_files = scan_copyright(
        repo_path, tracked_files, max_paths, tpl_config,
        lic_scan_entry=(lic_scan or {}).get(repo['repo_id']))
    results['COPYRIGHT'] = (cr_score, cr_na, cr_detail)
    results['DANGEROUS_WF'] = scan_dangerous_wf(workflow_files, max_paths)
    results['TOKEN_PERM'] = scan_token_perm(workflow_files, baseline_map, max_paths)
    results['BRANCH_PROTECTION'] = scan_branch_protection(repo_path)
    results['PACKAGING'] = scan_packaging(repo['repo_url'], workflow_files, euler_manifest)
    results['SAST'] = scan_sast(repo_path, workflow_files)
    # 2026-10-19 社区集中文件例外：owner 首段命中 boostkit/openeuler 时改扫社区统一文件
    owner_first = parse_repo_identity(repo['repo_url'])[0].split('/')[0].lower()
    community_key = owner_first if owner_first in COMMUNITY_SECURITY_POLICY_FILES else None
    results['SECURITY_POLICY'] = scan_security_policy(
        repo_path, root_entries, docs_entries, community_key=community_key)
    return results, unmatched_files


def build_na_results(reason, message):
    """三态异常（无默认分支/本地目录不存在/checkout 失败）时构造 7 指标全 NA 结果。

    口径与线上编码风格任务"写空记录不丢仓"对齐：score NULL + is_na=1 照常写库，
    detail 记录 reason/message 便于排查（design.md §3：NA 汇聚时剔除分子分母）。
    """
    detail = {'reason': reason, 'message': message}
    return {code: (None, 1, detail) for code in (
        'COPYRIGHT', 'DANGEROUS_WF', 'TOKEN_PERM',
        'BRANCH_PROTECTION', 'PACKAGING', 'SAST', 'SECURITY_POLICY')}


def main():
    args = parse_arguments()
    print("=== Debug Information ===")
    print(f"Command line arguments: {sys.argv}")

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
        euler_manifest = load_euler_manifest(connection, args.euler_table)
        # TOKEN_PERM 插件基准表（Doris 配置表 sdi_sec_token_perm_plugin，单一数据源）
        baseline_map, _default_bl = load_token_perm_baseline(connection)
        # COPYRIGHT 版权模板配置表（dim_copyright_template_config，启动时一次整表加载）
        tpl_config = load_copyright_templates(connection)
        # license 扫描表现成结果（多协议判定信号1，2026-10-15 问题5；
        # 依赖 DS 工作流中 license 扫描任务先于版权扫描执行）
        lic_scan = load_license_scan_results(connection)

        total = len(repos)
        metric_totals = {}  # 汇总各指标得分均值（便于快速质检）
        na_repo_count = 0   # 三态异常仓（8 指标全 NA 写库，不计失败）
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
                    # 三态①：sdi_repo_branch_info 无默认分支
                    na_reason = 'no_default_branch'
                    na_message = 'sdi_repo_branch_info has no default_branch for this repo'
                elif not os.path.isdir(repo_dir):
                    # 三态②：处理脚本未预 clone 该仓（目录不存在）
                    na_reason = 'repo_not_found'
                    na_message = f'local repo directory not found: {repo_dir}'
                elif not checkout_branch(repo_dir, default_branch):
                    # 三态③：checkout 默认分支失败（不 fetch，信任处理脚本已拉最新）
                    na_reason = 'checkout_failed'
                    na_message = f'git checkout {default_branch} failed in {repo_dir}'

                if na_reason:
                    results = build_na_results(na_reason, na_message)
                    # PACKAGING 例外（2026-10-19）：euler 包名匹配分支只依赖 repo_url
                    # 与 DB 清单，不依赖本地仓；三态失败时仍可判定（2选1口径）——
                    # 命中得 10 分，未命中维持 NA（插件分支不可验证，不能给 0 分）
                    results['PACKAGING'] = scan_packaging(
                        repo_url, [], euler_manifest, scan_failed_reason=na_reason)
                    copyright_unmatched = []
                    na_repo_count += 1
                    print(f"  NA ({na_reason}): {na_message}", flush=True)
                else:
                    results, copyright_unmatched = scan_one_repo(
                        repo, repo_dir, euler_manifest, args.max_detail_paths,
                        baseline_map, tpl_config, lic_scan)
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
                    # 明细试验：版权逐文件明细（辅助数据，失败不阻断主表）
                    detail_inserted = insert_copyright_file_rows(
                        repo_id, unified_scan_time,
                        copyright_unmatched, connection, etl_time)
                    scores_desc = ', '.join(
                        f"{m}={'NA' if results[m][1] else results[m][0]}" for m in results)
                    print(f"  inserted {inserted} rows"
                          f"{' + ' + str(detail_inserted) + ' file details' if detail_inserted else ''}"
                          f" | {scores_desc}", flush=True)
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
          f"{na_repo_count} NA repos (7 metrics all-NA; PACKAGING may still "
          f"score via euler manifest), scan_time={unified_scan_time}")
    for m in sorted(metric_totals):
        t = metric_totals[m]
        avg = round(t['sum'] / t['n'], 2) if t['n'] else None
        print(f"  {m:18s} avg_score={avg} scored={t['n']} na={t['na']}")
    if success_count == 0 and failure_count > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
