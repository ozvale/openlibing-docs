#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全许可证扫描 P2 脚本（代码安全检查评分看板 · design.md v4 §11.3 P2）

功能（指标1 LICENSE，规则见 design.md §5.1）：
  1. 从 Doris 读仓库清单：sdi_repo_info WHERE repo_id IN (operate_conf is_operate=1)，
     JOIN sdi_repo_branch_info 取默认分支（default_branch=true，只扫默认分支，
     口径与 openlibing-ops PR 看板 repo/branch/all 接口一致，2026-09-21 与 P1 同步）
  2. 复用"处理脚本"预 clone 的本地仓（2026-09-22 改版：不再 clone，与 DS
     "[GitCode]扫描代码仓编码风格"任务同款路径口径）：--repo-base-dir（默认
     /openlibing/git）下 {platform}/{owner}/{repo_name}；仅 checkout 默认分支
     （信任处理脚本已拉最新，不做 fetch）。三种异常均写 NA 行不丢仓：
       ① 本地目录不存在（pre-clone 失败）→ NA（reason=repo_not_found）
       ② 无默认分支信息 → NA（reason=no_default_branch）
       ③ checkout 失败 → NA（reason=checkout_failed）
     LICENSE 文件定位（2026-10-10 改版：对齐 OpenSSF scorecard v5.5.0
     checks/raw/license.go 口径，规则详见 find_license_target docstring）：
     仅根目录；大小写不敏感核心词 patent(s)/copy(ing|right)/LICEN[SC]E(S)，
     支持前后缀 SPDX ID（如 GPL-2.0-LICENCE）与扩展名白名单（license.yaml 拒收）；
     优先级：裸名 LICENSE 族 > 裸名其他核心词 > 带修饰变体 > 许可证文件夹
  3. 调 scancode-toolkit 扫描定位结果（扫描模式不变：单文件喂给 scancode；
     文件夹命中如 LICENSES/ 时逐个候选文件扫描取最高分，拍板 2026-10-10 A-b，
     多协议仓"任一有效协议即有证"）：
     scancode --license --copyright --license-text --license-text-diagnostics
              --json-pp <out.json> <license_file>
  4. 阶梯计分（递进式累加，2026-10-10 口径仲裁改版；无 NA，无许可证=0 分是有效得分）：
       检出许可证（基础分）                     -> 5
       + 内容与标准模板一致（scancode score==100）-> +3 = 8
       + copyright 年份/责任人替换正确           -> +1 = 9
       + 许可证类型 OSI/FSF 认证（SPDX 标志位）    -> +1 = 10
       无许可证文件/未检出许可证                   -> 0
     注：递进式高档位预设低档位条件——OSI/FSF 认证仅在模板一致且版权正确时
         才累加最后 1 分（原并联"只取满足的最高档"会让 OSI 认证许可证如
         Apache-2.0 绕过 copyright 检查直接 10 分，2026-10-10 拍板改递进累加）；
         分开记录 osi_approved_ok/fsf_libre_ok（2026-09-26 issue #126）保留。
         三态异常 NA 行（第 2 步）属工程兜底，与"恒非 NA"计分口径不冲突：
         score NULL + is_na=1，汇聚时剔除该仓权重（不丢仓）。
  5. 结果写 dwi_rd_efc_security_license_scan（UNIQUE KEY repo_id+scan_time，同批次重跑幂等覆盖）

OSI/FSF 判定数据源：SPDX 官方许可证清单
  https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json
  （忽略大小写匹配 licenseId 的 isOsiApproved / isFsfLibre 标志，满足任一累加最后 1 分至 10；
    2026-09-26 issue #126 改版：原"清单命中即满分"会误放非 OSI/非 FSF 许可证）。
  优先用 --spdx-list-file 本地文件；否则 URL 下载并缓存到工作目录
  （spdx_licenses.json）；下载失败且无缓存时 osi_fsf_ok / osi_approved_ok /
  fsf_libre_ok 置 NULL，该仓最高只能得 9 分（记 WARN，不阻断批次）。

运行前置：
  - Python3 + pip install pymysql scancode-toolkit（scancode 命令需在 PATH）
  - 本机 git 可用（仅本地 checkout，不联网）
  - "处理脚本"已完成预 clone（--repo-base-dir 下 {platform}/{owner}/{repo_name}）
  - Doris 已执行 dwi-dm层建表DDL.sql（dwi_rd_efc_security_license_scan 表）
  - 凭证不落脚本：Doris 认证从参数/环境变量注入，禁止写死

DS（DolphinScheduler）部署：脚本内 DS 占位符由 DS 全局文本替换注入，
本地裸跑时占位符未替换（仍以 $ 开头），自动回退 CLI 参数 / 环境变量。
"""

import difflib
import os
import sys
import re
import json
import argparse
import datetime
import subprocess
import tempfile
import urllib.request

# Windows 控制台编码保护
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
# 常量区（规则来源：design.md v4 §5.1）
# =====================================================================

# SPDX 官方许可证清单（OSI/FSF 判定，忽略大小写）
SPDX_LIST_URL = 'https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json'
SPDX_CACHE_NAME = 'spdx_licenses.json'

# scancode 同义许可证 key 归一化映射（2026-10-13 用户拍板）：
# 木兰宽松许可证第2版的中英文本在 scancode 知识库中是两条规则（mulanpsl-2.0 中文 /
# mulanpsl-2.0-en 英文），同一份 LICENSE（尤其中英双语正文）会检出两条甚至 AND 复合
# 一条，语义上是同一协议。统一归并为 mulanpsl-2.0（与 SPDX 官方 ID MulanPSL-2.0
# 大小写不敏感比对命中，isOsiApproved=1），明细展示去重 + OSI 档恢复可达。
LICENSE_KEY_ALIASES = {'mulanpsl-2.0-en': 'mulanpsl-2.0'}

# 华为版权声明（指标1 专用，宽松正则兼容空格有无；与指标2 COPYRIGHT 的 C1 无空格口径独立）
# §5.1 原文格式：Copyright (c) <年份> Huawei Technologies Co.（年份可替换）
HUAWEI_COPYRIGHT_RE = re.compile(r'Copyright\s*\(c\)\s*\d{4}\s+Huawei Technologies Co', re.IGNORECASE)

# LICENSE 文件定位（OpenSSF scorecard v5.5.0 checks/raw/license.go 移植，
# 2026-10-10 用户拍板：定位对齐 scorecard，扫描维持单文件模式不变）
# reLicenseFile：Go -> Python 等价转换（[[:digit:]] -> [0-9]）；与 Go 一致无结尾 $，
# 全串校验由 _license_path_of 完成（对应 Go getLicensePath）
RE_LICENSE_FILE = re.compile(
    r'(?i)'
    r'^(?P<lp>'
    # 可选前缀 SPDX ID（宽松匹配，如 GPL-2.0 as in GPL-2.0-LICENCE）
    r'(?P<preSpdx>([0-9A-Za-z]+)((([-_.])[0-9]{1,2}[A-Za-z]{0,1}){0,5})((([_-])?[0-9A-Za-z.])*))?'
    r'(?P<pre>[-_])?'                                                    # 可选前分隔符
    r'(?P<detectedFile>patent(s)?|copy(ing|right)|LICEN[SC]E(S)?)'        # 核心词（必须）
    r'(?P<suf>[-_./])?'                                                   # 可选后分隔符（/ 即文件夹）
    r'(?P<sufSpdx>([0-9A-Za-z]+)((([-_.])[0-9]{1,2}[A-Za-z]{0,1}){0,5})((([_-])?[0-9A-Za-z.])*))?'
    r'(?P<ext>[.]?[A-Za-z]+)?'                                            # 可选扩展名
    r')'
)
# reLicenseFileExts：扩展名白名单（scorecard 注释明确举例 license.yaml 被拒）
RE_LICENSE_EXTS = re.compile(
    r'(?i)(\.adoc|\.asc|\.doc(x)?|\.ext|\.html|\.markdown|\.md|\.rst|\.txt|\.xml)')
# 裸名核心词优先级（拍板 B-ii）：LICENSE 族（含英式/复数）> 其他核心词
CORE_WORDS_TIER1 = frozenset(('license', 'licence', 'licenses', 'licences'))
CORE_WORDS_TIER2 = frozenset(('copying', 'copyright', 'patent', 'patents'))
# 文件夹命中的候选文件扫描上限（防御性：正常 LICENSES/ 目录 2-5 个文件）
MAX_FOLDER_FILES = 20

LICENSE_READ_LIMIT = 4 * 1024 * 1024     # 4MB：LICENSE 文件远小于此，超限视为异常
RAW_JSON_LIMIT = 1024 * 1024             # raw_json 落库截断上限（1MB）

# scancode 单文件扫描超时（秒）
SCANCDE_TIMEOUT = 300

# Doris 目标表（dwi-dm层建表DDL.sql [5]）
TARGET_TABLE = 'dwi_rd_efc_security_license_scan'

# 处理脚本预 clone 的本地仓根目录（与 DS"[GitCode]扫描代码仓编码风格"任务一致）
DEFAULT_REPO_BASE_DIR = '/openlibing/git'


# =====================================================================
# 参数与环境（DS 凭证注入与 P1 同款：生产编码风格任务同构）
# =====================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Security license scan (P2, scancode) -> dwi_rd_efc_security_license_scan')
    parser.add_argument('--doris-url', default=None,
                        help='Doris JDBC URL（本地调试用；DS 运行时由占位符注入，无需传）')
    parser.add_argument('--doris-username', default=None, help='Doris 用户名（本地调试用）')
    parser.add_argument('--doris-password', default=None, help='Doris 密码（本地调试用）')
    parser.add_argument('--repo-ids', default=None,
                        help='逗号分隔的 repo_id 过滤列表（调试单仓用）')
    parser.add_argument('--repo-base-dir', default=DEFAULT_REPO_BASE_DIR,
                        help='处理脚本预 clone 的本地仓根目录（默认 /openlibing/git），'
                             '仓路径 = {base}/{platform}/{owner}/{repo_name}')
    parser.add_argument('--work-dir', default=None,
                        help='scancode 输出与 SPDX 缓存工作目录（不再 clone）；'
                             '缺省 系统临时目录/security_license_scan')
    parser.add_argument('--spdx-list-file', default=None,
                        help='SPDX 许可证清单本地 JSON 文件（离线环境用）；缺省 URL 下载并缓存')
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
    清单口径（2026-09-22 与 P1 同步）：只扫默认分支（sdi_repo_branch_info.default_branch，
    与 ops PR 看板 repo/branch/all 口径一致）；不再 clone，无需平台凭证。
    返回行含 repo_id / repo_url / platform / default_branch。
    2026-10-06 起加 platform='gitcode' 过滤（与 P1 文件扫描脚本同口径，
    安全指标仅评估 GitCode 仓；2026-10-10 合入生产副本）。"""
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
    no_branch_count = sum(1 for r in rows if not r.get('default_branch'))
    print(f"Loaded {len(rows)} repos (is_operate=1, platform=gitcode), "
          f"{no_branch_count} without default_branch (will be NA)")
    return rows


def insert_license_row(connection, row):
    """UNIQUE KEY (repo_id, scan_time)，同批次重跑自动覆盖（幂等）。失败重试 1 次。"""
    sql = (f"INSERT INTO {TARGET_TABLE} "
           "(repo_id, scan_time, repo_url, spdx, has_license, template_match, copyright_ok, "
           "osi_fsf_ok, detail, raw_json, score, is_na, etl_time) "
           "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    last_err = None
    for attempt in (1, 2):
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (
                    row['repo_id'], row['scan_time'], row['repo_url'], row['spdx'],
                    row['has_license'], row['template_match'], row['copyright_ok'],
                    row['osi_fsf_ok'], row['detail'], row['raw_json'],
                    row['score'], row['is_na'], row['etl_time']))
            connection.commit()
            return True
        except Exception as e:
            last_err = e
            try:
                connection.rollback()
            except Exception:
                pass
            print(f"  insert attempt {attempt} failed: {e}", flush=True)
    raise last_err


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
    -c safe.directory=* 跳过 dubious ownership 检查（处理脚本 clone 的仓所有权可能不同）。"""
    git_safe_args = ['-c', 'safe.directory=*']
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


# =====================================================================
# SPDX 清单（OSI/FSF 判定）
# =====================================================================

def load_spdx_map(spdx_list_file, work_dir):
    """加载 SPDX 官方清单 {licenseId_lower: {'osi': isOsiApproved, 'fsf': isFsfLibre}}。
    优先级：--spdx-list-file > URL 下载（缓存 work_dir/spdx_licenses.json）> 缓存文件。
    全部失败返回 None（osi_fsf_ok/osi_approved_ok/fsf_libre_ok 置 NULL，不阻断）。
    2026-09-26（issue #126）：OSI/FSF 改按清单 isOsiApproved/isFsfLibre 标志位判定，
    替代原"清单命中即 10 分"——原口径会把非 OSI/非 FSF 许可证（如 CC-BY-NC）误判满分。"""
    def _parse(text):
        data = json.loads(text)
        ids = {}
        for lic in data.get('licenses', []):
            lid = lic.get('licenseId')
            if lid:
                ids[str(lid).strip().lower()] = {
                    'osi': bool(lic.get('isOsiApproved')),
                    'fsf': bool(lic.get('isFsfLibre')),
                }
        return ids

    if spdx_list_file:
        try:
            with open(spdx_list_file, 'r', encoding='utf-8') as f:
                ids = _parse(f.read())
            if ids:
                print(f"Loaded SPDX list from {spdx_list_file}: {len(ids)} license ids")
                return ids
        except Exception as e:
            print(f"WARN: failed to read --spdx-list-file {spdx_list_file}: {e}")

    cache_path = os.path.join(work_dir, SPDX_CACHE_NAME)
    # 尝试在线刷新；失败则回退本地缓存
    try:
        print(f"Downloading SPDX license list from {SPDX_LIST_URL} ...")
        req = urllib.request.Request(SPDX_LIST_URL, headers={'User-Agent': 'security-license-scan/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode('utf-8')
        ids = _parse(text)
        if ids:
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    f.write(text)
            except OSError:
                pass
            print(f"Loaded SPDX list from URL: {len(ids)} license ids (cached at {cache_path})")
            return ids
    except Exception as e:
        print(f"WARN: download SPDX list failed: {e}")

    if os.path.isfile(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                ids = _parse(f.read())
            if ids:
                print(f"Loaded SPDX list from cache: {len(ids)} license ids")
                return ids
        except Exception as e:
            print(f"WARN: failed to read SPDX cache {cache_path}: {e}")

    print("WARN: SPDX list unavailable. osi_fsf_ok/osi_approved_ok/fsf_libre_ok "
          "will be NULL and score capped at 9.")
    return None


# =====================================================================
# LICENSE 扫描
# =====================================================================

def _spdx_id_of(m):
    """scorecard getSpdxID 移植：preSpdx 优先于 sufSpdx；UN 特例归一为 UNLICENSE
    （unlicense 的 'un' 会被宽松 SPDX 组捕获，映射不到清单里的 'Unlicense'）。"""
    if m.group('preSpdx'):
        return 'UNLICENSE' if m.group('preSpdx').upper() == 'UN' else m.group('preSpdx')
    if m.group('sufSpdx'):
        return 'UNLICENSE' if m.group('sufSpdx').upper() == 'UN' else m.group('sufSpdx')
    return ''


def _ext_of(filename, m):
    """scorecard getExt 移植：filepath.Ext 等价（最后一个点起、含点，无点为空）；
    扩展名吞掉核心词时回空（Go: strings.Contains(ext, detectedFile)）。"""
    i = filename.rfind('.')
    ext = filename[i:] if i >= 0 else ''
    if ext and m.group('detectedFile') in ext:
        return ''
    return ext


def _folder_of(m):
    """scorecard getFolder 移植：后分隔符为 / 时视为许可证文件夹（如 LICENSES/）。"""
    return m.group('detectedFile') + m.group('suf') if m.group('suf') == '/' else ''


def _extension_ok(ext):
    """scorecard extensionOK 移植：无扩展名放行；有则须命中白名单。"""
    if ext == '':
        return True
    return RE_LICENSE_EXTS.search(ext) is not None


RE_SPDX_DOT_DIGIT = re.compile(r'\.[0-9]')


def _validate_spdx_and_ext(m, spdx, ext):
    """scorecard validateSpdxIDAndExt 移植：SPDX ID 与扩展名的歧义消解。
    - ext 吞掉 spdx（如 license.yaml 的 yaml 同时被两组捕获）→ spdx 置空
    - spdx 吞掉 ext 且 ext 不在白名单而 spdx 含 .数字（如 CANN-V2.0 的 .0）→ ext 置空
    - spdx 吞掉 ext 且可拆 → 从 spdx 中剔除 ext
    - ext 与正则 ext 组不一致 → 把 ext 组内容拼回 spdx"""
    if spdx == '':
        return spdx, ext
    if ext != '' and spdx in ext:
        spdx = ''
    if ext != '' and spdx != '' and ext in spdx:
        if not _extension_ok(ext) and RE_SPDX_DOT_DIGIT.search(spdx):
            ext = ''
        else:
            spdx = spdx.replace(ext, '')
    elif ext != '' and spdx != '' and ext != spdx:
        if ext != (m.group('ext') or ''):
            spdx += m.group('ext') or ''
    return spdx, ext


def _license_path_of(m, val, spdx, ext):
    """scorecard getLicensePath 移植：匹配段须覆盖全串（lp==val），
    文件夹/SPDX 佐证可豁免一次（lp+ext==val），扩展名白名单最后把关。"""
    lp = m.group('lp')
    if lp != val:
        if _folder_of(m) == '' and spdx == '':
            return ''
        if lp + ext == val:
            return lp + ext
        return ''
    if not _extension_ok(ext):
        return ''
    return lp


def check_license_name(lf_name):
    """scorecard checkLicense 移植：判定文件名/路径名是否为许可证条目。
    返回 (license_path, spdx_id)；未命中返回 ('', '')。
    裸名快路径（整体等于核心词，如 License/COPYING）免扩展名/SPDX 校验直接命中，
    返回值保留原始大小写。"""
    m = RE_LICENSE_FILE.match(lf_name)
    if not m:
        return '', ''
    detected = m.group('detectedFile')
    if lf_name == detected:
        return detected, ''
    spdx = _spdx_id_of(m)
    ext = _ext_of(lf_name, m)
    spdx, ext = _validate_spdx_and_ext(m, spdx, ext)
    path = _license_path_of(m, lf_name, spdx, ext)
    if path == '':
        return '', ''
    return path, spdx


def find_license_target(repo_path):
    """根目录 LICENSE 定位（scorecard v5.5.0 口径，2026-10-10 用户拍板）：
      R1 仅根目录（^ 锚定），子目录里的 LICENSE 不算；
      R2 核心词（大小写不敏感）：patent(s)/copy(ing|right)/licen[sc]e(s)；
      R3 文件名过 scorecard 正则（含前后缀 SPDX ID、分隔符、扩展名）；
      R4 扩展名白名单：.adoc .asc .doc(x) .ext .html .markdown .md .rst .txt .xml；
      R5 SPDX/扩展名歧义消解（_validate_spdx_and_ext）；
      R6 scorecard 宽松性照抄不收紧（如 NOTALICENSE 也会命中）；
      R7 隐藏条目（点开头）不参与（拍板 C-ii）；
      R8 优先级（拍板 B-ii）：裸名 LICENSE 族 > 裸名其他核心词 > 带修饰变体
         > 许可证文件夹；同层多命中按名称大小写不敏感排序取首个
         （scorecard 遍历非确定，此处强制确定性保证同批次幂等）。
    返回 ('file', rel_path) / ('folder', folder_name, [folder内候选rel_path]) / None。
    文件夹候选：单层文件、全路径（folder/name）过 scorecard 正则（如
    LICENSES/GPL-V2.0）；scorecard 对文件夹内容是 TODO 忽略，本脚本按拍板
    A-b 交由调用方逐文件扫描取最高分。"""
    try:
        entries = sorted(os.listdir(repo_path), key=lambda s: (s.lower(), s))
    except OSError:
        return None
    tier1, tier2, tier3, folder = [], [], [], None
    for name in entries:
        if name.startswith('.'):
            continue                                    # R7：隐藏条目排除
        full = os.path.join(repo_path, name)
        if os.path.isdir(full):
            if folder is None and check_license_name(name + '/')[0]:
                folder = name
        elif check_license_name(name)[0]:
            low = name.lower()
            if low in CORE_WORDS_TIER1:
                tier1.append(name)
            elif low in CORE_WORDS_TIER2:
                tier2.append(name)
            else:
                tier3.append(name)
    for tier in (tier1, tier2, tier3):
        if tier:
            return 'file', tier[0]
    if folder is None:
        return None
    try:
        inner = sorted(os.listdir(os.path.join(repo_path, folder)),
                       key=lambda s: (s.lower(), s))
    except OSError:
        return None
    cands = []
    for n in inner:
        if n.startswith('.'):
            continue
        if os.path.isfile(os.path.join(repo_path, folder, n)) \
                and check_license_name(f'{folder}/{n}')[0]:
            cands.append(f'{folder}/{n}')
    if not cands:
        return None
    return 'folder', folder, cands


def normalize_license_expr(expr):
    """同义 key 归一化（LICENSE_KEY_ALIASES）；AND 复合表达式逐分量归一化。"""
    if not expr:
        return expr
    parts = [p.strip() for p in re.split(r'\s+AND\s+', expr)]
    parts = [LICENSE_KEY_ALIASES.get(p.lower(), p) for p in parts]
    return ' AND '.join(parts)


def dedupe_detections(norm):
    """检出项归一化去重（2026-10-13 拍板：en/zh 双路木兰视为同一协议）：
    - 每项 key 先过 normalize_license_expr；
    - 单表达式按 key 分组取最高分一条；
    - AND 复合表达式若全部分量已被单表达式检出覆盖则整体丢弃
      （如 "mulanpsl-2.0 AND mulanpsl-2.0-en" 被 mulanpsl-2.0 单条覆盖）；
      未被全覆盖的复合表达式保留（真正的多协议混排文本）。
    返回新列表（dict 插入序即首见最高分项顺序，确定性）。"""
    best_by_key = {}
    composites = []
    passthrough = []
    for x in norm:
        expr = x.get('spdx') or ''
        if not expr:
            passthrough.append(x)
            continue
        x = dict(x, spdx=normalize_license_expr(expr))
        comps = [c for c in x['spdx'].split(' AND ') if c]
        if len(comps) > 1:
            composites.append(x)
        else:
            k = comps[0].lower()
            if k not in best_by_key or x['score'] > best_by_key[k]['score']:
                best_by_key[k] = x
    single_keys = set(best_by_key)
    result = list(best_by_key.values()) + passthrough
    for x in composites:
        comps = set(c.lower() for c in x['spdx'].split(' AND ') if c)
        if comps <= single_keys:
            continue
        result.append(x)
    return result


def check_scancode_available():
    """scancode 命令可用性检查（P2 硬依赖）。"""
    try:
        result = subprocess.run(['scancode', '--version'], capture_output=True, text=True,
                                timeout=60, errors='replace')
        if result.returncode == 0:
            version = (result.stdout or '').strip().splitlines()[0] if result.stdout else 'unknown'
            print(f"scancode available: {version}")
            return True
    except FileNotFoundError:
        pass
    except Exception:
        pass
    print("ERROR: scancode command not found. Install: pip install scancode-toolkit")
    return False


def run_scancode(license_file_abs, out_json_path):
    """执行 scancode 单文件扫描，返回解析后的 dict 或 None（失败/超时）。"""
    cmd = ['scancode', '--license', '--copyright', '--license-text',
           '--license-text-diagnostics', '--json-pp', out_json_path, license_file_abs]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=SCANCDE_TIMEOUT, errors='replace')
        if result.returncode != 0:
            print(f"  scancode failed: {(result.stderr or '').strip()[-300:]}", flush=True)
            return None
    except subprocess.TimeoutExpired:
        print(f"  scancode timed out ({SCANCDE_TIMEOUT}s)", flush=True)
        return None
    except Exception as e:
        print(f"  scancode error: {e}", flush=True)
        return None
    try:
        with open(out_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  parse scancode json failed: {e}", flush=True)
        return None


def _no_license_row():
    """无许可证/未检出兜底行（0 分形态；detail 由调用方覆写原因）。"""
    return {
        'spdx': None, 'has_license': 0, 'template_match': None,
        'copyright_ok': None, 'osi_fsf_ok': None,
        'osi_approved_ok': None, 'fsf_libre_ok': None,
        'detail': {'reason': 'no_license_file'}, 'raw_json': None,
    }


# ---------------------------------------------------------------------------
# 模板差异对照（2026-10-23）：官方模板全文 vs 文件命中文本，逐行并排 diff。
# 数据源：scancode 安装目录自带官方模板（licensedcode/data/licenses/<key>.LICENSE，
# 离线可读）+ match 的 matched_text（--license-text 产生）。
# 页面消费：detail.template_diff.rows → Java 注入 diffRows → conf"模板差异对照"表格。
# ---------------------------------------------------------------------------
DIFF_TEXT_LIMIT = 160      # 单元格文本截断长度
DIFF_ROW_LIMIT = 40        # 对照行数上限（超出截断）
DIFF_RUN_LIMIT = 6         # 连续缺失/多出段逐行展示上限（超出折叠）
DIFF_CONTEXT_LINES = 1     # 变更区保留的相同上下文行数


def _diff_clip(text):
    text = (text or '').rstrip()
    return text[:DIFF_TEXT_LIMIT] + '…' if len(text) > DIFF_TEXT_LIMIT else text


# 2026-10-24 生产批次复核（repo 400030 木兰，coverage 99.43 却撞 40 行上限）：
# difflib 行全等比较使纯空白差异（如 "1.   定义" 3 空格 vs "1. 定义" 1 空格、行首缩进）
# 全部标成 mod，还诱发标题/URL 行 del+add 错位配对，被检查人满屏琥珀却找不到实质问题。
# 二次复核：压成单空格仍放行"模板引号后有空格/文件没有"这类肉眼不可见的差异
# （"“软件” 是指" vs "“软件”是指"），页面两列看似相同却标 mod。
# 最终口径：比对剔除全部空白字符，展示保留原文——只标真实字符差异
# （如半角/全角标点、增删内容），score 判定仍由 scancode 负责，diff 仅用于展示。
_WS_RUN_RE = re.compile(r'\s+')


def _diff_norm(line):
    """diff 行级相等判定用的空白归一化：剔除全部空白（仅用于比对，不影响展示文本）。"""
    return _WS_RUN_RE.sub('', line)


def _find_template_text(license_key):
    """按 scancode license key 读官方模板全文；环境无 licensedcode 或无该模板返回 None。"""
    if not license_key:
        return None
    try:
        import licensedcode
    except ImportError:
        return None
    path = os.path.join(os.path.dirname(licensedcode.__file__),
                        'data', 'licenses', f'{license_key}.LICENSE')
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
    except OSError:
        return None
    # licensedcode 模板文件是 YAML front matter（首行 --- 到下一个 --- 行）+ 许可证正文，
    # 2026-10-23 E2E 实测（mit.LICENSE 前 23 行为元数据），diff 只用正文
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            text = text[end + 4:]
    return text.lstrip('\n')


def _build_template_diff(best_match, license_text):
    """官方模板 vs LICENSE 全文逐行并排对照，返回 detail.template_diff 结构；无法生成返回 None。

    文件侧用 LICENSE 全文而非 scancode matched_text（2026-10-23 E2E 实测两个盲区）：
    matched_text 只含命中区域，① 模板有而文件缺的内容不会出现；② 命中区域外的
    多出内容（如末尾追加条款、前导声明）也不会出现。全文对照两者都能照出，
    且行号天然是文件真实行号，无需 start_line 偏移。

    rows[].status：del=模板有文件缺（红）｜add=文件多出（琥珀）｜mod=两边不一致（琥珀）｜
                   same=一致（上下文）｜omit=相同内容折叠占位。行号列 = 文件内行号
                   （del 行无文件行号，显示 —）。"""
    tpl_text = _find_template_text(best_match.get('license_expression'))
    if not license_text or not tpl_text:
        return None
    tpl_display = [ln.rstrip() for ln in tpl_text.splitlines()]   # 展示用原文
    file_display = [ln.rstrip() for ln in license_text.splitlines()]
    tpl_lines = [_diff_norm(s) for s in tpl_display]              # 比对用归一化
    file_lines = [_diff_norm(s) for s in file_display]
    sm = difflib.SequenceMatcher(a=tpl_lines, b=file_lines, autojunk=False)
    rows = []
    truncated = False

    def add(status, file_ln, tpl, file):
        if len(rows) >= DIFF_ROW_LIMIT:
            nonlocal truncated
            truncated = True
            return
        rows.append({'status': status,
                     'line': str(file_ln) if file_ln else '—',
                     'tpl': _diff_clip(tpl), 'file': _diff_clip(file)})

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if len(rows) >= DIFF_ROW_LIMIT:
            truncated = True
            break
        if tag == 'equal':
            gap = i2 - i1
            head = min(DIFF_CONTEXT_LINES, gap)
            tail = min(gap - head, DIFF_CONTEXT_LINES)
            for k in range(head):
                add('same', j1 + k + 1, tpl_display[i1 + k], file_display[j1 + k])
            mid = gap - head - tail
            if mid > 0 and len(rows) < DIFF_ROW_LIMIT:
                rows.append({'status': 'omit', 'line': '—',
                             'tpl': f'……（与文件一致，省略 {mid} 行）', 'file': ''})
            for k in range(gap - tail, gap):
                add('same', j1 + k + 1, tpl_display[i1 + k], file_display[j1 + k])
        elif tag == 'delete':          # 模板有、文件缺
            run = i2 - i1
            for k in range(min(run, DIFF_RUN_LIMIT)):
                add('del', None, tpl_display[i1 + k], '（无）')
            if run > DIFF_RUN_LIMIT and len(rows) < DIFF_ROW_LIMIT:
                rows.append({'status': 'omit', 'line': '—',
                             'tpl': f'……（模板还有 {run - DIFF_RUN_LIMIT} 行未出现在你的 LICENSE 中）',
                             'file': ''})
        elif tag == 'insert':          # 文件多出
            run = j2 - j1
            for k in range(min(run, DIFF_RUN_LIMIT)):
                add('add', j1 + k + 1, '（无）', file_display[j1 + k])
            if run > DIFF_RUN_LIMIT and len(rows) < DIFF_ROW_LIMIT:
                rows.append({'status': 'omit', 'line': '—', 'tpl': '',
                             'file': f'……（还有 {run - DIFF_RUN_LIMIT} 行多出，已省略）'})
        else:                          # replace：两边不一致，逐行配对
            for k in range(max(i2 - i1, j2 - j1)):
                if len(rows) >= DIFF_ROW_LIMIT:
                    truncated = True
                    break
                has_tpl = k < i2 - i1
                has_file = k < j2 - j1
                tpl_txt = tpl_display[i1 + k] if has_tpl else '（无）'
                file_txt = file_display[j1 + k] if has_file else '（无）'
                if (has_tpl and has_file
                        and tpl_lines[i1 + k] == file_lines[j1 + k]):
                    # 归一化后相同（opcodes 边缘情形）：降级为 same，避免空白噪音
                    add('same', j1 + k + 1, tpl_txt, file_txt)
                    continue
                add('mod',
                    j1 + k + 1 if has_file else None,
                    tpl_txt, file_txt)

    if not rows:
        return None
    if truncated:
        # 2026-10-24 复核补充：撞 DIFF_ROW_LIMIT 截断时补占位行，避免用户误以为对照表完整
        rows.append({'status': 'omit', 'line': '—',
                     'tpl': f'……（差异较多，仅展示前 {DIFF_ROW_LIMIT} 行，完整文本请对照上方官方模板链接）',
                     'file': ''})
    return {
        'tpl_id': best_match.get('license_expression'),
        'coverage': best_match.get('match_coverage'),
        'match_lines': f"{best_match.get('start_line')}-{best_match.get('end_line')}",
        'rule_identifier': best_match.get('rule_identifier'),
        'rule_url': best_match.get('rule_url'),
        'truncated': truncated,
        'rows': rows,
    }


def _scan_license_file(repo_path, license_rel, work_dir, spdx_map, out_name):
    """单文件 LICENSE 扫描（scancode 引擎，原 scan_license 主体），返回 (score, row_fields)。
    row_fields: spdx/has_license/template_match/copyright_ok/osi_fsf_ok/
                osi_approved_ok/fsf_libre_ok/detail/raw_json。"""
    no_license_row = _no_license_row()
    license_abs = os.path.join(repo_path, license_rel)

    out_json = os.path.join(work_dir, out_name)
    scan = run_scancode(license_abs, out_json)
    try:
        os.remove(out_json)
    except OSError:
        pass
    if scan is None:
        # 文件存在但 scancode 执行失败：按未检出处理（0 分），明细记录原因
        return 0.0, {**no_license_row, 'detail': {'reason': 'scancode_failed',
                                                  'license_path': license_rel}}

    files = scan.get('files') or []
    file_info = files[0] if files else {}
    copyrights = file_info.get('copyrights') or []

    # scancode 输出格式兼容（2026-09-21 实测 32.5.0 / output format 4.1.0）：
    #   32.x：files[].license_detections[]（license_expression + matches[].score），无 files[].licenses
    #   3.x 旧版：files[].licenses[]（spdx_license_key + score），保留兼容
    # 统一归一化为 [{spdx, spdx_id, score, is_unknown}]
    norm = []
    for det in (file_info.get('license_detections') or []):
        matches = det.get('matches') or []
        best_score = max((m.get('score') or 0) for m in matches) if matches else 0
        expr = str(det.get('license_expression') or '')
        # license_expression_spdx 是 SPDX 官方 ID（如 BSD-3-Clause）；scancode 私有 key
        # 映射不到官方 ID 时为 LicenseRef-scancode-<key>（如 unknown-license-reference）
        norm.append({'spdx': expr or None, 'spdx_id': det.get('license_expression_spdx'),
                     'score': best_score, 'is_unknown': 'unknown' in expr})
    for lic in (file_info.get('licenses') or []):
        norm.append({'spdx': lic.get('spdx_license_key') or lic.get('key'), 'spdx_id': None,
                     'score': lic.get('score') or 0, 'is_unknown': False})

    # 同义 key 归一化 + 去重（2026-10-13 拍板：mulanpsl-2.0-en 与 mulanpsl-2.0 为
    # 同一木兰协议的中英双路，归并为 mulanpsl-2.0；明细展示去重 + OSI 档恢复可达）
    norm = dedupe_detections(norm)

    if not norm:
        # 文件存在但未识别出任何许可证：按无许可证=0 分（design.md 阶梯"无许可证 0 分"）
        return 0.0, {**no_license_row,
                     'detail': {'reason': 'no_license_detected', 'license_path': license_rel}}

    # 主许可证：score 最高的检出项；落库标识优先 SPDX 官方 ID
    # （scancode key 体系与 SPDX ID 不一致，如 bsd-new -> BSD-3-Clause）
    best = max(norm, key=lambda x: x['score'])
    spdx_id = best.get('spdx_id')
    spdx_key = spdx_id if (spdx_id and not str(spdx_id).startswith('LicenseRef')) else best['spdx']

    # 模板一致：任一已知模板命中 score==100（design.md §5.1"与模板一致性"）。
    # 排除 unknown-license-reference 兜底规则——它命中 100 恰恰说明未匹配到任何已知模板
    template_match = 1 if any(x['score'] == 100 and not x['is_unknown'] for x in norm) else 0

    # 模板不一致时提取 scancode 诊断（issue #126：score!=100 时取 matched_text_diagnostics
    # 看不一致内容）。取全检出中 score 最高的 match，携带其诊断字段
    # （matched_text / matched_text_diagnostics 由 --license-text-diagnostics 产生；
    #   2026-10-19 修正 key 名：scancode 32.5.0 实际输出字段为 matched_text_diagnostics
    #   （32.x format 4.1.0 实测），此前误写 license_text_diagnostics 被静默过滤未落库）
    # 2026-10-23 新增：官方模板逐行并排对照（template_diff，页面"模板差异对照"表格数据源）
    matched_text_diagnostics = None
    template_diff = None
    if template_match != 1:
        best_match = None
        for det in (file_info.get('license_detections') or []):
            for m in (det.get('matches') or []):
                if best_match is None or (m.get('score') or 0) > (best_match.get('score') or 0):
                    best_match = m
        if best_match is not None:
            matched_text_diagnostics = {k: best_match[k] for k in (
                'score', 'match_coverage', 'matched_length', 'matcher',
                'license_expression', 'rule_identifier', 'rule_relevance',
                'matched_text', 'matched_text_diagnostics')
                if best_match.get(k) is not None}
            # diff 文件侧用 LICENSE 全文（读取失败/超限时跳过 diff，不阻断主流程）
            try:
                with open(license_abs, encoding='utf-8', errors='replace') as fh:
                    license_text = fh.read(LICENSE_READ_LIMIT)
            except OSError:
                license_text = None
            template_diff = _build_template_diff(best_match, license_text)

    # copyright 年份/责任人正确（宽松正则，匹配任一 copyright 值）
    copyright_ok = 0
    copyright_matched = None
    for c in copyrights:
        # scancode 32.x（format 4.1.0）copyrights[] 元素键名为 copyright，
        # 旧版 3.x 为 value —— 双键兼容（2026-10-07 实测 32.5.0 raw_json 修正，
        # 2026-10-10 合入生产副本；此前生产副本仅取 value，32.5.0 下恒不命中）
        value = c.get('copyright') or c.get('value') or ''
        if HUAWEI_COPYRIGHT_RE.search(value):
            copyright_ok = 1
            copyright_matched = value
            break

    # OSI/FSF：SPDX 清单 isOsiApproved/isFsfLibre 标志位判定（issue #126：满足任一即
    # 10 分，分开记录 osi_approved_ok / fsf_libre_ok，明确"具体是哪个不满足"）。
    # 清单不可用时三者置 NULL（无法判定）。双路比对：license_expression_spdx（官方 ID，
    # 如 BSD-3-Clause）与 license_expression（scancode key，常见许可证与 SPDX ID 相同）
    osi_fsf_ok = None
    osi_approved_ok = None
    fsf_libre_ok = None
    if spdx_map is not None:
        osi_approved_ok, fsf_libre_ok = 0, 0
        for cand in (str(best.get('spdx_id') or '').strip().lower(),
                     str(best.get('spdx') or '').strip().lower()):
            info = spdx_map.get(cand)
            if info:
                osi_approved_ok = 1 if info['osi'] else 0
                fsf_libre_ok = 1 if info['fsf'] else 0
                break
        osi_fsf_ok = 1 if (osi_approved_ok or fsf_libre_ok) else 0

    # 阶梯计分（递进式累加，2026-10-10 口径仲裁：由"只取满足的最高档"改为递进累加）：
    #   检出许可证（基础分）                 -> 5
    #   + 模板一致（scancode score==100）     -> +3 = 8
    #   + copyright 年份/责任人替换正确       -> +1 = 9
    #   + OSI/FSF 认证（SPDX 标志位）         -> +1 = 10
    # 高档位预设低档位条件：OSI/FSF 认证仅在模板一致且版权正确时才累加，
    # 修复原并联取最高档时"OSI 认证许可证（如 Apache-2.0）绕过 copyright 检查直接 10 分"的口径漏洞
    score = 5.0
    if template_match == 1:
        score += 3.0
        if copyright_ok == 1:
            score += 1.0
            if osi_fsf_ok == 1:
                score += 1.0

    # 明细：检出清单 / copyright 匹配原文 / 模板差异对照（排查用；scancode 原始全文已落 raw_json）
    detail = {
        'license_path': license_rel,
        'detected_licenses': [{'spdx': x['spdx'], 'score': x['score']} for x in norm[:10]],
        'template_id': spdx_key,
        'matched_text_diagnostics': matched_text_diagnostics,
        'template_diff': template_diff,
        'copyright_matched': copyright_matched,
        'osi_approved_ok': osi_approved_ok,
        'fsf_libre_ok': fsf_libre_ok,
    }

    # raw_json：scancode 原始输出全文（超限截断）
    raw_text = json.dumps(scan, ensure_ascii=False)
    if len(raw_text) > RAW_JSON_LIMIT:
        raw_text = raw_text[:RAW_JSON_LIMIT]

    row = {
        'spdx': spdx_key, 'has_license': 1, 'template_match': template_match,
        'copyright_ok': copyright_ok, 'osi_fsf_ok': osi_fsf_ok,
        'osi_approved_ok': osi_approved_ok, 'fsf_libre_ok': fsf_libre_ok,
        'detail': detail, 'raw_json': raw_text,
    }
    return score, row


def _and_flag(values):
    """多文件标志位 AND 合并：任一 None（无法判定）→ None；否则全 1 才 1。"""
    if any(v is None for v in values):
        return None
    return 1 if all(v == 1 for v in values) else 0


def scan_license(repo_path, work_dir, spdx_map, repo_seq):
    """单仓 LICENSE 扫描，返回 (score, row_fields)。
    2026-10-10 改版：定位对齐 scorecard v5.5.0（find_license_target）；
    2026-10-19 口径升级（用户拍板）：多许可证文件夹仓（如 cann/driver 的
    LICENSES/ 双协议）改为"全部达标才算达标"——
      得分 = 各候选文件得分最低值（min）；
      标志位（模板/版权/OSI-FSF）= 各文件 AND；
      主行 spdx = 各文件 SPDX 用「、」拼接（如 cann-v2.0、GPL-2.0-only）；
      detail.folder_files_scanned 逐文件留痕（含模板/版权/OSI 各台阶结果），
      detected_licenses 汇总各文件主检出，供前端 summary 展示全部许可证。
    单文件命中行为不变。"""
    no_license_row = _no_license_row()
    target = find_license_target(repo_path)
    if target is None:
        return 0.0, no_license_row
    if target[0] == 'file':
        _, rel = target
        return _scan_license_file(repo_path, rel, work_dir, spdx_map,
                                  f'scancode_{repo_seq}.json')

    # 文件夹命中：候选逐个单文件扫描，全达标口径聚合（2026-10-19 拍板）
    _, folder_rel, cand_rels = target
    if len(cand_rels) > MAX_FOLDER_FILES:
        print(f"  WARN: {folder_rel}/ has {len(cand_rels)} candidates, "
              f"scanning first {MAX_FOLDER_FILES} (sorted)", flush=True)
        cand_rels = cand_rels[:MAX_FOLDER_FILES]
    scored = []                                    # (score, rel, row) 插入序 = 排序序
    for k, rel in enumerate(cand_rels):
        s, row = _scan_license_file(repo_path, rel, work_dir, spdx_map,
                                    f'scancode_{repo_seq}_{k}.json')
        scored.append((s, rel, row))

    scores = [s for s, _, _ in scored]
    min_score = min(scores)
    # 瓶颈文件 = 得分最低者（平分取排序首个，确定性）；诊断字段以其为准
    min_idx = scores.index(min_score)
    base_row = scored[min_idx][2]

    per_file = []
    for s, rel, row in scored:
        det = row.get('detail') if isinstance(row.get('detail'), dict) else {}
        per_file.append({
            'path': rel, 'score': s, 'spdx': row.get('spdx'),
            'template_match': row.get('template_match'),
            'copyright_ok': row.get('copyright_ok'),
            'osi_fsf_ok': row.get('osi_fsf_ok'),
            'reason': det.get('reason'),
        })

    # 聚合主检出（每文件主 spdx 一条），供前端 summary「SPDX 标识」全量展示
    detected = []
    for _, rel, row in scored:
        spdx_val = row.get('spdx')
        if spdx_val:
            detected.append({'spdx': spdx_val, 'score': 100})

    detail = dict(base_row.get('detail') or {}) if isinstance(base_row.get('detail'), dict) else {}
    detail['license_folder'] = folder_rel
    detail['folder_files_scanned'] = per_file
    if detected:
        detail['detected_licenses'] = detected
    # 多文件时 template_id 一并拼接，避免阶梯文案只报瓶颈文件一个标识
    spdx_all = '、'.join(str(p['spdx']) for p in per_file if p['spdx'])
    if spdx_all:
        detail['template_id'] = spdx_all

    row = dict(base_row)
    row.pop('score', None)                         # score 由主流程落库，不进 row_fields
    row['spdx'] = spdx_all or None
    row['has_license'] = 1 if min_score >= 5 else 0
    row['template_match'] = _and_flag([r.get('template_match') for _, _, r in scored])
    row['copyright_ok'] = _and_flag([r.get('copyright_ok') for _, _, r in scored])
    row['osi_fsf_ok'] = _and_flag([r.get('osi_fsf_ok') for _, _, r in scored])
    row['osi_approved_ok'] = _and_flag([r.get('osi_approved_ok') for _, _, r in scored])
    row['fsf_libre_ok'] = _and_flag([r.get('fsf_libre_ok') for _, _, r in scored])
    row['detail'] = detail
    return min_score, row


# =====================================================================
# 主流程
# =====================================================================

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

    if not check_scancode_available():
        return 1

    repo_id_filter = None
    if args.repo_ids:
        repo_id_filter = [int(x) for x in args.repo_ids.split(',') if x.strip()]

    # 复用处理脚本预 clone 的本地仓根目录（不 clone、不删除，共享资源）
    repo_base_dir = args.repo_base_dir
    if not os.path.isdir(repo_base_dir):
        print(f"WARN: repo base dir not found: {repo_base_dir} "
              f"(处理脚本预 clone 根目录；缺失时所有仓将写 NA 行 reason=repo_not_found)")
    print(f"Repo base dir: {repo_base_dir}")

    # work_dir 仅用于 scancode 输出 json 与 SPDX 缓存（不再 clone）
    work_dir = args.work_dir or os.path.join(tempfile.gettempdir(), 'security_license_scan')
    os.makedirs(work_dir, exist_ok=True)
    print(f"Work dir: {work_dir}")

    spdx_map = load_spdx_map(args.spdx_list_file, work_dir)

    unified_scan_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # etl_time 逐仓取实际入库时刻（issue #126：扫描结束时间=入库时间）；
    # scan_time 保持批次统一（幂等键 UNIQUE KEY(repo_id, scan_time)）
    print(f"Unified scan time: {unified_scan_time}")

    connection = get_db_connection(doris_url, doris_username, doris_password)
    success_count = 0
    failure_count = 0
    na_count = 0      # 三态异常仓（NA 行写库，不计失败）
    score_sum = 0.0
    score_n = 0
    try:
        repos = load_repo_list(connection, repo_id_filter)
        if not repos:
            print("ERROR: empty repo list")
            return 1
        total = len(repos)
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
                    # 三态兜底 NA 行：score NULL + is_na=1（工程兜底，汇聚剔除权重，不丢仓）
                    na_count += 1
                    print(f"  NA ({na_reason}): {na_message}", flush=True)
                    row = {
                        'repo_id': repo_id,
                        'scan_time': unified_scan_time,
                        'repo_url': repo_url,
                        'spdx': None, 'has_license': None, 'template_match': None,
                        'copyright_ok': None, 'osi_fsf_ok': None,
                        'osi_approved_ok': None, 'fsf_libre_ok': None,
                        'detail': json.dumps({'reason': na_reason, 'message': na_message},
                                             ensure_ascii=False),
                        'raw_json': None,
                        'score': None,
                        'is_na': 1,
                        'etl_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    insert_license_row(connection, row)
                    success_count += 1
                else:
                    score, fields = scan_license(repo_dir, work_dir, spdx_map, i)
                    row = {
                        'repo_id': repo_id,
                        'scan_time': unified_scan_time,
                        'repo_url': repo_url,
                        'score': score,
                        'is_na': 0,  # 本指标恒非 NA（design.md §5.1）
                        'etl_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        **fields,
                    }
                    row['detail'] = json.dumps(row['detail'], ensure_ascii=False) \
                        if isinstance(row['detail'], dict) else row['detail']
                    insert_license_row(connection, row)
                    success_count += 1
                    score_sum += score
                    score_n += 1
                    print(f"  inserted | spdx={row['spdx']} score={score} "
                          f"(has={row['has_license']} tpl={row['template_match']} "
                          f"cr={row['copyright_ok']} osi={row['osi_fsf_ok']})", flush=True)
            except Exception as e:
                failure_count += 1
                print(f"  ERROR processing repo_id={repo_id}: {e}", flush=True)
                import traceback
                traceback.print_exc()
            print(f"Progress: {i + 1}/{total} | OK: {success_count} FAIL: {failure_count} NA: {na_count}", flush=True)
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

    print("\n" + "=" * 60)
    print(f"Summary: {success_count} successful, {failure_count} failed, "
          f"{na_count} NA repos, scan_time={unified_scan_time}")
    if score_n:
        print(f"  LICENSE avg_score={round(score_sum / score_n, 2)} scored={score_n}")
    if success_count == 0 and failure_count > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
