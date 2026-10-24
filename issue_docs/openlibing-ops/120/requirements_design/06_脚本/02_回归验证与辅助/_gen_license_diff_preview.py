#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 MCP 查询结果文件解析 10 个典型仓的 template_diff，生成对比效果 HTML（还原 beta 前端渲染契约）。"""
import json
import os
import re
import html

BASE = r'C:\Users\caoxiaolin\AppData\Local\Temp\2\trae\toolcall-output'
FILES = [
    # 批次 2026-10-24 11:22:49（最终口径：比对剔除全部空白）
    'eeba1894-35c2-480b-a561-912ecb16e441.txt',   # 400030, 401430, 402226
    'ea484d64-4dc3-49f1-b141-48c25c68412c.txt',   # 401797, 403132, 403420, 404675
    # 该 3 仓 diff 与旧批次完全一致（本就没有空白噪音），沿用旧文件
    '1120eab9-35c3-47fe-bd8d-a566bcdf0dec.txt',   # 401148, 401515, 401546, (404675 忽略)
]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   '_preview_license_diff_ui_10repos.html')

repos = []
for fn in FILES:
    with open(os.path.join(BASE, fn), encoding='utf-8') as fh:
        raw = fh.read()
    m = re.search(r'\[\{"type":"text","text":"(.*)"\}\]', raw, re.S)
    if not m:
        raise SystemExit(f'cannot locate payload in {fn}')
    payload = json.loads('"' + m.group(1) + '"')      # 去掉外层 JS 字符串转义
    obj = json.loads(payload)
    for row in obj['data']:
        if row['repo_id'] in {r['repo_id'] for r in repos}:
            continue                      # 去重：404675 两批都有，取新批次
        row['td'] = json.loads(row['td']) if isinstance(row['td'], str) else row['td']
        repos.append(row)

repos.sort(key=lambda r: r['repo_id'])
print(f'parsed {len(repos)} repos:', [r['repo_id'] for r in repos])

# ---------- 行渲染（与 beta 前端约定一致：wrap 列 pre-wrap，cell.level 决定行背景） ----------
STATUS_META = {
    'del':  ('bg-red-50',    'text-red-700',  '模板有 / 文件缺'),
    'add':  ('bg-amber-50',  'text-amber-700', '文件多出'),
    'mod':  ('bg-amber-50',  'text-amber-700', '两边不一致'),
    'same': ('',             '',               '一致（上下文）'),
    'omit': ('',             '',               '折叠占位'),
}

def esc(s):
    return html.escape(s or '', quote=False)

def render_row(r):
    st = r.get('status', '')
    bg, fg, label = STATUS_META.get(st, ('', '', st))
    if st == 'omit':
        return (f'  <tr class="omit-row"><td colspan="3">{esc(r.get("tpl",""))}</td></tr>\n')
    # cell level：del 行 file 列 na；tpl 列 del=error；file 列 add/mod=warning
    line_cell = esc(r.get('line', '—'))
    tpl_txt = esc(r.get('tpl', ''))
    file_txt = esc(r.get('file', ''))
    row_cls = f' class="diff-row {bg} {fg}"' if bg else ' class="diff-row"'
    return (f'  <tr{row_cls}>'
            f'<td class="line-col">{line_cell}</td>'
            f'<td class="wrap-col">{tpl_txt}</td>'
            f'<td class="wrap-col">{file_txt}</td></tr>\n')

def render_repo(r):
    td = r.get('td') or {}
    rows = td.get('rows') or []
    owner_repo = r['repo_url'].rstrip('/').split('/')[-1].removesuffix('.git')
    owner = r['repo_url'].split('/gitcode.com/')[1].split('/')[0]
    trs = ''.join(render_row(x) for x in rows)
    rule_url = td.get('rule_url', '')
    stats = {}
    for x in rows:
        stats[x['status']] = stats.get(x['status'], 0) + 1
    stat_str = '　'.join(f'{k}:{v}' for k, v in sorted(stats.items()))
    return f'''
<section class="repo-card">
  <h2><a href="{esc(r["repo_url"])}">{esc(owner_repo)}</a>
      <span class="meta">repo_id {r["repo_id"]}　owner {esc(owner)}　SPDX {esc(r["spdx"])}　score {r["score"]}</span></h2>
  <p class="meta">模板 <b>{esc(td.get("tpl_id",""))}</b>　覆盖率 {esc(str(td.get("coverage","")))}%　命中行 {esc(td.get("match_lines",""))}
      ｜行统计 {esc(stat_str)}{esc("　（已截断）") if td.get("truncated") else ""}
      ｜<a href="{esc(rule_url)}">官方模板</a></p>
  <table class="diff-table">
    <thead><tr><th class="line-col">行号</th><th class="wrap-col">官方模板要求</th><th class="wrap-col">你的 LICENSE 实际内容</th></tr></thead>
    <tbody>
{trs}    </tbody>
  </table>
</section>'''

legend = ''.join(
    f'<span class="lg"><i class="sw {cls}"></i>{desc}</span>'
    for cls, desc in [('bg-red-50', 'del：模板有 / 你的文件缺失'),
                      ('bg-amber-50', 'mod：内容不一致 / add：文件多出'),
                      ('', 'same：一致（上下文）')])

page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>LICENSE 模板差异对照 · 10 个典型仓效果预览</title>
<style>
  body {{ font-family: "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px; color: #1f2329; background: #f5f6f7; }}
  h1 {{ font-size: 20px; }}
  .note {{ color: #646a73; font-size: 13px; margin: 8px 0 4px; }}
  .lg {{ margin-right: 18px; font-size: 13px; color: #4e5460; }}
  .sw {{ display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: -2px; margin-right: 4px; border: 1px solid #dee0e3; }}
  .repo-card {{ background: #fff; border: 1px solid #dee0e3; border-radius: 8px; padding: 16px 20px; margin: 18px 0; }}
  .repo-card h2 {{ font-size: 16px; margin: 0 0 6px; }}
  .repo-card h2 a {{ color: #1664ff; text-decoration: none; }}
  .meta {{ color: #646a73; font-weight: normal; font-size: 13px; }}
  .meta a {{ color: #1664ff; }}
  table.diff-table {{ border-collapse: collapse; width: 100%; font-size: 13px; table-layout: fixed; }}
  .diff-table th, .diff-table td {{ border: 1px solid #dee0e3; padding: 4px 8px; vertical-align: top; }}
  .diff-table th {{ background: #f2f3f5; text-align: left; font-weight: 500; }}
  .line-col {{ width: 64px; text-align: center; color: #646a73; }}
  .wrap-col {{ width: auto; white-space: pre-wrap; word-break: break-all; }}   /* 前端 type=wrap 契约 */
  .diff-row.bg-red-50 {{ background: #fef2f2; }}   .diff-row.bg-red-50 .wrap-col {{ color: #b91c1c; }}
  .diff-row.bg-amber-50 {{ background: #fffbeb; }} .diff-row.bg-amber-50 .wrap-col {{ color: #b45309; }}
  .omit-row td {{ text-align: center; color: #8f959e; font-style: italic; background: #fafafa; }}
</style>
</head>
<body>
<h1>LICENSE 指标 · 模板差异对照（并排 diff）— 10 个典型仓数据还原</h1>
<p class="note">数据来源：dwi_rd_efc_security_license_scan 批次 2026-10-24 11:22:49（detail.template_diff，最终口径：比对剔除全部空白）。页面按 beta 前端渲染契约还原：wrap 列 pre-wrap + 按行 status 染色。</p>
<p class="note">行图例：{legend}</p>
{''.join(render_repo(r) for r in repos)}
</body>
</html>'''

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write(page)
print('written:', OUT)
