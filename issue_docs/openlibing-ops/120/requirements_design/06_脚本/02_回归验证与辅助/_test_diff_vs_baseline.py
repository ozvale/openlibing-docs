# -*- coding: utf-8 -*-
"""标点级粒度改动前后对比：新 _test_copyright_v2_result.json vs 基线 baseline_20261006"""
import io, sys, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912'
new = json.load(open(os.path.join(BASE, '_test_copyright_v2_result.json'), encoding='utf-8'))['results']
old = json.load(open(os.path.join(BASE, '_test_copyright_v2_result_baseline_20261006.json'), encoding='utf-8'))['results']

diffs = []
for repo in sorted(old):
    o, n = old[repo], new.get(repo)
    if n is None:
        diffs.append((repo, '缺失', None, None)); continue
    if o['is_na'] != n['is_na'] or abs((o['score'] or 0) - (n['score'] or 0)) > 1e-9:
        diffs.append((repo, o, n, None))

print(f'总仓数: old={len(old)} new={len(new)}  分数/NA 变化仓数: {len(diffs)}\n')
print(f"{'repo':<14}{'旧':>10}{'新':>10}   {'旧matched/target':<20}{'新matched/target':<20}分支(旧→新)")
big_drop, big_up = [], []
for repo, o, n, _ in diffs:
    if o == '缺失':
        print(f'{repo:<14}   缺失'); continue
    os_, ns_ = ('NA' if o['is_na'] else f"{o['score']:.2f}"), ('NA' if n['is_na'] else f"{n['score']:.2f}")
    ot, nt = f"{o['matched']}/{o['target']}", f"{n['matched']}/{n['target']}"
    br = f"{o['license_type']}→{n['license_type']}" if o['license_type'] != n['license_type'] else o['license_type']
    print(f'{repo:<14}{os_:>10}{ns_:>10}   {ot:<20}{nt:<20}{br}')
    d = (n['score'] or 0) - (o['score'] or 0)
    if d < -1: big_drop.append((repo, d))
    if d > 1: big_up.append((repo, d))

print(f'\n降分>1 的仓: {len(big_drop)}  升分>1 的仓: {len(big_up)}')

# 汇总: 原因计数对比
from collections import Counter
co, cn = Counter(), Counter()
for r in old.values():
    for k, v in (r.get('reasons') or {}).items(): co[k] += v
for r in new.values():
    for k, v in (r.get('reasons') or {}).items(): cn[k] += v
print('\n不合格原因计数 (旧 → 新):')
for k in sorted(set(co) | set(cn)):
    print(f'  {k:<22}{co.get(k,0):>8} → {cn.get(k,0):>8}')
