# -*- coding: utf-8 -*-
"""标点级粒度（2026-10-07）单测：真实文件 + 合成边界。
预期全部通过后，再跑 _test_copyright_v2_driver.py 做 113 仓回归。"""
import io, sys, os, re, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912'
spec = importlib.util.spec_from_file_location('sfs', os.path.join(BASE, 'security_file_scan.py'))
sfs = importlib.util.module_from_spec(spec); spec.loader.exec_module(sfs)

sys.path.insert(0, os.path.join(BASE, '参考', '版权合规明细示例'))
import scan_copyright_detail as D          # 复用其种子 SQL 解析（生产 load 逻辑复刻）
CFG, META = D.TPL_CONFIG, D.TPL_META

R = lambda *p: os.path.join(BASE, '_test_repos', *p)
results = []
def case(name, cond, detail=''):
    results.append((name, cond, detail))

# ---- 1. 归一化本身保留逗号/句号 ----
n = sfs._norm_text('Hello, World. Foo (c) Bar "quoted"')
case('norm 保留 ,. 剥其余标点', n == 'hello, world. foo c bar quoted', n)

# ---- 2. 真实文件：repo_401224 模态 CANN 头（带逗号 + 年份区间）----
c = sfs.read_head_text(R('repo_401224', 'op', 'kernel', 'binarywise_ops.cpp'))
if c is None:  # 路径可能不同，回退找第一个能读的
    pass
lines = None
if c:
    lines = sfs._clean_header_lines(sfs.extract_header(c, '.cpp'))
    ok, reason, tid, cl, banner = sfs.check_copyright_file(c, '.cpp', ('set41',), CFG)
    case('真实模态CANN头(逗号+2025-2026) 匹配 custom-cann',
          ok and tid == 'custom-cann', f'reason={reason}')

# 找不到该路径就用目录里任一模态文件
if not c or not results[-1][1]:
    found = False
    for dp, dns, fns in os.walk(R('repo_401224')):
        for fn in fns:
            if os.path.splitext(fn)[1].lower() != '.cpp': continue
            cc = sfs.read_head_text(os.path.join(dp, fn))
            if not cc: continue
            ok, reason, tid, cl, banner = sfs.check_copyright_file(cc, '.cpp', ('set41',), CFG)
            if ok and tid == 'custom-cann':
                found = True
                break
        if found: break
    case('repo_401224 存在模态匹配文件(兜底扫描)', found)

# ---- 3. 合成：无逗号变体必须挂（新粒度的核心语义）----
MODAL = '''Copyright (c) 2025-2026 Huawei Technologies Co., Ltd.
This program is free software, you can redistribute it and/or modify it under the terms and conditions of
CANN Open Software License Agreement Version 2.0 (the "License").
Please refer to the License for details. You may not use this file except in compliance with the License.
THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
See LICENSE in the root of the software repository for the full text of the License.'''
def wrap(text, marker):
    """合成用例必须裹注释符，否则 extract_header 判 no_header（真实文件头都在注释里）"""
    return '\n'.join(marker + ln if ln.strip() else '' for ln in text.split('\n'))

ok, reason, tid, cl, banner = sfs.check_copyright_file(wrap(MODAL, '// '), '.cpp', ('set41',), CFG)
case('模态全文(合成) 匹配', ok and tid == 'custom-cann', f'reason={reason}')

nocomma = MODAL.replace('MERCHANTABILITY, OR', 'MERCHANTABILITY OR')
ok, reason, tid, cl, banner = sfs.check_copyright_file(wrap(nocomma, '// '), '.cpp', ('set41',), CFG)
case('无逗号变体 挂为 template_mismatch', not ok and reason == 'template_mismatch', f'ok={ok} reason={reason}')

# ---- 4. 年份单值 / part of 前缀 / LLVM banner ----
single = MODAL.replace('(c) 2025-2026', '(c) 2025')
ok, reason, tid, cl, banner = sfs.check_copyright_file(wrap(single, '// '), '.cpp', ('set41',), CFG)
case('年份单值 2025 匹配', ok, f'reason={reason}')

with_prefix = 'This file is part of the ABC project.\n' + MODAL
ok, reason, tid, cl, banner = sfs.check_copyright_file(wrap(with_prefix, '// '), '.cpp', ('set41',), CFG)
case('part of 前缀行 仍匹配', ok, f'reason={reason}')

banner_hdr = MODAL.replace('See LICENSE in the root of the software repository for the full text of the License.',
                           'See LICENSE in the root of the software repository for the full text of the License.\nPart of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.')
ok, reason, tid, cl, banner = sfs.check_copyright_file(wrap(banner_hdr, '// '), '.cpp', ('set41',), CFG)
case('LLVM banner 附加行: 计入主原因 template_mismatch 且 banner=True',
     (not ok) and reason == 'template_mismatch' and banner, f'ok={ok} reason={reason} banner={banner}')

# ---- 5. 木兰分支（用 msinsight 真实文件）----
found = False
for dp, dns, fns in os.walk(R('repo_401717')):
    for fn in fns:
        if os.path.splitext(fn)[1].lower() != '.py': continue
        cc = sfs.read_head_text(os.path.join(dp, fn))
        if not cc: continue
        ok, reason, tid, cl, banner = sfs.check_copyright_file(cc, '.py', ('mulan', 'MulanPSL-2.0'), CFG)
        if ok:
            found = True
            break
    if found: break
case('msinsight 木兰仓存在匹配文件', found)

# ---- 6. mulan 官方模板（种子文本自身）合成检查 ----
mulan_tpl = next(m['content'] for m in META if m['template_id'] == 'mulan-psl-2.0')
rendered = mulan_tpl.replace('{year}', '2026').replace('{owner}', 'Huawei Technologies Co., Ltd.') \
                    .replace('{software_name}', 'MindStudio')
ok, reason, tid, cl, banner = sfs.check_copyright_file(wrap(rendered, '# '), '.py', ('mulan', 'MulanPSL-2.0'), CFG)
case('木兰官方模板渲染后 自匹配', ok, f'reason={reason}')

# ---- 7. 装饰线 + 注释风格（//）免疫 ----
decorated = '/*\n * ' + MODAL.replace('\n', '\n * ') + '\n */'
ok, reason, tid, cl, banner = sfs.check_copyright_file(decorated, '.c', ('set41',), CFG)
case('块注释包裹 + 装饰行 匹配', ok, f'reason={reason}')

slash = '// ' + MODAL.replace('\n', '\n// ')
ok, reason, tid, cl, banner = sfs.check_copyright_file(slash, '.go', ('set41',), CFG)
case('// 行注释 匹配', ok, f'reason={reason}')

fails = [r for r in results if not r[1]]
for name, cond, detail in results:
    print(('PASS' if cond else 'FAIL'), '|', name, ('| ' + detail if detail and not cond else ''))
print(f'\n{len(results) - len(fails)}/{len(results)} 通过')
sys.exit(1 if fails else 0)
