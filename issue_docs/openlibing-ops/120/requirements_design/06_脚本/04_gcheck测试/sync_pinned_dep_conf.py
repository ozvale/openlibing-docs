# -*- coding: utf-8 -*-
"""同步 PINNED_DEP conf_json 三处（classpath / update.sql / init.sql）并校验。

用法：python sync_pinned_dep_conf.py
- 以 classpath PINNED_DEP.json 为基准（压缩为单行）
- 替换 update.sql 中 PINNED_DEP UPDATE 的 conf_json 行（与 classpath 字节一致）
- 替换 init.sql 中 PINNED_DEP INSERT 的 conf_json 行（保留 init.sql 原有的
  definition 块合并进新配置——classpath/生产库均无 definition，属既有分歧，
  此处不扩散、不丢失）
- 校验：update.sql 段 == classpath 压缩；init.sql 段去掉 definition 后 == classpath
"""
import json
import re
import sys

BASE = r'c:\Users\caoxiaolin\Desktop\openlibing'
CLASSPATH = BASE + r'\openlibing-ops\src\main\resources\security\detail-conf\PINNED_DEP.json'
UPDATE_SQL = BASE + r'\docs\0912\detail-conf-gcheck-update.sql'
INIT_SQL = (BASE + r'\openlibing-docs\spec\openlibing-ops\task_design'
            r'\2026-09-23_安全合规评分看板接口\detail-conf-init.sql')

# 修订记录（追加到 update.sql 头部注释，按时间顺序插在最后一条修订之后）
REVISION_NOTE = (
    '-- 修订：ai-assisted 2026-10-16 PINNED_DEP 移除「依赖明细」表格分组——全量明细已迁移至\n'
    '--       独立分页接口 /security/pinned-dep-list（表 dwi_rd_efc_security_pinned_dep_detail），\n'
    '--       metric-detail 响应保留判据汇总与不满足项卡片。\n')

# update.sql 实际结构：
# UPDATE openlibing.dm_rd_efc_security_metric_detail_conf
# SET conf_json = '{json}',
#     updated_by = 'ai-assisted',
#     updated_at = NOW()
# WHERE metric_code = 'PINNED_DEP';
PAT_UPDATE = re.compile(
    r"(UPDATE openlibing\.dm_rd_efc_security_metric_detail_conf\s*\n"
    r"SET conf_json = ')"
    r"(.*?)"
    r"(',\s*\n\s*updated_by = 'ai-assisted',\s*\n\s*updated_at = NOW\(\)\s*\n"
    r"WHERE metric_code = 'PINNED_DEP';)", re.S)

# init.sql 实际结构：
# VALUES ('PINNED_DEP',
# '{json}',
# 1, 'ai-assisted', NOW());
PAT_INIT = re.compile(
    r"(VALUES \('PINNED_DEP',\n')"
    r"(.*?)"
    r"(',\n1, 'ai-assisted', NOW\(\)\);)", re.S)


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def write(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def main():
    conf = json.loads(read(CLASSPATH))
    compact = json.dumps(conf, ensure_ascii=False, separators=(',', ':'))
    print(f'classpath 压缩后 {len(compact)} 字节')

    # --- update.sql：替换 PINNED_DEP UPDATE 的 conf_json ---
    up = read(UPDATE_SQL)
    m = PAT_UPDATE.search(up)
    if not m:
        print('!! update.sql 未找到 PINNED_DEP UPDATE 段')
        return 1
    up_new = PAT_UPDATE.sub(lambda _: m.group(1) + compact + m.group(3), up, count=1)
    # 头部补修订记录（已含则不重复加）；插在头部注释收尾分隔线之前（按时间顺序排最后）
    if '2026-10-16 PINNED_DEP 移除「依赖明细」' not in up_new:
        head_end = up_new.index('UPDATE openlibing')   # 第一条 UPDATE 之前
        sep = up_new.rindex('-- ====', 0, head_end)    # 头部注释收尾分隔线
        up_new = up_new[:sep] + REVISION_NOTE + up_new[sep:]
    write(UPDATE_SQL, up_new)
    print(f'update.sql PINNED_DEP 段已替换（{len(m.group(2))} -> {len(compact)} 字节）')

    # --- init.sql：替换 PINNED_DEP INSERT 的 conf_json（保留 definition 合并） ---
    ini = read(INIT_SQL)
    m2 = PAT_INIT.search(ini)
    if not m2:
        print('!! init.sql 未找到 PINNED_DEP INSERT 段')
        return 1
    old_ini_conf = json.loads(m2.group(2))
    definition = old_ini_conf.get('definition')
    if definition is not None and 'definition' not in conf:
        merged = {}
        for k, v in conf.items():
            merged[k] = v
            if k == 'rule':
                merged['definition'] = definition
        print(f'init.sql 保留原有 definition 块（{len(json.dumps(definition, ensure_ascii=False))} 字节）')
    else:
        merged = conf
    compact_ini = json.dumps(merged, ensure_ascii=False, separators=(',', ':'))
    ini_new = PAT_INIT.sub(lambda _: m2.group(1) + compact_ini + m2.group(3), ini, count=1)
    write(INIT_SQL, ini_new)
    print(f'init.sql PINNED_DEP 段已替换（{len(m2.group(2))} -> {len(compact_ini)} 字节）')

    # --- 校验 ---
    a = json.dumps(json.loads(read(CLASSPATH)), ensure_ascii=False, separators=(',', ':'))
    b = PAT_UPDATE.search(read(UPDATE_SQL)).group(2)
    c_raw = json.loads(PAT_INIT.search(read(INIT_SQL)).group(2))
    c_raw.pop('definition', None)
    c = json.dumps(c_raw, ensure_ascii=False, separators=(',', ':'))
    ok_u = a == b
    ok_i = a == c
    print('classpath == update.sql               :', ok_u)
    print('classpath == init.sql(去 definition)  :', ok_i)
    return 0 if (ok_u and ok_i) else 1


if __name__ == '__main__':
    sys.exit(main())
