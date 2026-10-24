# -*- coding: utf-8 -*-
"""抽样测算：需求黑名单后缀在评估仓里的覆盖面（contents API BFS 遍历版）。

背景：需求方给出二进制制品指标的原始黑名单（后缀判定），与当前 gcheck
（OSSF Scorecard v5.5.0 内容识别）口径差异巨大。本脚本抽样若干仓，
逐目录遍历 GitCode 文件列表，统计黑名单后缀分布，量化口径切换的冲击面。
"""
import json
import os
import re
import sys
import time
import urllib.request

API = 'https://gitcode.com/api/v5'
TOKEN = os.environ.get('GC_TOKEN', '')
MAX_DIRS_PER_REPO = 400   # 单仓目录数上限（抽样够用，防超大仓跑不完）

# 需求黑名单（2026-10-16 用户提供）
BLACKLIST_EXEC = {'exe', 'dll', 'so', 'dylib', 'a', 'o', 'obj', 'pyc',
                  'class', 'jar', 'war', 'ear'}
BLACKLIST_ARCH = {'zip', 'tar', 'gz', '7z', 'rar', 'bz2', 'xz'}
BLACKLIST_DOC = {'pdf', 'doc', 'docx', 'xls', 'xlsx'}

REPOS = [
    ('openUBMC', 'webui'),
    ('openUBMC', 'devmon'),
    ('opengauss', 'Plugin'),
    ('cann', 'asnumpy'),
    ('Ascend', 'MindIE-SD'),
    ('boostkit', 'KAE'),
    ('Ascend', 'RecSDK'),
]


def http_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'survey',
                'Accept': 'application/json',
                **({'private-token': TOKEN} if TOKEN else {}),
            })
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            if i == retries - 1:
                print(f'  ! FAIL {url}: {e}', file=sys.stderr)
                return None
            time.sleep(2)


def walk(owner, repo, branch):
    """BFS 遍历目录，返回 (文件数, 分类计数, 目录访问数, 是否截断)。"""
    cnt = {'exec': 0, 'arch': 0, 'doc': 0}
    samples = {'exec': [], 'arch': [], 'doc': []}
    n_files = 0
    n_dirs = 0
    truncated = False
    queue = ['']
    while queue:
        path = queue.pop(0)
        n_dirs += 1
        if n_dirs > MAX_DIRS_PER_REPO:
            truncated = True
            break
        entries = http_json(
            f'{API}/repos/{owner}/{repo}/contents/{path}?ref={branch}')
        if entries is None or not isinstance(entries, list):
            continue
        for e in entries:
            t = e.get('type')
            if t == 'dir':
                queue.append(e['path'])
            elif t == 'file':
                n_files += 1
                name = e['path'].rsplit('/', 1)[-1]
                m = re.search(r'\.([A-Za-z0-9]+)$', name)
                ext = m.group(1).lower() if m else ''
                for cat, bl in (('exec', BLACKLIST_EXEC),
                                ('arch', BLACKLIST_ARCH),
                                ('doc', BLACKLIST_DOC)):
                    if ext in bl:
                        cnt[cat] += 1
                        if len(samples[cat]) < 3:
                            samples[cat].append(e['path'])
                        break
    return n_files, cnt, samples, n_dirs, truncated


def main():
    print(f"{'仓库':<28}{'文件数':>8}{'目录数':>7} {'可执行类':>7} {'压缩包类':>7} {'文档类':>6}  截断  示例")
    totals = {'exec': 0, 'arch': 0, 'doc': 0, 'violated': 0, 'repos': 0}
    for owner, repo in REPOS:
        info = http_json(f'{API}/repos/{owner}/{repo}')
        if not info:
            continue
        branch = info.get('default_branch') or 'master'
        n_files, cnt, samples, n_dirs, truncated = walk(owner, repo, branch)
        violated = any(cnt.values())
        totals['exec'] += cnt['exec']
        totals['arch'] += cnt['arch']
        totals['doc'] += cnt['doc']
        totals['repos'] += 1
        totals['violated'] += 1 if violated else 0
        ex = ' | '.join(samples['exec'][:1] + samples['arch'][:1] + samples['doc'][:1])
        print(f"{owner}/{repo:<20}{n_files:>8}{n_dirs:>7} {cnt['exec']:>7} "
              f"{cnt['arch']:>7} {cnt['doc']:>6}  {'是' if truncated else '否':>2}  {ex[:70]}")
    print('-' * 100)
    print(f"抽样 {totals['repos']} 仓：命中黑名单 {totals['violated']} 仓；"
          f"可执行类 {totals['exec']} / 压缩包类 {totals['arch']} / 文档类 {totals['doc']} 个文件")


if __name__ == '__main__':
    sys.exit(main())
