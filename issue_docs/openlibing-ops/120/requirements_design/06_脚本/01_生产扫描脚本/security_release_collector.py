#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T3 Release 采集脚本（安全评分看板 · 指标11 发布签名 SIGNED_RELEASES）

替代 SeaTunnel get_release-已到raw表.conf：该 conf 的 PageNumber 分页模式下
数组展开与字段顺序均异常（2026-09-27 实测核验：raw 表 44 仓每仓恰好 1 行、
release_tag/owner/repo 三字段整体循环错位、只落了返回数组首元素）。
本脚本逐仓拉取 GitCode releases 并逐条落库。

功能：
  1. 从 Doris 读仓库清单（与 conf 源 SQL 同口径：is_operate=1 且 platform='gitcode'，
     实测 130 仓；不含 token 列与 acc JOIN——Python 版 token 走参数注入，
     不读 DB 加密字段，当前两口径仓数一致均为 130）
  2. 逐仓调用 GET /api/v5/repos/{owner}/{repo}/releases：
     - page 从 1 递增，per_page=100，direction=desc（接口默认升序=旧在前，
       必须显式 desc 才能"取最近"）
     - 返回空数组即该仓结束；一 release 一行（一仓多行，落库全量不止 30 条，
       "取最近 30"由 D2-11 计算层按 created_at DESC 过滤）
     - 403/404（私有/不存在仓）单仓跳过记日志，不阻断整体任务
     - 网络异常单请求重试 3 次，仍失败跳过该仓
  3. 落表 raw_repo_release_info (repo_id, release_tag, owner, repo, data_json)：
     - release_tag ← $.tag_name（不再是错位的 owner 名）
     - owner ← 仓库 owner、repo ← 仓库名（均来自遍历源 SQL 解析 repo_url）
     - data_json ← 单条 release 完整 JSON（含 assets，供 sdi 层 sha256/签名派生）
     - UNIQUE KEY (repo_id, release_tag)：同批次重跑幂等覆盖
     - 空 release 仓不落行（指标层判 NA，设计口径，不造默认行）
     - etl_time 由表 DEFAULT CURRENT_TIMESTAMP 自动填充（与 conf 行为一致）

凭证（不落脚本）：
  - Doris：DS 占位符 ${openlibing_doris_url/username/password}（DS 全局文本替换），
    本地回退 CLI 参数（同 security_license_scan.py 模式）
  - GitCode token：查表获取（同 conf 源 SQL）——源 SQL JOIN
    sdi_project_common_account_info.gitcode_token（密文），脚本内复刻
    openlibing-seatunnel-crypto CommonDecryptUtil 解密：
      DECRYPT_TOKEN 环境变量（5 段 base64，DS worker 与 SeaTunnel 同 pod 环境继承）
      → XOR(PART1,PART2,PART3) + PBKDF2WithHmacSHA256(10000, salt) 派生 rootKey
      → AES/GCM 解 WORK 得 workKey → AES/GCM 解 token 密文
    解密不可用（无 DECRYPT_TOKEN / 无 cryptography 库 / 单仓解密失败）时该仓
    匿名请求（公开仓带不带 token 结果一致，私有仓 403 跳过），记 WARN 不阻断。
    --token 参数保留作全局调试覆盖（优先级最高）。

DS（DolphinScheduler）部署：将工作流"[安全合规][job][raw]获取代码仓发布签名检查
（Signed-Releases）"中的 SEATUNNEL 任务"获取仓库release信息-发布签名检查
（Signed-Releases）"替换为 SHELL 任务贴入本脚本（同 security_license_scan.py /
代码仓commit扫描脚本 v6 模式）。

重灌前置（重要）：本表 UNIQUE KEY 为 (repo_id, release_tag)，旧错位数据
release_tag 全是 owner 名（'cann'/'Ascend'），重灌前必须 TRUNCATE
raw_repo_release_info，且 sdi 层 sdi_rd_efc_release_info 同样 UNIQUE KEY
(repo_id, release_tag) 且清洗 DML 只 INSERT 不删，需一并 TRUNCATE，
否则旧错位行残留污染 D2-11 计算。
"""

import os
import re
import sys
import json
import time
import base64
import hashlib
import argparse
import urllib.request
import urllib.error
import urllib.parse

SCRIPT_VERSION = 'v2-20260927'

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

# AES/GCM（token 解密用，复刻 CommonDecryptUtil；仅标准库无法实现 AES）
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTO_OK = True
except ImportError:
    CRYPTO_OK = False

# =====================================================================
# 常量区
# =====================================================================

GITCODE_API_BASE = 'https://api.gitcode.com/api/v5'
DEFAULT_PER_PAGE = 100      # 接口单页上限
DEFAULT_MAX_PAGES = 100     # 分页兜底（100 页 × 100 条 = 1 万 release/仓，防跑飞）
REQUEST_TIMEOUT = 60        # 单请求超时（秒），对齐 conf socket_timeout_ms=60000
RETRY_TIMES = 3             # 单请求重试次数，对齐 conf retry=3
RETRY_INTERVAL = 2          # 重试基础间隔（秒），逐次递增
REQUEST_INTERVAL = 0.2      # 相邻请求限流间隔（秒），避免压垮上游接口

# Doris 目标表（raw层6表建表DDL.sql T3 段）
TARGET_TABLE = 'raw_repo_release_info'


# =====================================================================
# 参数与环境（DS 凭证注入同 security_license_scan.py 模式）
# =====================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='T3 Release collector (SIGNED_RELEASES) -> raw_repo_release_info')
    parser.add_argument('--doris-url', default=None,
                        help='Doris JDBC URL（本地调试用；DS 运行时由占位符注入，无需传）')
    parser.add_argument('--doris-username', default=None, help='Doris 用户名（本地调试用）')
    parser.add_argument('--doris-password', default=None, help='Doris 密码（本地调试用）')
    parser.add_argument('--token', default=None,
                        help='GitCode API token 全局调试覆盖（优先级最高；'
                             '正式链路为源 SQL 查表 gitcode_token + DECRYPT_TOKEN 解密）')
    parser.add_argument('--repo-ids', default=None,
                        help='逗号分隔的 repo_id 过滤列表（调试单仓用）')
    parser.add_argument('--dry-run', action='store_true',
                        help='只拉接口打印每仓 release 数与 tag 列表，不写库')
    parser.add_argument('--per-page', type=int, default=DEFAULT_PER_PAGE,
                        help=f'分页每页条数（默认 {DEFAULT_PER_PAGE}，接口上限）')
    parser.add_argument('--max-pages', type=int, default=DEFAULT_MAX_PAGES,
                        help=f'单仓分页兜底上限（默认 {DEFAULT_MAX_PAGES}）')
    return parser.parse_args()


def get_dolphinscheduler_params():
    """Doris 凭证（照抄 security_license_scan.py get_dolphinscheduler_params）：
    占位符裸写在返回值字面量里，DS 内联任务执行前对脚本文本做全局替换。"""
    return (
        '${openlibing_doris_url}',
        '${openlibing_doris_username}',
        '${openlibing_doris_password}',
    )


# =====================================================================
# GitCode token 解密（复刻 openlibing-seatunnel-crypto CommonDecryptUtil）
# 链路：DECRYPT_TOKEN env（5 段 base64）→ rootKey(PBKDF2) → workKey → token 明文
# =====================================================================

def _aes_gcm_decrypt(cipher_bytes, key_bytes):
    """AES/GCM/NoPadding，IV=密文前 12 字节，tag 128bit 附于密文尾。
    对齐 CommonDecryptUtil.decrypt(byte[], byte[])。"""
    iv = cipher_bytes[:12]
    ct_and_tag = cipher_bytes[12:]
    return AESGCM(key_bytes).decrypt(iv, ct_and_tag, None)


def _decode_part(part):
    """双层 base64：段先 b64decode 得 base64 字符串，再 b64decode 得原始字节。
    对齐 CommonDecryptUtil 静态块 + genRootKey 的双重解码。"""
    return base64.b64decode(base64.b64decode(part).decode())


class GitTokenDecryptor:
    """从 DECRYPT_TOKEN 环境变量初始化的 token 解密器（同 SeaTunnel worker 侧）。
    初始化失败返回 None（调用方匿名降级）；单条密文解密失败抛异常由调用方决策。"""

    def __init__(self):
        env = os.environ.get('DECRYPT_TOKEN')
        if not env:
            raise RuntimeError('DECRYPT_TOKEN env not set')
        parts = env.split(';')
        if len(parts) != 5:
            raise RuntimeError(f'DECRYPT_TOKEN env must have 5 parts, got {len(parts)}')
        # rootKey = PBKDF2WithHmacSHA256(base64(XOR(PART3, XOR(PART1, PART2))), SALT, 10000, 256bit)
        data1 = _decode_part(parts[0])
        data2 = _decode_part(parts[1])
        data3 = _decode_part(parts[2])
        salt = _decode_part(parts[3])
        work_cipher_str = base64.b64decode(parts[4]).decode()

        def _xor(a, b):
            if len(a) != len(b):
                return bytes(len(a))
            return bytes(x ^ y for x, y in zip(a, b))

        root_material = base64.b64encode(_xor(data3, _xor(data1, data2)))
        # Java PBEKeySpec(char[]) 的 PBKDF2WithHmacSHA256 按 UTF-8 取密码字节
        root_key = hashlib.pbkdf2_hmac('sha256', root_material, salt, 10000, dklen=32)
        # workKey = AES/GCM 解 WORK（密文为 base64 字符串）
        work_key_str = _aes_gcm_decrypt(base64.b64decode(work_cipher_str), root_key)
        # workKey 明文本身是 base64 编码的最终 AES key
        self._work_key = base64.b64decode(work_key_str)

    def decrypt(self, ciphertext):
        """解密单条 token 密文（DB 中 gitcode_token 值），返回明文。"""
        plain = _aes_gcm_decrypt(base64.b64decode(ciphertext), self._work_key)
        return plain.decode('utf-8')


def init_token_decryptor():
    """初始化解密器：cryptography 缺失 / DECRYPT_TOKEN 未配置时返回 None（WARN）。"""
    if not CRYPTO_OK:
        print("WARN: cryptography lib not available. Install: pip install cryptography. "
              "GitCode tokens from DB cannot be decrypted; will request anonymously.")
        return None
    try:
        return GitTokenDecryptor()
    except Exception as e:
        print(f"WARN: token decryptor init failed ({e}). "
              "Will request anonymously (public repos unaffected).")
        return None


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
    """扫描范围：sdi_rd_efc_repo_operate_conf is_operate=1 且 platform='gitcode'
    （接口层采集设计 §2 统一源同口径，含 acc JOIN 取 gitcode_token 密文，
    与 conf 源 SQL 逐字一致；owner/repo 由 repo_url 解析）。
    返回行含 repo_id / owner / repo / repo_url / token_cipher，
    按 repo_id 去重防御 JOIN 重复行。"""
    sql = ("SELECT cf.repo_id, "
           "SUBSTRING_INDEX(SUBSTRING_INDEX(cf.repo_url, '/', 4), '/', -1) AS owner, "
           "SUBSTRING_INDEX(SUBSTRING_INDEX(cf.repo_url, '/', -1), '.', 1) AS repo, "
           "cf.repo_url, "
           "acc.gitcode_token AS token_cipher "
           "FROM sdi_rd_efc_repo_operate_conf cf "
           "INNER JOIN sdi_repo_info info ON info.repo_id = cf.repo_id "
           "INNER JOIN sdi_project_common_account_info acc ON acc.project_id = info.project_id "
           "WHERE cf.is_operate = 1 AND info.platform = 'gitcode'")
    params = []
    if repo_id_filter:
        sql += " AND cf.repo_id IN (%s)" % ','.join(['%s'] * len(repo_id_filter))
        params = list(repo_id_filter)
    sql += " ORDER BY cf.repo_id"
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    dedup = {}
    for r in rows:
        dedup[r['repo_id']] = r
    result = list(dedup.values())
    no_token = sum(1 for r in result if not r.get('token_cipher'))
    print(f"Loaded {len(result)} gitcode repos (is_operate=1, platform=gitcode), "
          f"{no_token} without token cipher in DB")
    return result


def resolve_repo_token(row, decryptor, cli_token):
    """单仓 token 解析：--token 全局覆盖 > 查表密文解密 > 匿名 None。
    解密失败不阻断（WARN + 匿名，公开仓不受影响，私有仓 403 跳过）。
    返回 (token, mode)：mode 用于日志统计。"""
    if cli_token:
        return cli_token, 'cli'
    cipher = row.get('token_cipher')
    if not cipher:
        return None, 'anonymous'
    if decryptor is None:
        return None, 'anonymous'
    try:
        return decryptor.decrypt(cipher), 'db-decrypt'
    except Exception as e:
        print(f"  WARN: token decrypt failed (repo_id={row['repo_id']}): {e}; "
              f"requesting anonymously", flush=True)
        return None, 'anonymous'


def insert_release_rows(connection, repo_id, owner, repo, releases):
    """单仓 release 批量落库（executemany 一仓一批）。
    失败时降级逐行 INSERT（UNIQUE KEY (repo_id, release_tag) 幂等覆盖，
    同仓 tag 重复时行数少于 API 数属预期）。返回成功行数。
    tag_name 缺失的 release 跳过并记 WARN（无法作为唯一键）。"""
    rows = []
    for rel in releases:
        tag = rel.get('tag_name')
        if not tag:
            print(f"  WARN: release without tag_name skipped "
                  f"(repo_id={repo_id}, keys={sorted(rel.keys())[:5]})", flush=True)
            continue
        rows.append((repo_id, str(tag), owner, repo,
                     json.dumps(rel, ensure_ascii=False)))
    if not rows:
        return 0
    sql = (f"INSERT INTO {TARGET_TABLE} "
           "(repo_id, release_tag, owner, repo, data_json) VALUES (%s, %s, %s, %s, %s)")
    try:
        with connection.cursor() as cursor:
            cursor.executemany(sql, rows)
        connection.commit()
        return len(rows)
    except Exception as e:
        try:
            connection.rollback()
        except Exception:
            pass
        print(f"  batch insert failed, fallback to row-by-row: {e}", flush=True)
        ok = 0
        for row in rows:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql, row)
                connection.commit()
                ok += 1
            except Exception as e2:
                try:
                    connection.rollback()
                except Exception:
                    pass
                print(f"  row insert failed (repo_id={repo_id}, "
                      f"release_tag={row[1]}): {e2}", flush=True)
        return ok


# =====================================================================
# GitCode API
# =====================================================================

def gitcode_get_json(url, token, timeout=REQUEST_TIMEOUT):
    """GET GitCode API，返回 (status, parsed_json, raw_text)。
    HTTP 4xx/5xx 不抛异常（调用方按状态码决策）；网络异常向上抛由调用方重试。"""
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'security-release-collector/1.0',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode('utf-8', errors='replace')
            try:
                return resp.status, json.loads(text), text
            except ValueError:
                return resp.status, None, text
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode('utf-8', errors='replace')
        except Exception:
            text = ''
        return e.code, None, text


def fetch_repo_releases(owner, repo, token, per_page, max_pages):
    """拉取单仓全部 release（direction=desc，page 递增直到空页/尾页）。
    返回 (releases_list, error_message)。
    - 403/404：私有/不存在仓，返回错误由调用方跳过该仓
    - 网络异常：重试 RETRY_TIMES 次，仍失败返回错误
    - 尾页优化：返回数 < per_page 必然是最后一页，无需再请求一次空页"""
    releases = []
    page = 1
    while page <= max_pages:
        url = (f"{GITCODE_API_BASE}/repos/"
               f"{urllib.parse.quote(str(owner))}/{urllib.parse.quote(str(repo))}"
               f"/releases?page={page}&per_page={per_page}&direction=desc")
        status = None
        data = None
        last_exc = None
        for attempt in range(1, RETRY_TIMES + 1):
            try:
                status, data, _ = gitcode_get_json(url, token)
                break
            except Exception as e:
                last_exc = e
                if attempt < RETRY_TIMES:
                    time.sleep(RETRY_INTERVAL * attempt)
        if status is None:
            return None, f"network error after {RETRY_TIMES} retries: {last_exc}"
        if status in (403, 404):
            return None, f"HTTP {status} (private or missing repo)"
        if status != 200:
            return None, f"HTTP {status}"
        if not isinstance(data, list):
            return None, f"unexpected response type: {type(data).__name__}"
        if not data:
            break                    # 空页：该仓结束
        releases.extend(data)
        if len(data) < per_page:
            break                    # 尾页（不足满页即最后一页）
        page += 1
        time.sleep(REQUEST_INTERVAL)
    return releases, None


# =====================================================================
# 主流程
# =====================================================================

def main():
    args = parse_arguments()
    print("=== Debug Information ===")
    print(f"Command line arguments: {sys.argv}")
    print(f"Script version: {SCRIPT_VERSION}")

    doris_url = args.doris_url
    doris_username = args.doris_username
    doris_password = args.doris_password

    if not all([doris_url, doris_username, doris_password]):
        print("No params from command line, trying DS environment variables...")
        (doris_url, doris_username, doris_password) = get_dolphinscheduler_params()

    # token 解密器：源 SQL 查表 gitcode_token 密文 + DECRYPT_TOKEN 环境变量解密
    # （--token 传入时跳过初始化，全局覆盖）
    if args.token:
        decryptor = None
        masked = args.token[:6] + '***' if len(args.token) > 6 else '***'
        print(f"GitCode token: {masked} (CLI override, DB decrypt skipped)")
    else:
        decryptor = init_token_decryptor()
        if decryptor is not None:
            print("GitCode token decryptor initialized (from DECRYPT_TOKEN env)")

    repo_id_filter = None
    if args.repo_ids:
        repo_id_filter = [int(x) for x in args.repo_ids.split(',') if x.strip()]

    connection = None
    ok_repos = 0          # 成功采集仓数（含 0 release 仓）
    empty_repos = 0       # 空 release 仓（不落行，指标层判 NA）
    error_repos = 0       # 跳过仓数（403/404/网络失败）
    total_rows = 0        # 落库总行数
    token_mode_count = {} # token 来源统计（db-decrypt / cli / anonymous）
    try:
        connection = get_db_connection(doris_url, doris_username, doris_password)
        repos = load_repo_list(connection, repo_id_filter)
        if not repos:
            print("ERROR: empty repo list")
            return 1
        total = len(repos)
        for i, r in enumerate(repos):
            repo_id = r['repo_id']
            owner = r['owner']
            repo = r['repo']
            token, token_mode = resolve_repo_token(r, decryptor, args.token)
            token_mode_count[token_mode] = token_mode_count.get(token_mode, 0) + 1
            if token:
                masked = token[:4] + '***'
                print(f"\n[{i + 1}/{total}] repo_id={repo_id} {owner}/{repo} "
                      f"(token: {masked})", flush=True)
            else:
                print(f"\n[{i + 1}/{total}] repo_id={repo_id} {owner}/{repo} "
                      f"(token: none, anonymous)", flush=True)
            try:
                releases, err = fetch_repo_releases(
                    owner, repo, token, args.per_page, args.max_pages)
                if err is not None:
                    error_repos += 1
                    print(f"  SKIP ({err})", flush=True)
                elif not releases:
                    # 空 release 仓：不落行（设计口径，指标层判 NA）
                    empty_repos += 1
                    ok_repos += 1
                    print(f"  0 releases (no rows inserted, NA at metric layer)", flush=True)
                else:
                    tags = [str(x.get('tag_name')) for x in releases]
                    print(f"  {len(releases)} releases (desc): {tags}", flush=True)
                    if args.dry_run:
                        ok_repos += 1
                    else:
                        inserted = insert_release_rows(
                            connection, repo_id, owner, repo, releases)
                        total_rows += inserted
                        ok_repos += 1
                        print(f"  inserted {inserted} rows", flush=True)
            except Exception as e:
                error_repos += 1
                print(f"  ERROR processing repo_id={repo_id}: {e}", flush=True)
                import traceback
                traceback.print_exc()
            print(f"Progress: {i + 1}/{total} | OK: {ok_repos} "
                  f"(empty: {empty_repos}) SKIP/FAIL: {error_repos}", flush=True)
    except Exception as e:
        print(f"FATAL: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if connection is not None:
            try:
                connection.close()
                print("Database connection closed", flush=True)
            except Exception:
                pass

    print("\n" + "=" * 60)
    mode = " (DRY-RUN, no rows written)" if args.dry_run else ""
    print(f"Summary:{mode} {ok_repos} repos collected ({empty_repos} empty/no-release), "
          f"{error_repos} skipped/failed, {total_rows} rows inserted")
    print(f"Token modes: {token_mode_count or '{}'} "
          f"(db-decrypt=table+DECRYPT_TOKEN, cli=--token override, anonymous=no token)")
    if error_repos > 0 and error_repos >= ok_repos:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
