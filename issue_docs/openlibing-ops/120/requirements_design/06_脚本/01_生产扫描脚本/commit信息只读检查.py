#!/usr/bin/env python3
"""
只读检查脚本：仿照 代码仓commit扫描脚本.py（v6-20260927-100d）的取数/路径/git log 逻辑，
对前 N 个（默认 20）commit 最活跃的仓做诊断。【不写任何表，只打印】

每仓打印四段对照：
  DB    ：raw_repo_commit_log 里该仓的 commit 总数 / max(commit_time)
  SCAN  ：复刻生产脚本的 git log --since=<近100天> 调用 → 条数 / max commit_time
  LOCAL ：本地分支 HEAD 最新 commit + 实际检查的磁盘路径
  REMOTE：git fetch origin 后 origin/<默认分支> tip + 本地 HEAD 落后数

判定：
  OK            本地=远端最新，且 DB 已含本地最新 commit
  SCAN_BUG      本地扫得到新 commit 但 DB 里没有 → 扫描/入库环节丢数据（脚本问题）
  BRANCH_LAG    远端引用已新，本地分支 HEAD 还是旧的 → pull 只 fetch 没推进本地分支，
                而生产扫描扫的正是本地 HEAD → 这就是数据停在旧日期的根因
  STALE_LOCAL   连 origin 引用都是旧的 → fetch 链路断了（token/调度/权限）
  FETCH_FAILED  fetch 报错（stderr 原样打出，多为 token 失效）
  PRECLONE_MISS 本地目录不存在
  NO_BRANCH     sdi_repo_branch_info 无默认分支

用法（生产服务器上）：
  # DS 内贴进 PYTHON 任务跑（占位符自动替换），或手动跑时显式传 Doris 凭证：
  python3 commit信息只读检查.py \
      --doris-url jdbc:mysql://<host>:<port>/<db> --doris-user <u> --doris-pass <p>
  # 指定仓（如已知活跃仓）：--repo-ids 401469,402155
  # 跳过 fetch（不碰远端，只看本地+DB）：--no-fetch

说明：git fetch 只更新 .git 远端引用，不 checkout、不动工作区文件，安全。
"""

import os
import sys
import subprocess
import argparse
import datetime
import re
import pymysql
import pymysql.cursors

SCRIPT_VERSION = 'check-v1-20260927'

GIT_SAFE = ['-c', 'safe.directory=*']


def parse_arguments():
    parser = argparse.ArgumentParser(description='Read-only commit pipeline check (no writes)')
    parser.add_argument('--repo-ids', required=False, default=None,
                        help='逗号分隔 repo_id（缺省取 commit 数最多的前 N 仓）')
    parser.add_argument('--limit', type=int, default=20,
                        help='检查仓数上限（默认 20）')
    parser.add_argument('--since-days', type=int, default=100,
                        help='复刻生产 --since 窗口天数（默认 100，与 v6 一致）')
    parser.add_argument('--no-fetch', action='store_true',
                        help='不执行 git fetch（只看本地 + DB 对照）')
    default_target_dir = os.path.abspath('/openlibing/git')
    parser.add_argument('--target-dir', default=default_target_dir,
                        help='与生产扫描脚本相同的本地仓根目录')
    # 手动跑时的凭证覆盖（DS 内跑则用占位符自动替换，无需传）
    parser.add_argument('--doris-url', default='${openlibing_doris_url}')
    parser.add_argument('--doris-user', default='${openlibing_doris_username}')
    parser.add_argument('--doris-pass', default='${openlibing_doris_password}')
    return parser.parse_args()


def mask_url(url):
    """打印 URL 时隐藏内嵌凭证。"""
    return re.sub(r'://[^@/]+@', '://***@', url or '')


def parse_doris_url(doris_url):
    if not doris_url.startswith('jdbc:mysql://'):
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    url_part = doris_url[len('jdbc:mysql://'):]
    db_name_match = re.search(r'[^/]+/([^?]+)', url_part)
    if not db_name_match:
        raise ValueError(f"Invalid Doris URL format: {doris_url}")
    db_database = db_name_match.group(1)
    hosts_ports_part = url_part.split('/')[0]
    first_host_port = hosts_ports_part.split(',')[0].strip()
    host_port_match = re.match(r'([^:]+):(\d+)', first_host_port)
    if not host_port_match:
        raise ValueError(f"Invalid host:port format: {doris_url}")
    return host_port_match.group(1), int(host_port_match.group(2)), db_database


def get_db_connection(doris_url, doris_username, doris_password):
    db_host, db_port, db_database = parse_doris_url(doris_url)
    connection = pymysql.connect(
        host=db_host, port=db_port, user=doris_username, password=doris_password,
        database=db_database, cursorclass=pymysql.cursors.DictCursor
    )
    print(f"Connected to database: {db_host}:{db_port}/{db_database}", flush=True)
    return connection


def load_repo_list(connection, repo_id_filter, limit):
    """与生产脚本同口径（is_operate=1 + platform='gitcode' + 默认分支），并带上
    raw 表当前状态，默认按 DB 内 commit 数倒序取前 N（挑活跃仓，新鲜度问题最容易被看出）。"""
    sql = ("SELECT sri.repo_id, sri.repo_url, sri.platform, "
           "ls.branch_name AS default_branch, "
           "COALESCE(rc.cnt, 0) AS db_commit_cnt, rc.db_max_commit, rc.db_last_scan "
           "FROM sdi_repo_info sri "
           "LEFT JOIN (SELECT repo_id, name AS branch_name FROM sdi_repo_branch_info "
           "            WHERE default_branch = true) ls "
           "       ON CAST(sri.repo_id AS VARCHAR) = ls.repo_id "
           "LEFT JOIN (SELECT repo_id, COUNT(*) AS cnt, "
           "                  MAX(CAST(commit_time AS DATETIME)) AS db_max_commit, "
           "                  MAX(scan_time) AS db_last_scan "
           "           FROM raw_repo_commit_log GROUP BY repo_id) rc "
           "       ON CAST(sri.repo_id AS VARCHAR) = rc.repo_id "
           "WHERE sri.platform = 'gitcode' "
           "  AND sri.repo_id IN "
           "      (SELECT repo_id FROM sdi_rd_efc_repo_operate_conf WHERE is_operate = 1)")
    params = []
    if repo_id_filter:
        sql += " AND sri.repo_id IN (%s)" % ','.join(['%s'] * len(repo_id_filter))
        params = list(repo_id_filter)
        sql += " ORDER BY sri.repo_id"
    else:
        sql += " ORDER BY rc.cnt DESC"
    sql += " LIMIT %d" % limit
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    print(f"Loaded {len(rows)} repos for check "
          f"(filter={'specified' if repo_id_filter else 'top-by-db-commits'}, limit={limit})", flush=True)
    return rows


# ---- 以下路径构造/分支函数照抄生产脚本，保证检查的就是生产扫的那份目录 ----

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
    except Exception:
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
    except Exception:
        return 'unknown', 'unknown'


def build_repo_path(base_dir, repo_url):
    platform = get_platform_from_url(repo_url)
    owner, repo_name = parse_repo_identity(repo_url)
    return os.path.join(base_dir, platform, owner, repo_name)


# ---- git 只读检查 ----

def run_git(repo_path, args_list, timeout=600):
    try:
        r = subprocess.run(['git', *GIT_SAFE, '-C', repo_path, *args_list],
                           capture_output=True, text=True, timeout=timeout,
                           encoding='utf-8', errors='replace')
        return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()
    except subprocess.TimeoutExpired:
        return -1, '', 'TIMEOUT after %ss' % timeout
    except Exception as e:
        return -2, '', str(e)


def iso_to_dt(s):
    try:
        return datetime.datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
    except Exception:
        return None


def check_repo(repo, target_dir, since_str, do_fetch):
    """返回 (verdict, detail_dict)。verdict 取值见文件头注释。"""
    repo_id = repo['repo_id']
    repo_url = repo['repo_url']
    branch = repo.get('default_branch')
    d = {'repo_id': repo_id, 'path': build_repo_path(target_dir, repo_url)}

    print(f"\n[{repo_id}] {mask_url(repo_url)} [branch={branch}]", flush=True)
    print(f"  DB    commits={repo.get('db_commit_cnt')} "
          f"max_commit={repo.get('db_max_commit')} "
          f"last_scan={repo.get('db_last_scan')}", flush=True)

    if not branch:
        print("  VERDICT: NO_BRANCH (sdi_repo_branch_info 无默认分支，生产扫描也会跳过)", flush=True)
        return 'NO_BRANCH', d

    repo_dir = d['path']
    if not os.path.isdir(repo_dir):
        print(f"  VERDICT: PRECLONE_MISS (本地目录不存在: {repo_dir})", flush=True)
        return 'PRECLONE_MISS', d

    # LOCAL：当前分支 + HEAD
    _, cur_branch, _ = run_git(repo_dir, ['branch', '--show-current'], timeout=15)
    _, head_hash, _ = run_git(repo_dir, ['rev-parse', 'HEAD'], timeout=15)
    _, head_line, _ = run_git(repo_dir, ['log', '-1', '--pretty=format:%aI %x1f %s'], timeout=15)
    head_time = head_line.split('\x1f')[0] if head_line else ''
    head_title = head_line.split('\x1f', 1)[1].strip() if '\x1f' in head_line else head_line
    d['head_time'] = head_time
    print(f"  LOCAL  path={repo_dir}", flush=True)
    print(f"  LOCAL  branch={cur_branch or '(detached)'} HEAD={head_hash[:12] if head_hash else 'N/A'} "
          f"last_commit={head_time} «{head_title[:50]}»", flush=True)

    # SCAN：复刻生产 scan_commits 的 git log --since 调用（同 fmt 同过滤）
    fmt = '%H%x1f%aI'
    rc, out, err = run_git(repo_dir, ['log', '--no-color', '--pretty=format:' + fmt,
                                      '--since=' + since_str], timeout=600)
    scan_cnt, scan_max = 0, ''
    if rc == 0:
        for line in out.split('\n'):
            if not line.strip():
                continue
            parts = line.split('\x1f')
            if len(parts) >= 2:
                scan_cnt += 1
                if parts[1] > scan_max:
                    scan_max = parts[1]
    d['scan_cnt'], d['scan_max'] = scan_cnt, scan_max
    print(f"  SCAN   git log --since='{since_str}' → {scan_cnt} commits, "
          f"max_commit={scan_max or 'N/A'} (rc={rc}{'; ' + err[:100] if rc != 0 else ''})", flush=True)

    # REMOTE：fetch 后对比（fetch 只更新 .git 远端引用，不动工作区）
    if not do_fetch:
        print("  REMOTE skipped (--no-fetch)", flush=True)
        verdict = 'OK' if (scan_max and repo.get('db_max_commit')
                           and str(repo['db_max_commit']) >= scan_max[:19]) else 'SCAN_BUG?'
        print(f"  VERDICT: {verdict} (仅本地+DB对照，建议去掉 --no-fetch 看远端)", flush=True)
        return verdict, d

    rc_f, _, err_f = run_git(repo_dir, ['fetch', 'origin'], timeout=600)
    if rc_f != 0:
        print(f"  REMOTE fetch FAILED rc={rc_f}: {err_f[:300]}", flush=True)
        print("  VERDICT: FETCH_FAILED ← 生产拉取脚本 fetch 失败会静默降级用本地副本，"
              "任务仍显示 SUCCESS", flush=True)
        return 'FETCH_FAILED', d

    remote_ref = f'origin/{branch}'
    _, remote_hash, _ = run_git(repo_dir, ['rev-parse', remote_ref], timeout=15)
    _, remote_line, _ = run_git(repo_dir, ['log', '-1', remote_ref, '--pretty=format:%aI %x1f %s'],
                                timeout=15)
    remote_time = remote_line.split('\x1f')[0] if remote_line else ''
    remote_title = remote_line.split('\x1f', 1)[1].strip() if '\x1f' in remote_line else remote_line
    _, behind_out, _ = run_git(repo_dir, ['rev-list', '--count', f'HEAD..{remote_ref}'], timeout=120)
    behind = int(behind_out) if behind_out.isdigit() else -1
    d['remote_time'], d['behind'] = remote_time, behind
    print(f"  REMOTE {remote_ref}={remote_hash[:12] if remote_hash else 'N/A'} "
          f"last_commit={remote_time} «{remote_title[:50]}»", flush=True)
    print(f"  REMOTE 本地 HEAD 落后远端 {behind} commits", flush=True)

    # 判定链
    now = datetime.datetime.now()
    remote_dt = iso_to_dt(remote_time)
    head_up_to_date = (head_hash and remote_hash and head_hash == remote_hash)

    if head_up_to_date:
        # 本地即远端最新 → 剩下只看 DB 是否跟上（SCAN_BUG = 脚本/入库丢数据）
        db_max = str(repo.get('db_max_commit') or '')
        if scan_max and db_max and db_max >= scan_max[:19]:
            print("  VERDICT: OK (本地=远端最新，DB 已含本地最新 commit)", flush=True)
            return 'OK', d
        else:
            print(f"  VERDICT: SCAN_BUG ← 本地扫到 max={scan_max}，但 DB max={db_max or '无'}；"
                  f"git log 拿得到、库里没有 → 扫描/入库环节丢数据", flush=True)
            return 'SCAN_BUG', d
    else:
        lag_days = (now - remote_dt).days if remote_dt else -1
        print(f"  VERDICT: BRANCH_LAG ← 远端引用已是最新(tip={remote_time})，"
              f"但本地 HEAD 停在 {head_time}（落后 {behind}）；"
              f"生产扫描 checkout 后 git log 扫的正是这个旧 HEAD，"
              f"这就是 raw 停在旧日期的根因。远端 tip 距今 {lag_days} 天", flush=True)
        return 'BRANCH_LAG', d


def main():
    args = parse_arguments()
    print(f"SCRIPT_VERSION: {SCRIPT_VERSION}", flush=True)

    # 凭证：DS 内跑占位符已替换；手动跑需显式传参（占位符未替换时报错退出）
    unresolved = [v for v in (args.doris_url, args.doris_user, args.doris_pass)
                  if v.startswith('${')]
    if unresolved:
        print("ERROR: Doris 凭证未提供（占位符未被 DS 替换）。"
              "手动运行请传 --doris-url/--doris-user/--doris-pass", flush=True)
        return 1

    since_str = (datetime.datetime.now() - datetime.timedelta(days=args.since_days)
                 ).strftime('%Y-%m-%d %H:%M:%S')

    repo_id_filter = None
    if args.repo_ids:
        repo_id_filter = [x.strip() for x in args.repo_ids.split(',') if x.strip()]

    print(f"Target dir: {args.target_dir}", flush=True)
    print(f"Since(复刻生产窗口): {since_str} ({args.since_days}d)", flush=True)
    print(f"Fetch: {'OFF (--no-fetch)' if args.no_fetch else 'ON (只更新远端引用，不动工作区)'}", flush=True)
    print("=" * 70, flush=True)

    stats = {}
    order = []
    connection = None
    try:
        connection = get_db_connection(args.doris_url, args.doris_user, args.doris_pass)
        repos = load_repo_list(connection, repo_id_filter, args.limit)
        if not repos:
            print("ERROR: no repos loaded.", flush=True)
            return 1
        for repo in repos:
            v, _ = check_repo(repo, args.target_dir, since_str, not args.no_fetch)
            stats[v] = stats.get(v, 0) + 1
            if v not in order:
                order.append(v)
            print("-" * 70, flush=True)
    except Exception as e:
        print(f"FATAL: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

    print("\n" + "#" * 70, flush=True)
    print(f"Summary ({sum(stats.values())} repos checked):", flush=True)
    for v in order:
        print(f"  {v:15s} {stats[v]}", flush=True)
    print("""
判读：
  BRANCH_LAG 多  → pull 任务只 fetch 没把本地分支推进到远端 tip（或 checkout 后未 reset/pull），
                   生产扫描扫的是旧 HEAD → 修拉取脚本的 sync 逻辑后重扫即可
  STALE_LOCAL 多 → fetch 链路断了：查拉取任务的调度/token（FETCH_FAILED 的 stderr 即证据）
  SCAN_BUG 多    → 本地明明有新 commit 而库里没有 → 把本输出发我，查扫描/入库代码
  OK 多          → 链路正常，raw 数据应是新的（若 Doris 同步侧仍有旧数据，查同步链路）
""", flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
