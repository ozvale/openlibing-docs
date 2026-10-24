# -*- coding: utf-8 -*-
"""临时 E2E：真实 scancode 扫本地 driver 克隆（repo_402093），验证多文件聚合。测完即删。"""
import importlib.util
import json
import os

BASE = r"c:\Users\caoxiaolin\Desktop\openlibing\docs\0912"
spec = importlib.util.spec_from_file_location('sls', BASE + r'\security_license_scan.py')
sls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sls)

repo = os.path.join(BASE, '_test_repos', 'repo_402093')
cache = os.path.join(BASE, '_test_p2_cache')
os.makedirs(cache, exist_ok=True)
spdx_map = sls.load_spdx_map(None, cache)
score, row = sls.scan_license(repo, cache, spdx_map, 999)
out = {
    'score': score,
    'spdx': row.get('spdx'),
    'has_license': row.get('has_license'),
    'template_match': row.get('template_match'),
    'copyright_ok': row.get('copyright_ok'),
    'osi_fsf_ok': row.get('osi_fsf_ok'),
    'detail': {k: v for k, v in (row.get('detail') or {}).items() if k != 'matched_text_diagnostics'},
}
print(json.dumps(out, ensure_ascii=False, indent=2))
