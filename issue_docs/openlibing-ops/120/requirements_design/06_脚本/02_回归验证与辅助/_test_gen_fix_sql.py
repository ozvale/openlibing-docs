# -*- coding: utf-8 -*-
"""临时生成（测完即删）：从 docs 仓 init.sql 提取 6 个受损指标的 conf，
unescape \\u003c/3e/26 后以标准 INSERT 模板重新拼装修复 SQL。"""
import io
import json
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SRC = r'c:\Users\caoxiaolin\Desktop\openlibing\openlibing-docs\spec\openlibing-ops\task_design\2026-09-23_安全合规评分看板接口\detail-conf-init.sql'
OUT = r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\2026-09-23_安全合规评分看板接口模版SQL\detail-conf-fix-escape.sql'

t = open(SRC, encoding='utf-8').read()

# 每条 INSERT：INSERT INTO ... VALUES ('CODE', '<json-literal>', 1, ... );
pat = re.compile(
    r"INSERT INTO dm_rd_efc_security_metric_detail_conf[^;]*?VALUES\s*\('([A-Z_]+)',\s*\n?'(.*?)',\s*\n?\s*1,",
    re.S)
corrupted = {'COPYRIGHT', 'TOKEN_PERM', 'SECURITY_POLICY', 'VULNS', 'MAINTAINED', 'CONTRIBUTORS'}
found = {}
for m in pat.finditer(t):
    mc, lit = m.group(1), m.group(2)
    if mc not in corrupted:
        continue
    fixed = re.sub(r'\\u00(3c|3e|26)', lambda x: {'3c': '<', '3e': '>', '26': '&'}[x.group(1)], lit)
    # 校验：SQL '' 还原 → json.loads
    json.loads(fixed.replace("''", "'"))
    found[mc] = fixed
    print(f'{mc}: 字面量 {len(fixed)} 字符，JSON 合法，残留 u00 转义: {fixed.count(chr(92) + "u00")}')

assert set(found) == corrupted, f'缺失: {corrupted - set(found)}'

hdr = """-- =====================================================================
-- 修复：detail conf 被转义吃字损坏（2026-10-16 定位）
-- 现象：10-14 16:11 批次写入的 6 个指标 conf 中 < > & 被存成裸 u003c/u003e/u0026
--       （JSON 合法转义 \\u003c 经 MySQL 协议执行时反斜杠被吃，落库成字面 "u003c"），
--       引擎 when 条件解析不到比较运算符，按不满足处理，failItems 卡片全部失效，
--       前端显示"全部满足、无扣分项"与实际扣分矛盾（msmodelslim 0.2 分却显示满分）。
-- 受影响：COPYRIGHT(matched_count<target_file_count)、MAINTAINED(total<@p.threshold)、
--         CONTRIBUTORS(n<@p.minOrgs)、TOKEN_PERM(文案 >)、VULNS(4 个 when >=1)、
--         SECURITY_POLICY(3 个 when &&)
-- 修复：\\uXXXX 还原为真实字符（JSON 合法且 SQL 字符串无需转义），
--       重新 INSERT 覆盖（UNIQUE KEY metric_code 后写覆盖）。
--       执行后最多 5 分钟（conf 缓存 TTL）自动生效，无需发版重启。
-- 来源：openlibing-docs detail-conf-init.sql 对应段 unescape，已逐条校验 JSON 合法。
-- 生成：ai-assisted 2026-10-16
-- =====================================================================

"""
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(hdr)
    for mc, lit in found.items():
        f.write(f"INSERT INTO dm_rd_efc_security_metric_detail_conf "
                f"(metric_code, conf_json, enabled, updated_by, updated_at)\n"
                f"VALUES ('{mc}',\n'{lit}',\n1, 'ai-assisted', NOW());\n\n")
print('已生成:', OUT)
