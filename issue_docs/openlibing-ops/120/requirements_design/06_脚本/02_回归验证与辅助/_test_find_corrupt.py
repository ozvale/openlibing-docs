# -*- coding: utf-8 -*-
"""临时分析（测完即删）：v2 SQL 文件中所有 \u003c/\u003e/\u0026 损坏点及其所属指标。"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
p = r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\2026-09-23_安全合规评分看板接口模版SQL\detail-conf-init-v2.sql'
t = open(p, encoding='utf-8').read()

# 每个 INSERT 段的 metric_code 起始位置
spans = [(m.start(), m.group(1)) for m in re.finditer(r"VALUES\s*\('([A-Z_]+)'", t)]
spans.append((len(t), 'END'))


def owner(pos):
    for i in range(len(spans) - 1):
        if spans[i][0] <= pos < spans[i + 1][0]:
            return spans[i][1]
    return '?'


print('=== 所有 backslash-uXXXX 损坏点 ===')
for m in re.finditer(r'\\u003[ce6]', t):
    s = max(0, m.start() - 55)
    print(f'[{owner(m.start())}] ...{t[s:m.end() + 55]}...')
    print('---')
