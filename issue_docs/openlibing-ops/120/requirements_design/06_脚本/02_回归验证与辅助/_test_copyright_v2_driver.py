#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时驱动（2026-10-06）：不连 Doris，离线复刻 load_copyright_templates（种子 SQL 11 条），
对 _test_repos 全部本地仓跑生产版 scan_copyright，汇总结果并与 demo 数据对照。
只读不写，测完即删。"""
import importlib.util
import io
import json
import os
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
SQL = os.path.join(BASE, '参考', 'copyright_template_config.sql')
REPOS_DIR = os.path.join(BASE, '_test_repos')
OUT = os.path.join(BASE, '_test_copyright_v3_result.json')

spec = importlib.util.spec_from_file_location('sfs', os.path.join(BASE, 'security_file_scan.py'))
sfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfs)


# ---------------- 种子 SQL 解析（字符级 tokenizer，支持多行字符串/数组/转义） ----------------

def parse_seed_sql(path):
    text = open(path, encoding='utf-8').read()
    rows, n = [], len(text)

    def skip_ws(j):
        while j < n and text[j] in ' \t\r\n':
            j += 1
        return j

    def parse_value(j):
        j = skip_ws(j)
        c = text[j]
        if c == "'":                      # 字符串字面量（'' 转义，可跨行）
            j += 1
            buf = []
            while j < n:
                if text[j] == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        buf.append("'"); j += 2; continue
                    return ''.join(buf), j + 1
                buf.append(text[j]); j += 1
            raise ValueError('unterminated string')
        if c == '[':                      # array<string>
            j += 1
            items = []
            while True:
                j = skip_ws(j)
                if text[j] == ']':
                    return items, j + 1
                v, j = parse_value(j)
                items.append(v)
                j = skip_ws(j)
                if text[j] == ',':
                    j += 1
        if text.startswith('NULL', j):    # NULL
            return None, j + 4
        k = j
        while k < n and (text[k].isdigit() or text[k] in '-.'):
            k += 1
        return int(text[j:k]) if '.' not in text[j:k] else float(text[j:k]), k

    # 种子 SQL 含多条独立 INSERT（mulan / builtin / custom 各一段），逐段解析
    for vals_idx in [m.start() for m in __import__('re').finditer(r'\bVALUES\b', text)]:
        i = text.index('(', vals_idx)
        while i < n:
            i = skip_ws(i)
            if text[i] != '(':
                break
            i += 1
            row = []
            while True:
                v, i = parse_value(i)
                row.append(v)
                i = skip_ws(i)
                if text[i] == ',':
                    i += 1; continue
                if text[i] == ')':
                    i += 1; break
            rows.append(row)
            i = skip_ws(i)
            if i < n and text[i] == ',':
                i += 1
            elif i < n and text[i] == ';':
                break
    return rows


def build_tpl_config(rows):
    """复刻 load_copyright_templates（security_file_scan.py L583-618）。"""
    enabled = [r for r in rows if r[9 - 1] == 1]  # 第 9 列 status（1-based 第 9）
    if not enabled:
        raise RuntimeError('no enabled template rows')
    mulan, set41 = {}, []
    for r in enabled:
        (tid, ttype, tname, lic_ids, content,
         require_sw, is_system, priority, status, desc) = r[:10]
        if ttype == 'mulan':
            entry = {
                'template_id': tid,
                'pattern': sfs._tpl_pattern(content),
                'pattern_the': sfs._tpl_pattern(content.replace('copy of Mulan', 'copy of the Mulan')),
            }
            for lid in (lic_ids or []):
                mulan[lid] = entry
        elif ttype in ('builtin', 'custom'):
            set41.append((tid, sfs._tpl_pattern(content), priority or 100))
    set41.sort(key=lambda x: (x[2], x[0]))
    return {'mulan': mulan, 'set41': [(t, p) for t, p, _ in set41]}


# ---------------- 全量扫描 ----------------

rows = parse_seed_sql(SQL)
tpl_config = build_tpl_config(rows)
print(f"templates: mulan={sorted(tpl_config['mulan'])} "
      f"set41={[t for t, _ in tpl_config['set41']]}", flush=True)

repos = sorted(d for d in os.listdir(REPOS_DIR) if os.path.isdir(os.path.join(REPOS_DIR, d)))
print(f"repos: {len(repos)}", flush=True)

# 多协议信号1 数据源：license 扫描表现成结果快照（2026-10-15 问题5）
LIC_SNAP = os.path.join(BASE, '_test_license_scan_snapshot.json')
lic_snap = {}
if os.path.exists(LIC_SNAP):
    with open(LIC_SNAP, encoding='utf-8') as f:
        lic_snap = {int(k): v for k, v in json.load(f).items()}
    print(f"license snapshot: {len(lic_snap)} repos", flush=True)
else:
    print("WARN: no license snapshot; multi-license signal-1 disabled", flush=True)

results = {}
errors = {}
for idx, repo in enumerate(repos, 1):
    rdir = os.path.join(REPOS_DIR, repo)
    try:
        rid = int(repo.split('_')[-1])
        tracked = sfs.list_tracked_files(rdir)
        score, is_na, detail = sfs.scan_copyright(
            rdir, tracked, sfs.MAX_DETAIL_PATHS, tpl_config,
            lic_scan_entry=lic_snap.get(rid))
        results[repo] = {
            'score': score, 'is_na': is_na,
            'target': detail.get('target_file_count'),
            'matched': detail.get('matched_count'),
            'license_type': detail.get('license_type'),
            'mulan_license_id': detail.get('mulan_license_id'),
            'matched_template_id': detail.get('matched_template_id'),
            'excluded_test': detail.get('excluded_test_file_count'),
            'oversize': detail.get('oversize_file_count'),
            'reasons': detail.get('unmatched_reasons'),
            'score_mode': detail.get('score_mode'),
            'na_reason': detail.get('na_reason'),
            'licenses': detail.get('licenses'),
        }
        r = results[repo]
        extra = (f" na={r['na_reason']} licenses={r['licenses']}"
                 if is_na and r['na_reason'] else '')
        print(f"[{idx:3d}/{len(repos)}] {repo} lic={str(r['license_type']):8s} "
              f"tpl={str(r['matched_template_id']):18s} "
              f"{'NA' if is_na else str(score):>5s} "
              f"({r['matched']}/{r['target']}) mode={r['score_mode']}{extra} "
              f"reasons={r['reasons']}", flush=True)
    except Exception as e:
        errors[repo] = str(e)
        print(f"[{idx:3d}/{len(repos)}] {repo} ERROR: {e}", flush=True)

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump({'results': results, 'errors': errors}, f, ensure_ascii=False, indent=1)

# ---------------- 汇总分析 ----------------
print('\n' + '=' * 90)
print('=== 汇总 ===')
na = [r for r in results.values() if r['is_na']]
scored = {k: v for k, v in results.items() if not v['is_na']}
print(f"总数={len(results)}  NA={len(na)}  有分={len(scored)}  错误={len(errors)}")

branch_cnt = Counter(r['license_type'] for r in results.values())
print(f"分支分布: {dict(branch_cnt)}")

tpl_cnt = Counter(r['matched_template_id'] for r in scored.values())
print(f"命中模板分布: {dict(tpl_cnt)}")

full = [k for k, v in scored.items() if v['score'] == 10.0]
zero = [k for k, v in scored.items() if v['score'] == 0]
print(f"满分仓={len(full)}  0分仓={len(zero)}  中间={len(scored) - len(full) - len(zero)}")

reason_tot = Counter()
for v in scored.values():
    for rk, cnt in (v['reasons'] or {}).items():
        reason_tot[rk] += cnt
print(f"不合格原因总计: {dict(reason_tot.most_common())}")

# demo 5 仓对照
DEMO = {'repo_403209': ('demo: 254/395 → 6.43 (混合协议→4+1)'),
        'repo_401717': ('demo: 0/1041 → 0.00 (木兰)'),
        'repo_401712': ('demo: 2/12692 → 0.00 (木兰+LLVM)'),
        'repo_401492': ('demo: 72/72 → 10.00 (CANN)'),
        'repo_402093': ('demo: NA (无LICENSE)')}
print('\n=== demo 5 仓生产版对照 ===')
for k, note in DEMO.items():
    v = results.get(k)
    if not v:
        print(f"{k}: 不在本地 ({note})"); continue
    print(f"{k}: {'NA' if v['is_na'] else v['score']} "
          f"({v['matched']}/{v['target']}) lic={v['license_type']} "
          f"tpl={v['matched_template_id']}  [{note}]")

print(f"\nsaved -> {OUT}")
