# -*- coding: utf-8 -*-
"""临时 E2E：合成 LICENSE（改写一句 + 删一段 + 多加一句）真跑 scancode，
验证 _build_template_diff 的 mod/del/add 行语义。测完即删。"""
import importlib.util
import json
import os
import shutil

BASE = r"c:\Users\caoxiaolin\Desktop\openlibing\docs\0912"
spec = importlib.util.spec_from_file_location('sls', BASE + r'\security_license_scan.py')
sls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sls)

# ---- 构造合成仓：MIT 官方模板正文（剥 YAML front matter）为基础做三处差异 ----
tpl_text = sls._find_template_text('mit')
assert tpl_text and not tpl_text.startswith('---'), '官方模板正文剥离 front matter 失败'
tpl_lines = tpl_text.splitlines()
print('官方模板行数:', len(tpl_lines))

lines = list(tpl_lines)
# 差异1（mod）：改写一句 —— 把第一段里的 "Permission is hereby granted, free of charge" 改措辞
for i, ln in enumerate(lines):
    if 'Permission is hereby granted, free of charge' in ln:
        lines[i] = ln.replace('free of charge', 'without any fee')
        mod_idx = i
        break
# 差异2（del）：删除 "The above copyright notice..." 一整段（含其后的空行，若相邻）
del_start = None
for i, ln in enumerate(lines):
    if 'The above copyright notice' in ln:
        del_start = i
        break
del_end = del_start + 1 if del_start + 1 < len(lines) and lines[del_start + 1].strip() == '' else del_start
del_block = lines[del_start:del_end + 1]
lines = lines[:del_start] + lines[del_end + 1:]
# 差异3（add）：末尾多加一行自定义条款
lines.append('This license is granted by Acme Corp only.')

repo = os.path.join(BASE, '_test_repos', 'repo_diff_test')
shutil.rmtree(repo, ignore_errors=True)
os.makedirs(repo)
with open(os.path.join(repo, 'LICENSE'), 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('\n'.join(lines) + '\n')

cache = os.path.join(BASE, '_test_p2_cache')
os.makedirs(cache, exist_ok=True)
spdx_map = sls.load_spdx_map(None, cache)
score, row = sls._scan_license_file(repo, 'LICENSE', cache, spdx_map, 'scancode_diff_e2e.json')

diff = (row.get('detail') or {}).get('template_diff')
out = {
    'score': score,
    'spdx': row.get('spdx'),
    'template_match': row.get('template_match'),
    'template_diff_meta': None if diff is None else {
        'tpl_id': diff.get('tpl_id'),
        'coverage': diff.get('coverage'),
        'match_lines': diff.get('match_lines'),
        'truncated': diff.get('truncated'),
        'row_count': len(diff.get('rows') or []),
    },
    'rows': None if diff is None else diff.get('rows'),
}
print(json.dumps(out, ensure_ascii=False, indent=2))

# ---- 断言 ----
assert diff is not None, 'template_diff 未生成'
rows = diff['rows']
statuses = [r['status'] for r in rows]
assert diff['tpl_id'] == 'mit', f"tpl_id 异常: {diff['tpl_id']}"
assert 'mod' in statuses, '改写句未被识别为 mod 行'
assert 'del' in statuses, '删除段未被识别为 del 行'
assert 'add' in statuses, '多出句未被识别为 add 行'
mod_rows = [r for r in rows if r['status'] == 'mod']
del_rows = [r for r in rows if r['status'] == 'del']
add_rows = [r for r in rows if r['status'] == 'add']
assert any('without any fee' in (r['file'] or '') for r in mod_rows), 'mod 行文件侧未含改写文案'
assert any(r['line'] == '—' for r in del_rows), 'del 行行号应为 —'
assert any('Acme Corp' in (r['file'] or '') for r in add_rows), 'add 行未含多出句'
assert add_rows[0]['line'] != '—', 'add 行应有文件内行号'
assert any(r['status'] == 'same' for r in rows), '应有 same 上下文行'
print('\n[E2E PASS] mod/del/add/same 行语义与行号规则全部符合预期')
