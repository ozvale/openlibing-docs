# -*- coding: utf-8 -*-
"""校验 FUZZING 明细配置三处同步的字节级一致性（classpath / 交付UPDATE / init.sql）"""
import json
import re

BASE = r'c:\Users\caoxiaolin\Desktop\openlibing'

with open(BASE + r'\openlibing-ops\src\main\resources\security\detail-conf\FUZZING.json', encoding='utf-8') as f:
    a = json.dumps(json.load(f), ensure_ascii=False, separators=(',', ':'))

with open(BASE + r'\docs\0912\detail-conf-gcheck-update.sql', encoding='utf-8') as f:
    upd = f.read()
pos = upd.index("WHERE metric_code = 'FUZZING'")
seg = upd[:pos]
ms = re.findall(r"SET conf_json = '(.*?)',\n", seg, re.S)
c2 = ms[-1]  # 取 FUZZING WHERE 之前最后一条 UPDATE（即 FUZZING 段）

with open(BASE + r'\openlibing-docs\spec\openlibing-ops\task_design\2026-09-23_安全合规评分看板接口\detail-conf-init.sql', encoding='utf-8') as f:
    ini = f.read()
i = ini.index("VALUES ('FUZZING',")
m2 = re.search(r"VALUES \('FUZZING',\n'(.*?)',\n1", ini[i:], re.S)
c3 = m2.group(1)

print('classpath == update.sql :', a == c2)
print('classpath == init.sql   :', a == c3)
conf = json.loads(a)
print('when                    :', conf['failItems'][0]['when'])
print('isNone in summary       :', any(s.get('key') == 'isNone' for s in conf['summary']))
