# -*- coding: utf-8 -*-
"""PINNED_DEP 明细配置移除「信号」展示项后，同步三处（classpath / update.sql / init.sql）。"""
import json
import re

BASE = r'c:\Users\caoxiaolin\Desktop\openlibing'
CONF = BASE + r'\openlibing-ops\src\main\resources\security\detail-conf\PINNED_DEP.json'
UPD = BASE + r'\docs\0912\detail-conf-gcheck-update.sql'
INI = BASE + r'\openlibing-docs\spec\openlibing-ops\task_design\2026-09-23_安全合规评分看板接口\detail-conf-init.sql'

with open(CONF, encoding='utf-8') as f:
    conf = json.load(f)
compact = json.dumps(conf, ensure_ascii=False, separators=(',', ':'))
assert 'signal' not in compact and '信号' not in compact, 'conf 仍残留 signal/信号'

# --- update.sql：替换 PINNED_DEP 段（第一条 UPDATE） ---
with open(UPD, encoding='utf-8') as f:
    upd = f.read()
pos = upd.index("WHERE metric_code = 'PINNED_DEP'")
head, tail = upd[:pos], upd[pos:]
new_head = re.sub(r"SET conf_json = '.*?',\n", "SET conf_json = '" + compact + "',\n",
                  head, count=1, flags=re.S)
assert new_head != head, 'update.sql 未发生替换'
with open(UPD, 'w', encoding='utf-8', newline='') as f:
    f.write(new_head + tail)

# --- init.sql：替换 PINNED_DEP INSERT 段 ---
with open(INI, encoding='utf-8') as f:
    ini = f.read()
i = ini.index("VALUES ('PINNED_DEP',")
new_ini = re.sub(r"VALUES \('PINNED_DEP',\n'.*?',\n", "VALUES ('PINNED_DEP',\n'" + compact + "',\n",
                 ini, count=1, flags=re.S)
assert new_ini != ini, 'init.sql 未发生替换'
with open(INI, 'w', encoding='utf-8', newline='') as f:
    f.write(new_ini)

# --- 回读校验 ---
with open(UPD, encoding='utf-8') as f:
    upd2 = f.read()
pos2 = upd2.index("WHERE metric_code = 'PINNED_DEP'")
c2 = re.findall(r"SET conf_json = '(.*?)',\n", upd2[:pos2], re.S)[-1]
with open(INI, encoding='utf-8') as f:
    ini2 = f.read()
i2 = ini2.index("VALUES ('PINNED_DEP',")
c3 = re.search(r"VALUES \('PINNED_DEP',\n'(.*?)',\n", ini2[i2:], re.S).group(1)
print('classpath == update.sql :', compact == c2)
print('classpath == init.sql   :', compact == c3)
