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
UPDATE_SQLS = [
    BASE + r'\docs\0912\detail-conf-gcheck-update.sql',
    BASE + r'\openlibing-docs\issue_docs\openlibing-ops\120\requirements_design'
           r'\05_SQL\03_明细展示配置\detail-conf-gcheck-update.sql',
]
INIT_SQLS = [
    BASE + r'\openlibing-docs\spec\openlibing-ops\task_design'
           r'\2026-09-23_安全合规评分看板接口\detail-conf-init.sql',
    BASE + r'\openlibing-docs\issue_docs\openlibing-ops\120\requirements_design'
           r'\05_SQL\03_明细展示配置\detail-conf-init.sql',
]

# 修订记录（追加到 update.sql 头部注释，按时间顺序插在最后一条修订之后）
REVISION_NOTE = (
    '-- 修订：ai-assisted 2026-10-26 PINNED_DEP 未满足卡片只展示总体原因——\n'
    '--       failItems.reason 去掉括号内的 gcheck 判定依据文案（{reason}）。\n'
)
REVISION_GUARD = '2026-10-26 PINNED_DEP 未满足卡片只展示总体原因'

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
    for path in UPDATE_SQLS:
        up = read(path)
        m = PAT_UPDATE.search(up)
        if not m:
            print(f'!! update.sql 未找到 PINNED_DEP UPDATE 段: {path}')
            return 1
        up_new = PAT_UPDATE.sub(lambda _: m.group(1) + compact + m.group(3), up, count=1)
        # 头部补修订记录（已含则不重复加）；插在头部注释收尾分隔线之前（按时间顺序排最后）
        if REVISION_GUARD not in up_new:
            head_end = up_new.index('UPDATE openlibing')   # 第一条 UPDATE 之前
            sep = up_new.rindex('-- ====', 0, head_end)    # 头部注释收尾分隔线
            up_new = up_new[:sep] + REVISION_NOTE + up_new[sep:]
        write(path, up_new)
        print(f'update.sql PINNED_DEP 段已替换（{len(m.group(2))} -> {len(compact)} 字节）: {path}')

    # --- init.sql：替换 PINNED_DEP INSERT 的 conf_json（保留 definition 合并） ---
    for path in INIT_SQLS:
        ini = read(path)
        m2 = PAT_INIT.search(ini)
        if not m2:
            print(f'!! init.sql 未找到 PINNED_DEP INSERT 段: {path}')
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
        write(path, ini_new)
        print(f'init.sql PINNED_DEP 段已替换（{len(m2.group(2))} -> {len(compact_ini)} 字节）: {path}')

    # --- 校验 ---
    a = json.dumps(json.loads(read(CLASSPATH)), ensure_ascii=False, separators=(',', ':'))
    ok = True
    for path in UPDATE_SQLS:
        b = PAT_UPDATE.search(read(path)).group(2)
        same = a == b
        ok = ok and same
        print(f'classpath == {path} : {same}')
    for path in INIT_SQLS:
        c_raw = json.loads(PAT_INIT.search(read(path)).group(2))
        c_raw.pop('definition', None)
        c = json.dumps(c_raw, ensure_ascii=False, separators=(',', ':'))
        same = a == c
        ok = ok and same
        print(f'classpath == {path}(去 definition) : {same}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
