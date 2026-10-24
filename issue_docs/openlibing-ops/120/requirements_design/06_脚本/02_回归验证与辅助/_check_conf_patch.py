# -*- coding: utf-8 -*-
"""校验 conf patch SQL 中的 conf_json 合法性。测完即删。"""
import json
import re

text = open(
    r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\2026-09-23_安全合规评分看板接口模版SQL'
    r'\detail-conf-patch-license-template-diff.sql', encoding='utf-8').read()
m = re.search(r"VALUES \('LICENSE',\s*'(.*?)',\s*1, 'ai-assisted'", text, re.S)
assert m, '未匹配到 INSERT VALUES'
conf = json.loads(m.group(1))
print('JSON OK; groups:', [g['key'] for g in conf['groups']])
print('diff group when:', conf['groups'][1]['when'])
print('diff columns:', [(c['key'], c.get('type')) for c in conf['groups'][1]['columns']])
print('summary last:', conf['summary'][-1])
# 与 classpath 内置 conf 语义一致性抽查：group keys / diff 列定义一致
classpath = json.load(open(
    r'c:\Users\caoxiaolin\Desktop\openlibing\openlibing-ops\src\main\resources\security\detail-conf\LICENSE.json',
    encoding='utf-8'))
assert [g['key'] for g in classpath['groups']] == [g['key'] for g in conf['groups']]
assert classpath['groups'][1]['columns'] == conf['groups'][1]['columns']
assert classpath['groups'][1]['rowLevel'] == conf['groups'][1]['rowLevel']
print('classpath 与 patch 一致')
