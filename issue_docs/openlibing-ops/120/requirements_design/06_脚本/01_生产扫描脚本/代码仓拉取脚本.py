#!/usr/bin/env python3
"""
ETL脚本：复用处理脚本预 clone 的代码仓并执行质量检查，结果写入raw_repo_quality_scan表

功能：
1. 从DolphinScheduler接收代码仓列表、认证信息和目标分支(show_branch)
2. 复用处理脚本预 clone 的代码仓，checkout到show_branch
3. 对每个分支执行3项质量检查（不做增量过滤，全量扫描）
4. 检查结果写入raw_repo_quality_scan表

使用场景：首次初始化、补历史数据
"""
import os
import sys
import subprocess
import argparse
import json
import ast
import datetime
import re
import time
import glob
import pymysql
import pymysql.cursors

# 确保 pip --user 安装的工具（ruff/clang-format/clang-tidy）能在 PATH 中找到
# DS worker 上这些工具通常装在 ~/.local/bin, 但 DS 任务的默认 PATH 可能不含此目录
for _p in [os.path.expanduser('~/.local/bin'), '/root/.local/bin']:
    if os.path.isdir(_p) and _p not in os.environ.get('PATH', ''):
        os.environ['PATH'] = _p + os.pathsep + os.environ.get('PATH', '')


STYLE_CONFIG_MAP = {
    'C':        ['.clang-format'],
    'C++':      ['.clang-format'],
    'Python':   ['.pyproject.toml'],
    'Rust':     ['.rustfmt.toml'],
    'JavaScript': ['eslint.config.*', '.prettierrc', '.prettierrc.js'],
    'TypeScript': ['eslint.config.*', '.prettierrc', '.prettierrc.js'],
    'Go':       [],
    'Java':     [],
}

CHECKSTYLE_PATHS = [
    'checkstyle.xml',
    'src/checkstyle.xml',
    'config/checkstyle.xml',
    'checkstyle/checkstyle.xml',
]

# 特殊仓 top 语言例外：忽略指定语言（常因仓内单个超大工具/CI 文件主导 top 语言造成误判）
# key: repo_id(字符串), value: 需从 top 语言中剔除的语言名列表（精确匹配 language 字段）
LANG_IGNORE_OVERRIDES = {
    '405446': ['JavaScript'],
}


def parse_arguments():
    parser = argparse.ArgumentParser(description='Full scan: pull repos and run quality checks on show_branch')
    parser.add_argument('--repo_url', required=False, help='JSON list of repository URLs')
    parser.add_argument('--auth_login', required=False, help='JSON list of auth logins')
    parser.add_argument('--auth_token', required=False, help='JSON list of auth tokens')
    parser.add_argument('--repo_id', required=False, help='JSON list of repository IDs')
    parser.add_argument('--show_branch', required=False, help='JSON list of target branches')
    default_target_dir = os.path.abspath('/openlibing/git')
    parser.add_argument('--target-dir', default=default_target_dir, help='Target directory to store repos')
    return parser.parse_args()


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


def insert_scan_results_to_db(results, connection):
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO raw_repo_quality_scan (repo_id, repo_git_url, repo_name, branch_name, is_default_branch, scan_time, data_json) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            BATCH_SIZE = 500
            inserted_count = 0
            batch_data = []
            for i, result in enumerate(results):
                try:
                    batch_data.append((
                        result['repo_id'], result['repo_git_url'], result['repo_name'],
                        result['branch_name'], result['is_default_branch'],
                        result['scan_time'], result['scan_json']
                    ))
                    if len(batch_data) >= BATCH_SIZE:
                        cursor.executemany(sql, batch_data)
                        inserted_count += len(batch_data)
                        print(f"Inserted batch {i//BATCH_SIZE + 1}: {len(batch_data)} records ({inserted_count} total)")
                        batch_data = []
                except Exception as e:
                    print(f"Error preparing record {i+1}: {e}")
                    continue
            if batch_data:
                cursor.executemany(sql, batch_data)
                inserted_count += len(batch_data)
                print(f"Inserted final batch: {len(batch_data)} records ({inserted_count} total)")
            connection.commit()
            print(f"Successfully inserted {inserted_count} records into database")
            return inserted_count
    except Exception as e:
        print(f"Error inserting data: {e}")
        import traceback
        traceback.print_exc()
        return 0


def get_dolphinscheduler_params():
    return (
        '${repo_url}', '${auth_login}', '${auth_token}', '${repo_id}', '${show_branch}',
        '${salt}',
        '${openlibing_doris_url}', '${openlibing_doris_driver}',
        '${openlibing_doris_username}', '${openlibing_doris_password}'
    )


def decrypt_token(encrypted_token, salt):
    try:
        cmd = ['java', '-jar', 'utils/decrypt-tool.jar', '--salt', salt, encrypted_token]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error decrypting token: [REDACTED]")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"Unexpected error during token decryption: {e}")
        return None


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


def construct_auth_url(repo_url, auth_login, auth_token):
    if 'gitcode' in repo_url or 'gitee' in repo_url or 'github' in repo_url:
        base_url = repo_url.split('://')[0] + '://'
        repo_path = repo_url.split('://')[1]
        return f"{base_url}{auth_login}:{auth_token}@{repo_path}"
    return repo_url


def get_platform_from_url(repo_url):
    """从 URL 提取平台名（gitcode/github/gitee/gitlab/bitbucket）。
    复刻自处理脚本.python。
    """
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
    repo_name 是末段（去掉 .git 后缀）。
    复刻自处理脚本.python。
    """
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
    与处理脚本.python 完全一致。
    """
    platform = get_platform_from_url(repo_url)
    owner, repo_name = parse_repo_identity(repo_url)
    return os.path.join(base_dir, platform, owner, repo_name)


def mask_auth_url(auth_url):
    if '://' in auth_url and '@' in auth_url:
        protocol_part, rest = auth_url.split('://', 1)
        if ':' in rest and '@' in rest:
            auth_part, repo_part = rest.split('@', 1)
            if ':' in auth_part:
                username, _ = auth_part.split(':', 1)
                return f"{protocol_part}://{username}:******@{repo_part}"
    return auth_url


def pull_repository(auth_url, target_dir, max_retries=1, retry_delay=10):
    masked = mask_auth_url(auth_url)
    for attempt in range(1, max_retries + 1):
        try:
            if attempt == 1:
                print("Checking if git is installed...", flush=True)
                git_check = subprocess.run(['git', '--version'], capture_output=True, text=True)
                if git_check.returncode != 0:
                    print(f"Git check failed: {git_check.stderr}", flush=True)
                    return False
            if os.path.exists(target_dir):
                delete_directory(target_dir)
            os.makedirs(target_dir, exist_ok=True)
            print(f"Cloning repository from {masked} to {target_dir} (attempt {attempt}/{max_retries})", flush=True)
            result = subprocess.run(['git', 'clone', auth_url, target_dir],
                                    capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print(f"Repository cloned successfully", flush=True)
                return True
            stderr = result.stderr or ''
            network_errors = [
                'curl 28', 'curl 7', 'Could not resolve', 'Couldn\'t connect',
                'Connection timed out', 'Connection refused', 'Network is unreachable',
                'RPC failed', 'early EOF', 'fatal: the remote end hung up',
                'SSL certificate problem'
            ]
            is_net = any(kw.lower() in stderr.lower() for kw in network_errors)
            if is_net and attempt < max_retries:
                print(f"Network error: {stderr.strip()}", flush=True)
                print(f"Retrying in {retry_delay}s...", flush=True)
                time.sleep(retry_delay)
                continue
            else:
                print(f"Error cloning: {stderr.strip()}", flush=True)
                return False
        except subprocess.TimeoutExpired:
            print(f"Clone timed out on attempt {attempt}", flush=True)
            return False
        except FileNotFoundError:
            print("Git is not installed or not in PATH.", flush=True)
            return False
        except Exception as e:
            print(f"Unexpected error: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False
    return False


def checkout_branch(repo_path, branch_name):
    # -c safe.directory=* 跳过 dubious ownership 检查（处理脚本 clone 的仓库所有权可能不同）
    git_safe_args = ['-c', 'safe.directory=*']
    try:
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


def sync_branch_to_latest(auth_url, repo_path, branch_name, max_retries=2, retry_delay=10):
    """检查 show_branch 是否有刷新，有则拉取最新代码并强制对齐到远程。

    返回 True 表示可继续扫描，False 表示失败需跳过。
    fetch 失败时降级到仅 checkout_branch（用本地副本，可能不是最新）。
    """
    git_safe_args = ['-c', 'safe.directory=*']

    # 步骤 0: 清理残留的 .git/index.lock（上一轮 git 进程异常退出遗留，只在当前仓库生效）
    _lock_file = os.path.join(repo_path, '.git', 'index.lock')
    if os.path.isfile(_lock_file):
        try:
            os.remove(_lock_file)
            print(f"  cleaned stale index.lock in {repo_path}", flush=True)
        except OSError as e:
            print(f"  failed to clean stale index.lock: {e}", flush=True)
            # 不中断，后续 git 命令失败时按原有 fallback 处理

    # 步骤 1: 刷新 origin URL（复用最新 auth_token，避免处理脚本 clone 时的 token 过期）
    try:
        subprocess.run(
            ['git', *git_safe_args, '-C', repo_path, 'remote', 'set-url', 'origin', auth_url],
            capture_output=True, text=True, timeout=300
        )
    except Exception as e:
        print(f"Warning: failed to refresh origin URL: {e}", flush=True)
        # 不中断，继续尝试 fetch（旧 URL 可能还能用）

    # 步骤 2: fetch 单个目标分支（增量传输，比 fetch --all 轻量）
    network_errors = [
        'curl 28', 'curl 7', 'Could not resolve', 'Couldn\'t connect',
        'Connection timed out', 'Connection refused', 'Network is unreachable',
        'RPC failed', 'early EOF', 'fatal: the remote end hung up',
        'SSL certificate problem'
    ]
    fetch_ok = False
    for attempt in range(1, max_retries + 1):
        try:
            result = subprocess.run(
                ['git', *git_safe_args, '-C', repo_path, 'fetch', 'origin', branch_name],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                fetch_ok = True
                break
            stderr = result.stderr or ''
            is_net = any(kw.lower() in stderr.lower() for kw in network_errors)
            if is_net and attempt < max_retries:
                print(f"Fetch network error: {stderr.strip()}, retrying in {retry_delay}s...", flush=True)
                time.sleep(retry_delay)
                continue
            else:
                print(f"Fetch failed: {stderr.strip()}", flush=True)
                break
        except subprocess.TimeoutExpired:
            print(f"Fetch timed out on attempt {attempt}", flush=True)
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                break
        except Exception as e:
            print(f"Fetch unexpected error: {e}", flush=True)
            break

    # fetch 失败：降级到仅 checkout（用本地副本，可能不是最新）
    if not fetch_ok:
        print(f"Fetch failed, falling back to local checkout only (may not be latest)", flush=True)
        return checkout_branch(repo_path, branch_name)

    # 步骤 3: 比较本地 HEAD 和 origin/<branch> 的 commit SHA
    local_sha = ''
    remote_sha = ''
    try:
        local_result = subprocess.run(
            ['git', *git_safe_args, '-C', repo_path, 'rev-parse', branch_name],
            capture_output=True, text=True, timeout=10
        )
        if local_result.returncode == 0:
            local_sha = local_result.stdout.strip()
        remote_result = subprocess.run(
            ['git', *git_safe_args, '-C', repo_path, 'rev-parse', f'origin/{branch_name}'],
            capture_output=True, text=True, timeout=10
        )
        if remote_result.returncode == 0:
            remote_sha = remote_result.stdout.strip()
    except Exception as e:
        print(f"Warning: failed to compare SHA: {e}, forcing reset", flush=True)

    # 步骤 4: 按比较结果决定操作
    if local_sha and remote_sha and local_sha == remote_sha:
        # SHA 一致（无刷新）→ 仅 checkout，复用本地副本
        print(f"Branch {branch_name} already up-to-date (SHA: {local_sha[:8]})", flush=True)
        return checkout_branch(repo_path, branch_name)
    else:
        # SHA 不一致或比较失败（有刷新）→ 强制同步
        local_disp = local_sha[:8] if local_sha else 'N/A'
        remote_disp = remote_sha[:8] if remote_sha else 'N/A'
        print(f"Branch {branch_name} has updates (local: {local_disp} -> remote: {remote_disp}), syncing...", flush=True)
        try:
            step_start = time.time()
            # clean untracked files
            subprocess.run(
                ['git', *git_safe_args, '-C', repo_path, 'clean', '-fd'],
                capture_output=True, text=True, timeout=600
            )
            print(f"  clean -fd done in {time.time() - step_start:.1f}s", flush=True)

            step_start = time.time()
            # detach HEAD（只移指针，不写文件），为 reset 做准备
            # 仓库可能处于 unborn 状态（如 clone 中断），此时 checkout 失败可忽略，reset 会兜底
            detach_result = subprocess.run(
                ['git', *git_safe_args, '-C', repo_path, 'checkout', '--detach'],
                capture_output=True, text=True, timeout=300
            )
            if detach_result.returncode == 0:
                print(f"  checkout --detach done in {time.time() - step_start:.1f}s", flush=True)
            else:
                print(f"  checkout --detach skipped (repo in unborn state), reset will handle", flush=True)

            step_start = time.time()
            # 一步到位对齐到远程（省掉 checkout -f 的全量写盘）
            subprocess.run(
                ['git', *git_safe_args, '-C', repo_path, 'reset', '--hard', f'origin/{branch_name}'],
                capture_output=True, text=True, check=True, timeout= 600
            )
            print(f"  reset --hard origin/{branch_name} done in {time.time() - step_start:.1f}s", flush=True)

            print(f"Branch {branch_name} synced to origin/{branch_name}", flush=True)
            return True
        except subprocess.TimeoutExpired as e:
            print(f"Timeout syncing branch {branch_name}: cmd={e.cmd} timeout={e.timeout}s", flush=True)
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error syncing branch {branch_name}: {e.stderr}", flush=True)
            return False
        except Exception as e:
            print(f"Unexpected error syncing branch {branch_name}: {e}", flush=True)
            return False


def delete_directory(path):
    try:
        if os.path.exists(path):
            import shutil
            shutil.rmtree(path)
            print(f"Deleted directory: {path}")
        return True
    except Exception as e:
        print(f"Error deleting directory {path}: {e}")
        return False


def get_top_languages(repo_id, branch_name, connection):
    try:
        lang_stats = []
        with connection.cursor() as cursor:
            sql = """
                  SELECT language, SUM(code_lines) as code_lines
                  FROM dwi_code_scan_language
                  WHERE repo_id = %s AND branch_name = %s
                    AND scan_time = (
                      SELECT MAX(scan_time) FROM dwi_code_scan_language
                      WHERE repo_id = %s AND branch_name = %s
                  )
                  GROUP BY language
                  ORDER BY code_lines DESC \
                  """
            cursor.execute(sql, (repo_id, branch_name, repo_id, branch_name))
            lang_stats = cursor.fetchall()
        if not lang_stats:
            with connection.cursor() as cursor:
                sql = """
                      SELECT language, SUM(code_lines) as code_lines
                      FROM sdi_code_scan_language
                      WHERE repo_id = %s AND branch_name = %s
                        AND scan_time = (
                          SELECT MAX(scan_time) FROM sdi_code_scan_language
                          WHERE repo_id = %s AND branch_name = %s
                      )
                      GROUP BY language
                      ORDER BY code_lines DESC \
                      """
                cursor.execute(sql, (repo_id, branch_name, repo_id, branch_name))
                lang_stats = cursor.fetchall()
        if not lang_stats:
            print(f"No language data for repo_id={repo_id}, branch={branch_name}")
            return []

        # 特殊仓例外：剔除被误判/工具类语言（如 405446 的 JavaScript 来自单个超大 CI 脚本）
        ignored = LANG_IGNORE_OVERRIDES.get(str(repo_id), [])
        if ignored:
            lang_stats = [s for s in lang_stats if s['language'] not in ignored]
            if not lang_stats:
                print(f"All languages ignored for repo_id={repo_id}, ignored={ignored}")
                return []

        total_lines = sum(s['code_lines'] for s in lang_stats)
        top2 = lang_stats[:2]
        for lang in top2:
            lang['ratio'] = round(lang['code_lines'] / total_lines, 4) if total_lines > 0 else 0
        return [{"name": s['language'], "code_lines": s['code_lines'], "ratio": s['ratio']} for s in top2]
    except Exception as e:
        print(f"Error getting top languages: {e}")
        import traceback
        traceback.print_exc()
        return []


def _candidate_filenames(pattern):
    """对点开头的 dotfile，同时返回带点和不带点两个候选名；
    非 dotfile 或 glob 通配模式原样返回。"""
    if pattern.startswith('.') and '*' not in pattern and '?' not in pattern:
        return [pattern, pattern[1:]]
    return [pattern]


def _normalize_lang(name):
    """将SCC输出的语言名标准化为配置映射表中的key。
    按 language_classification.md 全量适配：C 系列、Python 系列、JS 系列、Java 系列等。
    """
    lang_map = {
        # C 系列（含 C#/ObjC/Cuda/D/Nim/Haxe）
        'c': 'C',
        'c header': 'C',
        'c++': 'C++',
        'c++ header': 'C++',
        'cpp': 'C++',
        'c#': 'C++',
        'objective c': 'C++',
        'objective c++': 'C++',
        'objc': 'C++',
        'obj-c': 'C++',
        'cuda': 'C++',
        'd': 'C++',
        'nim': 'C++',
        'haxe': 'C++',
        # Rust 系列
        'rust': 'Rust',
        # Python 系列
        'python': 'Python',
        'cython': 'Python',
        # JavaScript 系列
        'javascript': 'JavaScript',
        'js': 'JavaScript',
        'typescript': 'TypeScript',
        'ts': 'TypeScript',
        'typescript typings': 'TypeScript',
        'vue': 'JavaScript',
        'jsx': 'JavaScript',
        'mdx': 'JavaScript',
        'coffeescript': 'JavaScript',
        'arkts': 'JavaScript',
        'ark ts': 'JavaScript',
        'reasonml': 'JavaScript',
        'rescript': 'JavaScript',
        'flow9': 'JavaScript',
        # Java 系列（JVM 语言）
        'java': 'Java',
        'javaserver pages': 'Java',
        'jsp': 'Java',
        'kotlin': 'Java',
        'scala': 'Java',
        'groovy': 'Java',
        'clojure': 'Java',
        # Go 系列
        'go': 'Go',
        'golang': 'Go',
    }
    return lang_map.get(name.lower(), name)


def is_go_language(name):
    return _normalize_lang(name) == 'Go'


def check_config_file(repo_path, filenames, subdirs=None):
    """
    在根目录及指定子目录下搜索配置文件。
    搜索顺序：根目录优先，根目录未命中时按 subdirs 顺序回退。
    subdirs 为相对 repo_path 的子目录名列表，例如 ['pre-commit']。
    对点开头的 dotfile 同时接受带点和不带点两个候选名。
    """
    search_dirs = [repo_path]
    if subdirs:
        for sd in subdirs:
            search_dirs.append(os.path.join(repo_path, sd))

    for base_dir in search_dirs:
        if not os.path.isdir(base_dir):
            continue
        for pattern in filenames:
            # dotfile 放宽：同时尝试带点和不带点两个候选名
            for candidate in _candidate_filenames(pattern):
                if '*' in candidate or '?' in candidate:
                    full_pattern = os.path.join(base_dir, candidate)
                    matches = glob.glob(full_pattern)
                    for matched in matches:
                        size = os.path.getsize(matched)
                        if size > 0:
                            rel = os.path.relpath(matched, repo_path)
                            return {"found": True, "file": rel, "size": size}
                else:
                    filepath = os.path.join(base_dir, candidate)
                    if os.path.exists(filepath):
                        size = os.path.getsize(filepath)
                        if size > 0:
                            rel = os.path.relpath(filepath, repo_path)
                            return {"found": True, "file": rel, "size": size}
    return {"found": False, "file": None, "size": 0}


def check_java_google_format(repo_path):
    search_files = ['pom.xml', 'build.gradle', 'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts']
    search_dirs = [repo_path, os.path.join(repo_path, 'pre-commit')]
    try:
        for base_dir in search_dirs:
            if not os.path.isdir(base_dir):
                continue
            for f in search_files:
                fp = os.path.join(base_dir, f)
                if os.path.exists(fp) and os.path.getsize(fp) > 0:
                    try:
                        result = subprocess.run(
                            ['grep', '-r', 'google-java-format', fp],
                            capture_output=True, text=True, timeout=10
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            rel = os.path.relpath(fp, repo_path)
                            return {"has_config": True, "config_file": rel,
                                    "config_size": os.path.getsize(fp),
                                    "status": "pass", "detail": ""}
                    except Exception:
                        pass
        return {"has_config": False, "config_file": None, "config_size": 0,
                "status": "fail", "detail": "google-java-format not found"}
    except Exception as e:
        return {"has_config": False, "config_file": None, "config_size": 0,
                "status": "error", "detail": str(e)}


def check_code_style(repo_path, top_languages):
    result = {}
    for lang_info in top_languages:
        lang_name = lang_info['name']
        normalized = _normalize_lang(lang_name)
        r = {
            "language": lang_name, "is_top2": True,
            "has_config": False, "config_file": None, "config_size": 0,
            "status": "fail", "detail": ""
        }
        if normalized == 'Go':
            r["has_config"] = True
            r["config_file"] = "builtin"
            r["config_size"] = -1
            r["status"] = "pass"
            r["detail"] = "Go语言默认支持编码风格"
        elif normalized == 'Java':
            jf_result = check_java_google_format(repo_path)
            r.update(jf_result)
        elif normalized in ('C', 'C++'):
            # C/C++ 编码风格配置判断（双重来源，两条路径都探测，不短路）：
            # 1) .clang-format 文件存在且非空（根目录或 pre-commit 子目录）
            # 2) .pre-commit-config.yaml 中存在 id: clang-format 的 hook
            # 命中任一即 pass；新增 match_source 字段记录具体命中的来源：
            #   - "clang_format_file" : 仅 .clang-format 文件命中
            #   - "pre_commit_hook"   : 仅 pre-commit hook 命中
            #   - "both"              : 两条路径都命中
            #   - "none"              : 都未命中
            # 原有字段（has_config/config_file/config_size/status/detail）语义不变
            filenames = STYLE_CONFIG_MAP.get(normalized, [])
            cfg_result = check_config_file(repo_path, filenames, subdirs=['pre-commit'])
            hook_result = check_pre_commit_clang_format_hook(repo_path)

            matched = []
            if cfg_result["found"]:
                matched.append('clang_format_file')
            if hook_result["found"]:
                matched.append('pre_commit_hook')
            r["match_source"] = 'both' if len(matched) == 2 else (matched[0] if matched else 'none')

            if cfg_result["found"]:
                # 路径1优先（保持与原逻辑兼容：config_file 优先记 .clang-format）
                r["has_config"] = True
                r["config_file"] = cfg_result["file"]
                r["config_size"] = cfg_result["size"]
                r["status"] = "pass"
            elif hook_result["found"]:
                r["has_config"] = True
                r["config_file"] = hook_result["file"]
                r["config_size"] = hook_result["size"]
                r["status"] = "pass"
                r["detail"] = "通过 pre-commit clang-format hook 识别"
            else:
                r["detail"] = "未找到 .clang-format 或 pre-commit clang-format hook"
        else:
            filenames = STYLE_CONFIG_MAP.get(normalized, [])
            if not filenames:
                r["has_config"] = 2
                r["config_file"] = "N/A"
                r["config_size"] = -1
                r["status"] = "N/A"
                r["detail"] = f"语言 {lang_name} 不在检查范围内"
                result[lang_name] = r
                continue
            cfg_result = check_config_file(repo_path, filenames, subdirs=['pre-commit'])
            if cfg_result["found"]:
                r["has_config"] = True
                r["config_file"] = cfg_result["file"]
                r["config_size"] = cfg_result["size"]
                r["status"] = "pass"
            else:
                r["detail"] = f"未找到 {' 或 '.join(filenames)}（文件不存在或为空）"
        result[lang_name] = r
    return result


def check_pre_commit(repo_path):
    config_files = ['.pre-commit-config.yaml', '.lintrunner.toml']
    result = check_config_file(repo_path, config_files, subdirs=['pre-commit'])
    return {
        "has_config": result["found"],
        "config_file": result["file"],
        "config_size": result["size"],
        "status": "pass" if result["found"] else "fail",
        "detail": "" if result["found"] else f"未找到 {' 或 '.join(config_files)}"
    }


def check_pre_commit_clang_format_hook(repo_path):
    """检查 .pre-commit-config.yaml 中是否存在 id: clang-format 的 hook。

    查找位置：根目录 + pre-commit 子目录（与 check_pre_commit 保持一致）。
    匹配规则：hooks 列表中存在 id 为 clang-format 的条目，不强制校验 files 过滤项。
    返回：{"found": bool, "file": rel_path or None, "size": int}
    """
    result = check_config_file(repo_path, ['.pre-commit-config.yaml'], subdirs=['pre-commit'])
    if not result["found"]:
        return {"found": False, "file": None, "size": 0}

    file_path = os.path.join(repo_path, result["file"])
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # 匹配 YAML 列表项 "- id: clang-format"，兼容不同缩进
        if re.search(r'^\s*-\s*id:\s*clang-format\s*$', content, re.MULTILINE):
            return {"found": True, "file": result["file"], "size": result["size"]}
    except Exception as e:
        print(f"Error checking clang-format hook in {result['file']}: {e}")
    return {"found": False, "file": None, "size": 0}


def _check_ci_autofix_reason(content):
    """解析 pre-commit-ci 配置, 返回 (是否达标, 未达标原因文案或None)。

    判定: 配置顶层存在 ci: 块, 且 ci.autofix_prs 为布尔 true。
    优先用 PyYAML 精确解析; PyYAML 不可用或语法异常时降级正则。
    """
    try:
        import yaml
        cfg = yaml.safe_load(content)
        if cfg is None:
            cfg = {}
        if not isinstance(cfg, dict):
            return False, '配置文件解析失败（内容不是 YAML 映射）'
        ci = cfg.get('ci')
        if not isinstance(ci, dict):
            return False, '存在 pre-commit 配置文件，但缺少顶层 ci: 配置块'
        if 'autofix_prs' not in ci:
            return False, '存在 ci: 配置块，但未配置 autofix_prs'
        if ci.get('autofix_prs') is True:
            return True, None
        return False, 'autofix_prs 未开启（仅 autofix_prs: true 视为已接入）'
    except ImportError:
        pass
    except Exception:
        return False, '配置文件解析失败（YAML 语法或格式异常）'

    # ---- 降级: 正则解析（PyYAML 不可用时）----
    lines = content.split('\n')

    def _is_top_key(s):
        # 顶层映射键: 行首无缩进, 形如 "key:" 或 "key: value"
        return re.match(r'^[^\s#][^:]*:', s) is not None

    ci_idx = None
    for _i, ln in enumerate(lines):
        if re.match(r'^ci\s*:', ln) is not None:
            ci_idx = _i
            break
    if ci_idx is None:
        return False, '存在 pre-commit 配置文件，但缺少顶层 ci: 配置块'
    for ln in lines[ci_idx + 1:]:
        s = ln.strip()
        if s == '' or s.startswith('#'):
            continue
        if _is_top_key(ln):
            break
        m = re.match(r'^(\s*)autofix_prs\s*:\s*(.+?)\s*(#.*)?$', ln)
        if m:
            val = m.group(2).strip()
            if val in ('true', 'True', 'TRUE', 'yes', 'Yes', 'on', 'On'):
                return True, None
            return False, 'autofix_prs 未开启（仅 autofix_prs: true 视为已接入）'
    return False, '存在 ci: 配置块，但未配置 autofix_prs'


def check_pre_commit_ci_autofix(repo_path):
    """检查仓库是否接入 pre-commit.ci 的代码风格自动修复。

    GitHub 仓专属指标4判定: 根目录(pre-commit 子目录)存在 .pre-commit-config.yaml/.yml,
    且顶层 ci.autofix_prs 为布尔 true 即为已接入。
    返回: {"pass": bool, "file": rel_path or None, "reason": 未达标文案 or None}
    """
    config_files = ['.pre-commit-config.yaml', '.pre-commit-config.yml']
    result = check_config_file(repo_path, config_files, subdirs=['pre-commit'])
    base = {"pass": False, "file": None, "reason": None}
    if not result["found"]:
        base["reason"] = '未找到 .pre-commit-config.yaml 或 .pre-commit-config.yml（文件不存在或为空）'
        return base
    file_path = os.path.join(repo_path, result["file"])
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {result['file']}: {e}")
        base["reason"] = '配置文件读取失败'
        return base
    ok, reason = _check_ci_autofix_reason(content)
    base["pass"] = ok
    base["file"] = result["file"]
    base["reason"] = reason
    return base


def _run_cmd(cmd, cwd, timeout=300):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, shell=True)
        out = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            return out, True
        else:
            return out, False
    except Exception as e:
        return str(e), False


def check_python_ruff(repo_path):
    result = {"default_rules": 0, "enabled_rules": 0, "extra_rules": 0, "status": "ok", "detail": ""}
    try:
        # 不用 2>/dev/null | wc -l 管道, 直接跑 ruff linter, 让工具不存在时能正确报 error
        # ruff linter 输出每行一个 linter 名, 用 Python 数非空行数
        out1, ok1 = _run_cmd('ruff linter --isolated', repo_path)
        if ok1 and out1:
            result["default_rules"] = len([l for l in out1.split('\n') if l.strip()])
        out2, ok2 = _run_cmd('ruff linter', repo_path)
        if ok2 and out2:
            result["enabled_rules"] = len([l for l in out2.split('\n') if l.strip()])

        if not ok1 or not ok2:
            result["status"] = "error"
            result["detail"] = f"ruff cmd fail ok1={ok1} ok2={ok2} | err1={out1[:200] if not ok1 else 'N/A'} err2={out2[:200] if not ok2 else 'N/A'}"
        elif result["default_rules"] > 0 and result["enabled_rules"] > 0:
            result["extra_rules"] = result["enabled_rules"] - result["default_rules"]
        else:
            result["status"] = "error"
            result["detail"] = f"ruff empty output out1_len={len(out1)} out2_len={len(out2)}"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


def check_cpp_clang_format(repo_path):
    result = {"custom_rules_count": 0, "custom_rules_detail": [], "status": "ok", "detail": ""}
    try:
        clang_format_bin = 'clang-format'
        # 方案A: 直接统计 --style=file --dump-config 输出的顶层 key 数
        # 输出 = 项目实际生效的所有配置项 (LLVM 默认 + .clang-format 显式修改的合并结果)
        # 顶层 key 格式: 顶格, 形如 "Key: value" 或 "Key:"
        # 等价于 shell: clang-format -style=file -dump-config | grep -E "^[A-Za-z]" | wc -l
        out2, ok2 = _run_cmd(f'{clang_format_bin} --style=file --dump-config', repo_path)
        if not ok2 or not out2:
            result["status"] = "error"
            result["detail"] = f"clang-format fail cmd={clang_format_bin} ok={ok2} err={out2[:200]}"
            return result

        # 统计顶层 key 数量 (行首是字母, 含冒号)
        rule_keys = []
        for line in out2.split('\n'):
            line = line.rstrip()
            if line and line[0].isalpha() and ':' in line:
                key = line.split(':')[0].strip()
                if key and key not in rule_keys:
                    rule_keys.append(key)

        result["custom_rules_count"] = len(rule_keys)
        result["custom_rules_detail"] = rule_keys
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


def check_cpp_clang_tidy(repo_path):
    """
    指标3 - C++: clang-tidy检查项统计
    clang-tidy --list-checks  → 列出项目实际启用的 checks（第一行 "Enabled checks:", 后续每行一个 check）
    注意: 不使用 --checks='*'。clang-tidy 默认不启用任何 check，需项目 .clang-tidy 配置才会启用。
          若项目无 .clang-tidy，返回 0（反映项目实际未配置 clang-tidy 规则）。
    """
    result = {"checks_count": 0, "status": "ok", "detail": ""}
    try:
        # 不用 2>/dev/null | wc -l 管道, 直接跑 clang-tidy --list-checks
        # 工具不存在时 returncode 非 0, 能正确报 error (避免管道假阳性)
        out, ok = _run_cmd('clang-tidy --list-checks', repo_path)
        if ok and out:
            # 跳过标题行 "Enabled checks:" 和空行, 统计实际 check 数
            checks_lines = [
                l for l in out.split('\n')
                if l.strip() and not l.strip().startswith('Enabled checks')
            ]
            result["checks_count"] = len(checks_lines)
        else:
            result["status"] = "error"
            result["detail"] = f"clang-tidy --list-checks failed: {out[:200]}"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


def check_java_checkstyle(repo_path):
    result = {"modules_count": 0, "config_file": None, "status": "ok", "detail": ""}
    try:
        found_xml = None
        for cp in CHECKSTYLE_PATHS:
            fp = os.path.join(repo_path, cp)
            if os.path.exists(fp):
                found_xml = fp
                result["config_file"] = cp
                break
        if found_xml:
            out, ok = _run_cmd(f"grep -c '<module name=' {found_xml}", repo_path)
            if ok and out:
                try:
                    result["modules_count"] = int(out.strip())
                except (ValueError, TypeError):
                    pass
            else:
                result["status"] = "error"
                result["detail"] = f"grep checkstyle.xml failed: {out}"
        else:
            result["detail"] = f"checkstyle.xml not found in paths: {CHECKSTYLE_PATHS}"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


def check_java_spotless(repo_path):
    result = {"has_config": False, "config_source": None, "status": "ok", "detail": ""}
    try:
        for f in ['pom.xml', 'build.gradle', 'build.gradle.kts']:
            fp = os.path.join(repo_path, f)
            if os.path.exists(fp) and os.path.getsize(fp) > 0:
                try:
                    grep_result = subprocess.run(
                        ['grep', '-i', 'spotless', fp],
                        capture_output=True, text=True, timeout=10
                    )
                    if grep_result.returncode == 0 and grep_result.stdout.strip():
                        result["has_config"] = True
                        result["config_source"] = f
                        break
                except Exception:
                    pass
        if not result["has_config"]:
            result["detail"] = "spotless not found in pom.xml or build.gradle"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


def check_java_spotbugs(repo_path):
    return {"status": "skipped", "detail": "需要编译环境，暂不自动分析"}


def run_quality_scan(repo_id, branch_name, repo_path, repo_git_url, repo_name,
                     is_default_branch, scan_time, connection):
    top_languages = get_top_languages(repo_id, branch_name, connection)
    if not top_languages:
        print(f"No language data for {repo_name}:{branch_name}, skipping quality checks")
        top_languages = []

    code_style = check_code_style(repo_path, top_languages)
    pre_commit = check_pre_commit(repo_path)
    pre_commit_ci = check_pre_commit_ci_autofix(repo_path)

    check_rules = {}
    lang_names = set(_normalize_lang(l['name']) for l in top_languages) if top_languages else set()

    if 'Python' in lang_names:
        check_rules['Python'] = {"ruff": check_python_ruff(repo_path)}
    if 'C++' in lang_names or 'C' in lang_names:
        lang_key = 'C++' if 'C++' in lang_names else 'C'
        check_rules[lang_key] = {
            "clang_format": check_cpp_clang_format(repo_path),
            "clang_tidy": check_cpp_clang_tidy(repo_path)
        }
    if 'Java' in lang_names:
        check_rules['Java'] = {
            "checkstyle": check_java_checkstyle(repo_path),
            "spotless": check_java_spotless(repo_path),
            "spotbugs": check_java_spotbugs(repo_path),
            "google_java_format": check_java_google_format(repo_path)
        }

    return {
        "scan_time": scan_time,
        "scan_status": "success",
        "scan_error": "",
        "top_languages": top_languages,
        "code_style": code_style,
        "pre_commit": pre_commit,
        "pre_commit_ci": pre_commit_ci,
        "check_rules": check_rules
    }


def build_null_scan_data(scan_time, scan_status, scan_error, repo_id, branch_name, connection):
    """构建空指标扫描数据（本地仓库不存在或同步失败时使用）。

    top_languages 仍从 DB 查询（语言统计独立于本地仓库，是事实数据）；
    文件级指标（code_style/pre_commit/check_rules）置空，由 dwi 层根据
    scan_status 将"已检查类"指标置 NULL，与"检查了但不达标"区分开。
    """
    top_languages = get_top_languages(repo_id, branch_name, connection)
    return {
        "scan_time": scan_time,
        "scan_status": scan_status,
        "scan_error": scan_error,
        "top_languages": top_languages,
        "code_style": {},
        "pre_commit": {},
        "pre_commit_ci": {},
        "check_rules": {}
    }


def main():
    args = parse_arguments()
    print("=== Debug Information ===")
    print(f"Command line arguments: {sys.argv}")

    repo_url_list = args.repo_url
    auth_login_list = args.auth_login
    auth_token_list = args.auth_token
    repo_id_list = args.repo_id
    show_branch_list = args.show_branch

    doris_url = None
    doris_username = None
    doris_password = None
    salt = None

    if not all([repo_url_list, auth_login_list, auth_token_list, repo_id_list, show_branch_list]):
        print("No params from command line, trying DS environment variables...")
        (repo_url_list, auth_login_list, auth_token_list, repo_id_list, show_branch_list,
         salt, doris_url, _, doris_username, doris_password) = get_dolphinscheduler_params()
        print(f"repo_url from env: {repo_url_list}")
        print(f"show_branch from env: {show_branch_list}")

    if not all([repo_url_list, auth_login_list, auth_token_list, repo_id_list, show_branch_list]):
        print("ERROR: Missing required parameters.")
        return 1

    create_directory(args.target_dir)

    try:
        def parse_list(val):
            if not val:
                return []
            if not (val.startswith('[') and val.endswith(']')):
                return [val]
            return ast.literal_eval(val)

        repo_urls = parse_list(repo_url_list)
        auth_logins = parse_list(auth_login_list)
        auth_tokens = parse_list(auth_token_list)
        repo_ids = parse_list(repo_id_list)
        show_branches = parse_list(show_branch_list)

        decrypted_auth_tokens = []
        if salt and not salt.startswith('$'):
            print("Decrypting auth tokens...")
            for et in auth_tokens:
                if et and not et.startswith('$'):
                    dt = decrypt_token(et, salt)
                    decrypted_auth_tokens.append(dt if dt else et)
                else:
                    decrypted_auth_tokens.append(et)
            auth_tokens = decrypted_auth_tokens
            print(f"Decrypted {len(auth_tokens)} tokens")
        else:
            print("No salt provided, skipping token decryption")

        lens = [len(repo_urls), len(auth_logins), len(auth_tokens), len(repo_ids), len(show_branches)]
        if len(set(lens)) != 1:
            print(f"ERROR: Lists must be same length: urls={lens[0]} logins={lens[1]} tokens={lens[2]} ids={lens[3]} branches={lens[4]}")
            return 1

        if len(repo_urls) == 0:
            print("ERROR: Empty lists.")
            return 1

    except Exception as e:
        print(f"Error processing data: {e}")
        return 1

    success_count = 0
    null_count = 0
    failure_count = 0
    total_repos = len(repo_urls)
    connection = None

    unified_scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Unified scan time: {unified_scan_time}")
    print(f"Total repos: {total_repos}")
    print("=" * 60)
    sys.stdout.flush()

    try:
        connection = get_db_connection(doris_url, doris_username, doris_password)

        for i in range(total_repos):
            repo_url = repo_urls[i]
            auth_login = auth_logins[i]
            auth_token = auth_tokens[i]
            repo_id = repo_ids[i]
            show_branch = show_branches[i]

            if not show_branch or str(show_branch).strip() == '':
                print(f"\n[{i+1}/{total_repos}] Skipping repo_id={repo_id}: show_branch is empty", flush=True)
                continue

            print(f"\nProcessing repository {i+1}/{total_repos}: id={repo_id} branch={show_branch}", flush=True)

            try:
                repo_name = get_repo_name(repo_url)
                full_target_dir = build_repo_path(args.target_dir, repo_url)
                auth_url = construct_auth_url(repo_url, auth_login, auth_token)

                # 仓库已由处理脚本预先 clone 到 full_target_dir
                # 三种情况：
                #   ① 本地目录不存在（pre-clone 失败）→ 写空指标记录，不丢弃
                #   ② sync 失败（fetch + checkout 都失败）→ 写空指标记录，不丢弃
                #   ③ 正常 → 执行质量扫描
                if not os.path.isdir(full_target_dir):
                    scan_error = f"local repo directory not found: {full_target_dir}"
                    print(f"Repo not found, inserting null metrics: {scan_error}", flush=True)
                    scan_data = build_null_scan_data(
                        unified_scan_time, 'repo_not_found', scan_error,
                        repo_id, show_branch, connection
                    )
                    null_count += 1
                elif not sync_branch_to_latest(auth_url, full_target_dir, show_branch):
                    scan_error = f"failed to sync branch {show_branch} to latest"
                    print(f"Sync failed, inserting null metrics: {scan_error}", flush=True)
                    scan_data = build_null_scan_data(
                        unified_scan_time, 'sync_failed', scan_error,
                        repo_id, show_branch, connection
                    )
                    null_count += 1
                else:
                    print(f"Running quality scan on {repo_name}:{show_branch}...", flush=True)
                    scan_data = run_quality_scan(
                        repo_id, show_branch, full_target_dir, repo_url, repo_name,
                        False, unified_scan_time, connection
                    )
                    success_count += 1

                scan_json_str = json.dumps(scan_data, ensure_ascii=False)

                results = [{
                    'repo_id': repo_id, 'repo_git_url': repo_url, 'repo_name': repo_name,
                    'branch_name': show_branch, 'is_default_branch': False,
                    'scan_time': unified_scan_time, 'scan_json': scan_json_str
                }]

                insert_scan_results_to_db(results, connection)
                # 不再 delete_directory：仓库生命周期由处理脚本管理

            except Exception as e:
                failure_count += 1
                print(f"Error processing repo id={repo_id}: {e}", flush=True)

            print(f"Progress: {i+1}/{total_repos} | OK: {success_count} NULL: {null_count} FAIL: {failure_count}", flush=True)
            print("-" * 60, flush=True)

    except Exception as e:
        print(f"Database connection error: {e}", flush=True)
        result = 1
    finally:
        if connection:
            try:
                connection.close()
                print("Database connection closed", flush=True)
            except Exception as e:
                print(f"Error closing connection: {e}", flush=True)

    print(f"\nSummary: {success_count} successful, {null_count} null metrics, {failure_count} failed", flush=True)

    if success_count == 0 and null_count == 0 and failure_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
