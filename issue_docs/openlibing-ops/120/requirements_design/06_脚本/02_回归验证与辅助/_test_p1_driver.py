#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时测试驱动（v2，2026-09-20 新口径）：只扫默认分支（sdi_repo_branch_info.default_branch，
不用 show_branch），走改造后的 sfs.clone_repo(branch=...) 真实验证 -b 参数 + 匿名回退；
COPYRIGHT 验证 v4.1 有空格正则。不连库，测完即删。"""
import importlib.util
import json
import os
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('sfs', os.path.join(BASE, 'security_file_scan.py'))
sfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfs)

# default_branch = sdi_repo_branch_info.default_branch（只扫默认分支，新口径）
REPOS = [
    {'repo_id': 400030, 'repo_url': 'https://gitcode.com/openUBMC/webui.git', 'default_branch': 'main'},
    {'repo_id': 401224, 'repo_url': 'https://gitcode.com/cann/ops-nn.git', 'default_branch': 'master'},
    {'repo_id': 401250, 'repo_url': 'https://gitcode.com/Ascend/MindIE-SD.git', 'default_branch': 'dev'},
    {'repo_id': 401227, 'repo_url': 'https://gitcode.com/cann/metadef.git', 'default_branch': 'master'},
    {'repo_id': 401234, 'repo_url': 'https://gitcode.com/cann/asnumpy.git', 'default_branch': 'master'},
    {'repo_id': 401239, 'repo_url': 'https://gitcode.com/cann/acl-extend.git', 'default_branch': None},
    {'repo_id': 401430, 'repo_url': 'https://gitcode.com/Ascend/pytorch.git', 'default_branch': 'master'},
    {'repo_id': 401431, 'repo_url': 'https://gitcode.com/Ascend/op-plugin.git', 'default_branch': 'master'},
    {'repo_id': 401651, 'repo_url': 'https://gitcode.com/openUBMC/dcmid.git', 'default_branch': 'main'},
    {'repo_id': 403142, 'repo_url': 'https://gitcode.com/kunpengcompute/kupl.git', 'default_branch': 'main'},
    {'repo_id': 405446, 'repo_url': 'https://github.com/triton-lang/triton-ascend.git', 'default_branch': 'main'},
    {'repo_id': 405682, 'repo_url': 'https://github.com/vllm-project/vllm-ascend.git', 'default_branch': 'main'},
]

# 2026-09-21 回归轮：clone 分支口径上轮已验证，全部复用已 clone 目录（仅验证打分逻辑回归）
FORCE_RECLONE = set()

work_dir = os.path.join(BASE, '_test_repos')
os.makedirs(work_dir, exist_ok=True)


def current_branch(repo_dir):
    """读已 clone 仓的当前分支（浅克隆 detached HEAD 时读 origin/HEAD）。"""
    import subprocess
    for args in (['rev-parse', '--abbrev-ref', 'HEAD'], ['symbolic-ref', '--short', 'refs/remotes/origin/HEAD']):
        r = subprocess.run(['git', '-c', 'safe.directory=*', '-C', repo_dir] + args,
                           capture_output=True, text=True, errors='replace')
        out = (r.stdout or '').strip()
        if r.returncode == 0 and out and out != 'HEAD':
            return out.replace('origin/', '')
    return '(unknown)'


summary = {}
fail = 0
for repo in REPOS:
    repo_dir = os.path.join(work_dir, f"repo_{repo['repo_id']}")
    branch = repo['default_branch']
    print(f"\n===== repo_id={repo['repo_id']} {repo['repo_url']} [default_branch={branch or 'HEAD'}] =====", flush=True)
    if repo['repo_id'] in FORCE_RECLONE:
        if os.path.isdir(repo_dir):
            sfs.rmtree_force(repo_dir)
        # 走生产 clone_repo（匿名，验证 branch 参数）
        if not sfs.clone_repo(repo['repo_url'], None, None, repo_dir, branch=branch):
            fail += 1
            continue
        actual = current_branch(repo_dir)
        flag = 'OK' if (branch is None or actual == branch) else 'MISMATCH!'
        print(f"  clone_repo done, actual branch={actual} [{flag}]", flush=True)
    elif os.path.isdir(os.path.join(repo_dir, '.git')):
        print(f"  reuse existing clone (branch={current_branch(repo_dir)})", flush=True)
    elif not sfs.clone_repo(repo['repo_url'], None, None, repo_dir, branch=branch):
        fail += 1
        continue
    try:
        results = sfs.scan_one_repo(repo, repo_dir, None, 200)
        summary[repo['repo_id']] = {}
        for code, (score, is_na, detail) in results.items():
            summary[repo['repo_id']][code] = 'NA' if is_na else score
            if code == 'COPYRIGHT':
                print(f"  COPYRIGHT: files={detail.get('target_file_count')} "
                      f"matched={detail.get('matched_count')}", flush=True)
            elif code == 'BINARY_ARTIFACTS':
                print(f"  BINARY_ARTIFACTS: hits={detail.get('binary_count')}", flush=True)
    except Exception:
        fail += 1
        import traceback
        traceback.print_exc()

# 汇总矩阵
print('\n' + '=' * 110)
header = f"{'repo':>8} | " + ' | '.join(f'{c[:9]:>9}' for c in
      ['COPYRIGHT', 'DANGEROUS_WF', 'TOKEN_PERM', 'BINARY_ART', 'PACKAGING', 'SAST', 'SEC_POLICY'])
print(header)
print('-' * 110)
for rid, row in summary.items():
    print(f"{rid:>8} | " + ' | '.join(
        f"{str(row.get(c, '-')):>9}" for c in
        ['COPYRIGHT', 'DANGEROUS_WF', 'TOKEN_PERM', 'BINARY_ARTIFACTS', 'PACKAGING', 'SAST', 'SECURITY_POLICY']))
print('=' * 110)
print(f"REPOS: {len(summary)} scanned, failures: {fail}")
sys.exit(1 if fail else 0)
