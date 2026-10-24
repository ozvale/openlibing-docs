# -*- coding: utf-8 -*-
"""score_pinned_deps 全量明细行（_dep_rows）产出/剥离回归测试。"""
import importlib.util
import json
import sys

SCRIPT = r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\security_gcheck_scan.py'
spec = importlib.util.spec_from_file_location('gscan', SCRIPT)
gscan = importlib.util.module_from_spec(spec)
sys.modules['gscan'] = gscan
spec.loader.exec_module(gscan)

check = {
    'status': 'finished',
    'summary': {'compliant': 2, 'nonCompliant': 2},
    'items': [
        {'id': 'containerImage', 'path': 'a.yml', 'lineStart': 3, 'snippet': 'image: ubuntu',
         'verdict': 'compliant', 'signal': 'digestPinned', 'detail': 'ok'},
        {'id': 'pipCommand', 'path': 'b.sh', 'lineStart': 7, 'snippet': 'pip3 install x',
         'verdict': 'nonCompliant', 'signal': None, 'detail': 'use --require-hashes'},
        {'id': None, 'path': 'c', 'lineStart': None, 'snippet': None,
         'verdict': 'notSupported', 'signal': None, 'detail': None},
        {'id': 'npmCommand', 'path': 'd.yaml', 'lineStart': 1, 'snippet': 'npm install',
         'verdict': 'compliant', 'signal': None, 'detail': 'ok'},
    ],
}
score, is_na, detail = gscan.score_pinned_deps(check, max_paths=2)
assert score == 5.0 and is_na == 0
# deps 截断 max_paths=2，_dep_rows 全量 4 条
assert len(detail['deps']) == 2
assert detail['truncated'] is True
rows = detail.pop('_dep_rows')
assert len(rows) == 4
assert rows[0] == (0, 'containerImage', 'a.yml', 3, 'image: ubuntu', 1, 'digestPinned', 'ok')
assert rows[1] == (1, 'pipCommand', 'b.sh', 7, 'pip3 install x', 0, None, 'use --require-hashes')
assert rows[2] == (2, 'unknown', 'c', None, None, None, None, None)  # id 缺失兜底 unknown
assert rows[3] == (3, 'npmCommand', 'd.yaml', 1, 'npm install', 1, None, 'ok')
# pop 后 detail 可安全 json 序列化（无元组/私有键残留）
j = json.dumps(detail, ensure_ascii=False)
assert '_dep_rows' not in j
# NA 结果无 _dep_rows，主流程 pop 得空列表
na_score, na_is_na, na_detail = gscan.score_pinned_deps({'status': 'inconclusive'}, 200)
assert na_is_na == 1 and na_detail.pop('_dep_rows', []) == []
print('ALL PASS')
