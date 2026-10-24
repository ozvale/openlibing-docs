# -*- coding: utf-8 -*-
"""临时扫描（测完即删）：模版SQL 目录 + docs0912 根目录所有 SQL 中 \\u003c/3e/26 的分布。"""
import glob
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
dirs = [
    r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\2026-09-23_安全合规评分看板接口模版SQL',
    r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912',
]
for d in dirs:
    for f in glob.glob(os.path.join(d, '*.sql')):
        t = open(f, encoding='utf-8').read()
        cnt = {p: len(re.findall(r'\\u00' + p, t)) for p in ('3c', '3e', '26')}
        if any(cnt.values()):
            print(os.path.basename(f), cnt)
# SECURITY_POLICY u0026 上下文（在能找到的文件里）
for d in dirs:
    for f in glob.glob(os.path.join(d, '*.sql')):
        t = open(f, encoding='utf-8').read()
        for m in re.finditer(r'\\u0026', t):
            s = max(0, m.start() - 70)
            print(f'[{os.path.basename(f)}] ...{t[s:m.end() + 70]}...')
