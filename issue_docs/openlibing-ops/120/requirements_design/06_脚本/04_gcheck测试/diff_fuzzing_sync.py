# -*- coding: utf-8 -*-
"""定位 update.sql 与 classpath 压缩 JSON 的差异点"""
import json
import difflib

BASE = r'c:\Users\caoxiaolin\Desktop\openlibing'

with open(BASE + r'\openlibing-ops\src\main\resources\security\detail-conf\FUZZING.json', encoding='utf-8') as f:
    a = json.dumps(json.load(f), ensure_ascii=False, separators=(',', ':'))

with open(BASE + r'\docs\0912\detail-conf-gcheck-update.sql', encoding='utf-8') as f:
    upd = f.read()
pos = upd.index("WHERE metric_code = 'FUZZING'")
import re
ms = re.findall(r"SET conf_json = '(.*?)',\n", upd[:pos], re.S)
c2 = ms[-1]  # 取 FUZZING WHERE 之前最后一条 UPDATE（即 FUZZING 段）

for i, (x, y) in enumerate(zip(a, c2)):
    if x != y:
        print('first diff at char', i)
        print('classpath :', repr(a[max(0, i - 40):i + 60]))
        print('update.sql:', repr(c2[max(0, i - 40):i + 60]))
        break
else:
    print('prefix identical, len a =', len(a), 'len c2 =', len(c2))
    n = min(len(a), len(c2))
    print('classpath tail:', repr(a[n:n + 80]))
    print('update.sql tail:', repr(c2[n:n + 80]))
