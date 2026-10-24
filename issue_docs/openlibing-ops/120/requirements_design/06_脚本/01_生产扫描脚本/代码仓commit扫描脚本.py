#!/usr/bin/env python3
"""
ETL脚本：扫描代码仓 commit 信息，结果写入 raw_repo_commit_log 表

功能（2026-09-26 对齐 security_file_scan.py 模式）：
1. 仓库清单与分支全部脚本自查，DS 只传 Doris 凭证与 since：
   - 仓库清单：sdi_repo_info WHERE repo_id IN (operate_conf is_operate=1)
   - 默认分支：sdi_repo_branch_info.default_branch（default_branch=true，实时维护），
     只扫默认分支——与安全扫描口径及 ops PR 看板 repo/branch/all 接口一致；
     不用 code_repo_branch_config.show_branch（PR 看板展示分支配置，非扫描口径），
     不用 dwi_code_scan_language.is_default_branch（扫描快照值，存在延迟）。
2. 复用处理脚本预 clone 的代码仓（不 fetch，信任处理脚本已拉最新），
   checkout 到默认分支（已在目标分支则跳过 checkout）
3. 用 git log 抓取 commit 基础元数据（hash/作者/邮箱/时间/标题）
4. 结果按 (repo_id, branch_name, commit_hash) 唯一键写表，重复扫描自动覆盖
5. 本地仓不存在 / 无默认分支 / checkout 失败 → 跳过该仓并计入失败

增量策略：
- 首次全量：since 传空 或 很早就过去
- 每日增量：Dolphin 每天传 since = 当天往前推4天（3天 + 1天缓冲，防止丢数据）
- commit 元数据不可变 + UNIQUE KEY 覆盖 => 同键重复写不堆积已由表保证

依赖：pymysql
"""
import os
import sys
import subprocess
import argparse
import datetime
import re
import pymysql
import pymysql.cursors

# 版本标记：每次重贴 DS 前核对日志第一行是否为本版本号
SCRIPT_VERSION = 'v6-20260927-100d'
TOTAL_LINES_EXPECTED = 494


def parse_arguments():
    parser = argparse.ArgumentParser(description='Scan repo commit info on default branch into raw_repo_commit_log')
    parser.add_argument('--repo-ids', required=False, default=None,
                        help='逗号分隔的 repo_id 过滤列表（调试单仓用），如 401431；缺省扫全部 is_operate=1')
    parser.add_argument('--since', required=False, default='',
                        help='起始时间(如 2026-01-01 00:00:00)；空则自动取当前时间往前100天'
                             '（D3 只需近90天 commit，100 天留缓冲；显式传 FULL 才全量）')
    default_target_dir = os.path.abspath('/openlibing/git')
    parser.add_argument('--target-dir', default=default_target_dir, help='Target directory to store repos')
    return parser.parse_args()


def get_dolphinscheduler_params():
    """Doris 凭证（照抄 security_file_scan.py get_dolphinscheduler_params，2026-09-26）：
    占位符裸写在返回值字面量里，DS 内联任务执行前对脚本文本做全局替换。"""
    return (
        '${openlibing_doris_url}',
        '${openlibing_doris_username}',
        '${openlibing_doris_password}',
    )


def parse_doris_url(doris_url):
    if not doris_url.startswith('jdbc:mysql://'):
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    url_part = doris_url[len('jdbc:mysql://'):]
    db_name_match = re.search(r'[^/]+/([^?]+)', url_part)
    if not db_name_match:
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    db_database = db_name_match.group(1)
    hosts_ports_part = url_part.split('/')[0]
    if not hosts_ports_part:
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    first_host_port = hosts_ports_part.split(',')[0].strip()
    host_port_match = re.match(r'([^:]+):(\d+)', first_host_port)
    if not host_port_match:
        raise ValueError(f"Invalid host:port format: {doris_url}")
    db_host = host_port_match.group(1)
    db_port = int(host_port_match.group(2))
    return db_host, db_port, db_database


def get_db_connection(doris_url, doris_username, doris_password):
    db_host, db_port, db_database = parse_doris_url(doris_url)
    connection = pymysql.connect(
        host=db_host, port=db_port, user=doris_username, password=doris_password,
        database=db_database, cursorclass=pymysql.cursors.DictCursor
    )
    print(f"Connected to database: {db_host}:{db_port}/{db_database}")
    return connection


def insert_commits_to_db(results, connection):
    """按 UNIQUE KEY (repo_id, branch_name, commit_hash) 写入，同键冲突自动覆盖（upsert）。
    Doris UNIQUE KEY 模型 + INSERT VALUES，重复键由表内 merge 逻辑替换。
    批量失败时降级逐行重试，隔离脏数据（只丢坏行，不损失整批）。"""
    sql = ("INSERT INTO raw_repo_commit_log "
           "(repo_id, repo_git_url, repo_name, branch_name, commit_hash, "
           " author_name, author_email, commit_time, commit_title, scan_time) "
           "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    BATCH_SIZE = 500
    inserted_count = 0
    failed_count = 0
    try:
        with connection.cursor() as cursor:
            batch_data = []
            batch_start_idx = 0

            def flush_batch():
                nonlocal inserted_count, failed_count, batch_data, batch_start_idx
                if not batch_data:
                    return
                try:
                    cursor.executemany(sql, batch_data)
                    inserted_count += len(batch_data)
                except Exception:
                    # 整批被拒（严格模式等）→ 逐行重试，只丢真正的坏行
                    for j, row in enumerate(batch_data):
                        try:
                            cursor.execute(sql, row)
                            inserted_count += 1
                        except Exception as row_err:
                            failed_count += 1
                            print(f"Bad record dropped (global #{batch_start_idx + j + 1}, "
                                  f"repo_id={row[0]}, hash={row[4]}): {row_err}", flush=True)
                batch_data = []
                batch_start_idx = 0

            for i, r in enumerate(results):
                batch_data.append((
                    r['repo_id'], r['repo_git_url'], r['repo_name'],
                    r['branch_name'], r['commit_hash'],
                    r['author_name'], r['author_email'],
                    r['commit_time'], r['commit_title'], r['scan_time']
                ))
                if len(batch_data) >= BATCH_SIZE:
                    flush_batch()
                    batch_start_idx = i + 1
            flush_batch()
            connection.commit()
        print(f"Successfully synced {inserted_count} commit records "
              f"({failed_count} bad records dropped)", flush=True)
        return inserted_count
    except Exception as e:
        print(f"Error inserting commit data: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 0


def load_repo_list(connection, repo_id_filter=None):
    """扫描范围与分支口径（照抄 security_file_scan.py load_repo_list，2026-09-26）：
      - 仓库清单：sdi_repo_info WHERE repo_id IN (operate_conf is_operate=1)
      - 只扫默认分支：default_branch 取 sdi_repo_branch_info.default_branch（实时维护；
        原 dwi_code_scan_language.is_default_branch 是扫描快照值，存在延迟）
      - 复用本地仓不再 clone / 不 fetch（凭证 JOIN 已删除，platform 仍需，
        用于拼本地路径 {base}/{platform}/{owner}/{repo_name}）
    返回行含 repo_id / repo_url / platform / default_branch。"""
    sql = ("SELECT sri.repo_id, sri.repo_url, sri.platform, "
           "ls.branch_name AS default_branch "
           "FROM sdi_repo_info sri "
           "LEFT JOIN (SELECT repo_id, name AS branch_name FROM sdi_repo_branch_info "
           "            WHERE default_branch = true) ls "
           "       ON CAST(sri.repo_id AS VARCHAR) = ls.repo_id "
           "WHERE sri.repo_id IN "
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
    print(f"Loaded {len(rows)} repos (is_operate=1), "
          f"{no_branch_count} without default_branch (will be skipped)", flush=True)
    return rows


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def get_repo_name(repo_url):
    try:
        if '://' in repo_url:
            repo_url = repo_url.split('://', 1)[1]
        if '@' in repo_url:
            repo_url = repo_url.split('@', 1)[1]
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
        return repo_url.replace('/', '_')
    except Exception as e:
        if repo_url.endswith('.git'):
            return repo_url.split('/')[-1].replace('.git', '')
        else:
            return repo_url.split('/')[-1]


def get_platform_from_url(repo_url):
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
    platform = get_platform_from_url(repo_url)
    owner, repo_name = parse_repo_identity(repo_url)
    return os.path.join(base_dir, platform, owner, repo_name)


def checkout_branch(repo_path, branch_name):
    git_safe_args = ['-c', 'safe.directory=*']
    try:
        # 已在目标分支则跳过 checkout（对齐 security_file_scan.py，减少大仓切换开销）
        cur = subprocess.run(
            ['git', *git_safe_args, '-C', repo_path, 'branch', '--show-current'],
            capture_output=True, text=True, timeout=10
        )
        if cur.returncode == 0 and cur.stdout.strip() == branch_name:
            print(f"  Already on branch: {branch_name} (skip checkout)")
            return True
        result = subprocess.run(
            ['git', *git_safe_args, '-C', repo_path, 'checkout', branch_name],
            capture_output=True, text=True, check=True
        )
        print(f"Checked out branch: {branch_name}")
        return True
    except subprocess.CalledProcessError as e:
        if "could be both a local file and a tracking branch" in (e.stderr or ''):
            try:
                result = subprocess.run(
                    ['git', *git_safe_args, '-C', repo_path, 'checkout', '--', branch_name],
                    capture_output=True, text=True, check=True
                )
                print(f"Checked out branch (with --): {branch_name}")
                return True
            except subprocess.CalledProcessError as e2:
                print(f"Error checking out {branch_name}: {e2.stderr}")
                return False
        else:
            print(f"Error checking out {branch_name}: {e.stderr}")
            return False
    except Exception as e:
        print(f"Unexpected error during checkout: {e}")
        return False


def truncate_utf8(s, max_bytes):
    """按 UTF-8 字节数截断（Doris VARCHAR(n) 限制的是 n 字节，非字符数；
    中文等多字节字符按字符切会超长）。不切断多字节字符中间。"""
    if not s:
        return ''
    b = s.encode('utf-8')
    if len(b) <= max_bytes:
        return s
    return b[:max_bytes].decode('utf-8', errors='ignore')


def scan_commits(repo_path, since):
    """用 git log 抓取当前 HEAD(已对齐到默认分支) 的 commit 基础元数据。

    since 为空 -> 全量；否则按 git log --since 过滤（含时间前缀边界）。
    返回 commit 字段列表的 raw list，由调用方组装完整记录。
    """
    git_safe_args = ['-c', 'safe.directory=*']
    # %H 完整hash %an 作者名 %ae 作者邮箱 %aI author ISO时间 %s 标题(首行)
    fmt = '%H%x1f%an%x1f%ae%x1f%aI%x1f%s'
    try:
        cmd = ['git', *git_safe_args, '-C', repo_path, 'log', '--no-color', '--pretty=format:' + fmt]
        # git log --since 对同一天的 commit 会包含当日起点之后，通常配合 --since + 无上界；
        # 鉴于 commit 元数据不可变 + 表唯一键覆盖，重叠区间重复写会被替换，无副作用。
        if since:
            since_arg = since if ' ' in since else since + ' 00:00:00'
            cmd += ['--since=' + since_arg]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(f"git log failed: {(result.stderr or '').strip()}", flush=True)
            return None
        commits = []
        for line in result.stdout.split('\n'):
            line = line.rstrip('\n')
            if not line:
                continue
            parts = line.split('\x1f')
            if len(parts) < 5:
                continue
            commit_hash, author_name, author_email, iso_time, title = parts[:5]
            # ISO 时间(带时区)转 Doris DATETIME(本地无时区)；
            # 校验合法性：格式错 / 年份超出 1900~9999（老仓损坏日期）→ NULL，防严格模式过滤
            commit_time = None
            if iso_time:
                try:
                    _dt = datetime.datetime.strptime(iso_time[:19], '%Y-%m-%dT%H:%M:%S')
                    if 1900 <= _dt.year <= 9999:
                        commit_time = _dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    commit_time = None
            commits.append({
                'commit_hash': commit_hash,
                # 三个 VARCHAR 字段均按字节截断（Doris VARCHAR(n) 是字节限制，中文 3 字节/字）
                'author_name': truncate_utf8(author_name, 200),
                'author_email': truncate_utf8(author_email, 255),
                'commit_time': commit_time,
                'commit_title': truncate_utf8(title, 500),
            })
        print(f"  git log returned {len(commits)} commits (since={since or 'FULL'})", flush=True)
        return commits
    except subprocess.TimeoutExpired:
        print(f"git log timed out after 600s", flush=True)
        return None
    except Exception as e:
        print(f"Unexpected error in git log: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


def main():
    args = parse_arguments()
    print(f"SCRIPT_VERSION: {SCRIPT_VERSION}", flush=True)

    repo_id_filter = None
    if args.repo_ids:
        repo_id_filter = [x.strip() for x in args.repo_ids.split(',') if x.strip()]
        print(f"Repo id filter (debug): {repo_id_filter}", flush=True)

    (doris_url, doris_username, doris_password) = get_dolphinscheduler_params()
    since = args.since.strip().strip('"').strip("'") if args.since else ''

    # 默认只扫近100天（D3 只需近90天，留10天缓冲）：
    # 全量首跑曾因大仓（8.6万 commits）拖到13小时；指标计算永远用不到90天以前的数据。
    # 需要真全量时显式传 --since FULL。
    if not since:
        since = (datetime.datetime.now() - datetime.timedelta(days=100)
                 ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"No --since given, defaulting to last 100 days: {since}", flush=True)
    elif since.upper() == 'FULL':
        since = ''
        print("--since FULL: full history scan", flush=True)

    create_directory(args.target_dir)

    unified_scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Unified scan time: {unified_scan_time}")
    print(f"Since(增量起始): {since or 'FULL(全量)'}")
    print("=" * 60)
    sys.stdout.flush()

    connection = None
    success_count = 0
    failure_count = 0
    skipped_count = 0

    try:
        connection = get_db_connection(doris_url, doris_username, doris_password)
        repos = load_repo_list(connection, repo_id_filter)
        total_repos = len(repos)
        if total_repos == 0:
            print("ERROR: no repos loaded (is_operate=1).", flush=True)
            return 1

        for i, repo in enumerate(repos):
            repo_id = repo['repo_id']
            repo_url = repo['repo_url']
            default_branch = repo.get('default_branch')

            if not default_branch:
                # 无默认分支 → 跳过（口径对齐 P1 三态，commit 链路无 NA 概念）
                print(f"\n[{i+1}/{total_repos}] Skipping repo_id={repo_id}: "
                      f"no default_branch in sdi_repo_branch_info", flush=True)
                skipped_count += 1
                continue

            print(f"\n[{i+1}/{total_repos}] Processing repo_id={repo_id} "
                  f"{repo_url} [branch={default_branch}]", flush=True)

            try:
                repo_name = get_repo_name(repo_url)
                repo_dir = build_repo_path(args.target_dir, repo_url)

                if not os.path.isdir(repo_dir):
                    # 处理脚本未预 clone 该仓 → 跳过
                    print(f"  Repo not found (pre-clone failed): {repo_dir}", flush=True)
                    failure_count += 1
                    continue

                if not checkout_branch(repo_dir, default_branch):
                    # checkout 默认分支失败（不 fetch，信任处理脚本已拉最新）
                    print(f"  git checkout {default_branch} failed in {repo_dir}", flush=True)
                    failure_count += 1
                    continue

                print(f"  Scanning commits on {repo_name}:{default_branch}...", flush=True)
                raw_commits = scan_commits(repo_dir, since)
                if raw_commits is None:
                    print(f"  git log failed, skipping {repo_name}:{default_branch}", flush=True)
                    failure_count += 1
                    continue

                records = []
                for c in raw_commits:
                    records.append({
                        'repo_id': repo_id, 'repo_git_url': repo_url, 'repo_name': repo_name,
                        'branch_name': default_branch,
                        'commit_hash': c['commit_hash'],
                        'author_name': c['author_name'],
                        'author_email': c['author_email'],
                        'commit_time': c['commit_time'],
                        'commit_title': c['commit_title'],
                        'scan_time': unified_scan_time,
                    })

                insert_commits_to_db(records, connection)
                success_count += 1

            except Exception as e:
                failure_count += 1
                print(f"  ERROR processing repo_id={repo_id}: {e}", flush=True)
                import traceback
                traceback.print_exc()

            print(f"Progress: {i+1}/{total_repos} | OK: {success_count} "
                  f"FAIL: {failure_count} SKIP(no-branch): {skipped_count}", flush=True)
            print("-" * 60, flush=True)

    except Exception as e:
        print(f"FATAL: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if connection:
            try:
                connection.close()
                print("Database connection closed", flush=True)
            except Exception:
                pass

    print(f"\nSummary: {success_count} successful, {failure_count} failed, "
          f"{skipped_count} skipped(no default_branch)", flush=True)

    if success_count == 0 and (failure_count > 0 or skipped_count > 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
