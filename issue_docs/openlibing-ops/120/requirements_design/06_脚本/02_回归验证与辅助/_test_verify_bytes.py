# -*- coding: utf-8 -*-
"""临时验证（测完即删）：修复 SQL 各指标字面量字节数 + 损坏差值（供与 DB length 对账）。"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SRC = r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\2026-09-23_安全合规评分看板接口模版SQL\detail-conf-fix-escape.sql'
t = open(SRC, encoding='utf-8').read()
# 损坏计数（DB 侧每处 \uXXXX→uXXXX 多 4 字节：源文件 \u003c 6 字符修复后 < 1 字符，DB 裸 u003c 5 字符）
delta = {'COPYRIGHT': 4, 'TOKEN_PERM': 16, 'SECURITY_POLICY': 24, 'VULNS': 16, 'MAINTAINED': 4, 'CONTRIBUTORS': 4}
for m in re.finditer(r"VALUES \('([A-Z_]+)',\n'(.*?)',\n1, 'ai-assisted', NOW\(\)\);", t, re.S):
    mc, lit = m.group(1), m.group(2)
    print(f"{mc}: 修复版 conf 字节数 = {len(lit.encode('utf-8'))}, +损坏差值 {delta[mc]} "
          f"=> 预期 DB length = {len(lit.encode('utf-8')) + delta[mc]}")
