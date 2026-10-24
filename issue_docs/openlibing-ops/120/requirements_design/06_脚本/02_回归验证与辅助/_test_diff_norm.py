#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 2026-10-24 空白归一化改动：纯空格差异不再产生 mod/del+add 噪音，真字符差异保留。"""
import sys, os, re, importlib.util

spec = importlib.util.spec_from_file_location(
    "sls", os.path.join(os.path.dirname(__file__), "security_license_scan.py"))
sls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sls)

TPL_KEY = 'mulanpsl-2.0'
tpl_text = sls._find_template_text(TPL_KEY)
assert tpl_text, 'licensedcode 模板不可读'
tpl_lines = [ln.rstrip() for ln in tpl_text.splitlines()]
nonblank = [ln for ln in tpl_lines if ln.strip()]
print(f"模板 mulanpsl-2.0 共 {len(tpl_lines)} 行（非空 {len(nonblank)}）")


def make_diff(license_text):
    bm = {'license_expression': TPL_KEY, 'match_coverage': 99.0,
          'start_line': 1, 'end_line': len(license_text.splitlines()),
          'rule_identifier': 'x', 'rule_url': 'y'}
    return sls._build_template_diff(bm, license_text)


def stats(rows):
    from collections import Counter
    return dict(Counter(r['status'] for r in rows))


# ---------- 场景1：纯空白差异（模拟 repo 400030 的噪音来源） ----------
spaced = []
for ln in tpl_lines:
    s = re.sub(r'^(1\.|2\.|3\.|4\.|5\.|0\.)   +', r'\1 ', ln)   # 编号后3空格 -> 1空格
    if s.strip():
        s = '  ' + s                                            # 行首缩进
    spaced.append(s)
license_spaced = '\n'.join(spaced)

d1 = make_diff(license_spaced)
st1 = stats(d1['rows']) if d1 else {}
print(f"场景1（纯空格差异）: rows={len(d1['rows']) if d1 else 0} status={st1} truncated={d1['truncated'] if d1 else '-'}")
bad = [r for r in (d1['rows'] or []) if r['status'] in ('mod', 'del', 'add')]
print(f"  噪音行数（mod/del/add）= {len(bad)}（预期 0）")
for r in bad[:3]:
    print(f"    意外: {r['status']} tpl={r['tpl'][:40]!r} file={r['file'][:40]!r}")

# ---------- 场景2：真实字符差异（全角->半角标点 + 删一段 + 加一段） ----------
changed = list(tpl_lines)
for i, ln in enumerate(changed):
    if '木兰宽松许可证, 第2版' in ln or '，' in ln:
        changed[i] = ln.replace('，', ',')                      # 全角逗号 -> 半角
changed.append('')
changed.append('本许可证由 Acme Corp 附加说明：仅限内部使用。')     # 文件多出
license_mod = '\n'.join(changed)

d2 = make_diff(license_mod)
st2 = stats(d2['rows']) if d2 else {}
print(f"场景2（真字符差异）: rows={len(d2['rows']) if d2 else 0} status={st2} truncated={d2['truncated'] if d2 else '-'}")
mods = [r for r in (d2['rows'] or []) if r['status'] == 'mod']
print(f"  mod 行数 = {len(mods)}（预期 >0，即标点差异被照出）")
if mods:
    print(f"    示例: tpl={mods[0]['tpl'][:30]!r} file={mods[0]['file'][:30]!r} line={mods[0]['line']}")
adds = [r for r in (d2['rows'] or []) if r['status'] == 'add']
print(f"  add 行数 = {len(adds)}（预期 >=1，附加条款被照出；若截断则末尾应有占位行）")
tail = d2['rows'][-1] if d2['rows'] else None
print(f"  末行: status={tail['status']} tpl={tail['tpl'][:40]!r}")
if d2['truncated']:
    assert tail['status'] == 'omit' and '仅展示前' in (tail['tpl'] or ''), '截断占位行缺失'
    print("  截断占位行 PASS")
dels = [r for r in (d2['rows'] or []) if r['status'] == 'del']
print(f"  del 行数 = {len(dels)}（标点差异若逐行配对则 del 少；>0 也属正常）")

# ---------- 场景3：展示文本保留原文（缩进不丢） ----------
d3 = make_diff(license_spaced)
sample = next((r for r in d3['rows'] if r['status'] == 'same' and r['file'].startswith('  ')), None)
print(f"场景3（展示保留原文缩进）: {'PASS file 行保留行首缩进: ' + repr(sample['file'][:20]) if sample else 'SKIP（无匹配行）'}")

# ---------- 场景4：模板引号后有空格、文件没有（"有 vs 无"空白差异，二次复核噪音源） ----------
nospace = [ln.replace('” ', '”') for ln in tpl_lines]
license_quoted = '\n'.join(nospace)
d4 = make_diff(license_quoted)
st4 = stats(d4['rows']) if d4 else {}
print(f"场景4（引号空格有vs无）: rows={len(d4['rows']) if d4 else 0} status={st4}")
bad4 = [r for r in (d4['rows'] or []) if r['status'] in ('mod', 'del', 'add')]
print(f"  噪音行数（mod/del/add）= {len(bad4)}（预期 0）")
for r in bad4[:3]:
    print(f"    意外: {r['status']} tpl={r['tpl'][:40]!r} file={r['file'][:40]!r}")

print('DONE')
