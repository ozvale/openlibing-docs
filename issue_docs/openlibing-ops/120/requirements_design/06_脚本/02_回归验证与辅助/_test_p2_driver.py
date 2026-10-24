#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2 临时测试驱动（2026-09-21）：复用 _test_repos 已 clone 仓，绕过连库直测
find_license_file + run_scancode + 解析 + 阶梯计分。测完即删。"""
import importlib.util
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('sls', os.path.join(BASE, 'security_license_scan.py'))
sls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sls)

work = os.path.join(BASE, '_test_repos')
cache = os.path.join(BASE, '_test_p2_cache')
os.makedirs(cache, exist_ok=True)

if not sls.check_scancode_available():
    print("scancode not available")
    sys.exit(1)

spdx_set = sls.load_spdx_set(None, cache)
print(f"SPDX set loaded: {'yes(' + str(len(spdx_set)) + ' licenses)' if spdx_set else 'NO (osi_fsf will be NULL)'}")

seq = 0
rows = []
for d in sorted(os.listdir(work)):
    if not d.startswith('repo_'):
        continue
    seq += 1
    repo_path = os.path.join(work, d)
    lic = sls.find_license_file(repo_path)
    score, row = sls.scan_license(repo_path, cache, spdx_set, seq)
    det = row.get('detail') or {}
    reason = det.get('reason', '')
    print(f"{d}  score={score}  license={lic}  spdx={row.get('spdx')}  "
          f"template={row.get('template_match')} copy_ok={row.get('copyright_ok')} "
          f"osi_fsf={row.get('osi_fsf_ok')}"
          + (f"  reason={reason}" if reason else ""))
    rows.append((d, score, row.get('spdx'), lic))

print(f"\nscanned: {len(rows)}, no-license(0): "
      f"{sum(1 for r in rows if r[2] is None and r[3] is None)}")
