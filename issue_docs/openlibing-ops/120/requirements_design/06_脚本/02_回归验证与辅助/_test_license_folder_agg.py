# -*- coding: utf-8 -*-
"""临时验证：scan_license 文件夹分支"全部达标"聚合口径（2026-10-19）。测完即删。"""
import importlib.util
import sys

BASE = r"c:\Users\caoxiaolin\Desktop\openlibing\docs\0912"
spec = importlib.util.spec_from_file_location('sls', BASE + r'\security_license_scan.py')
sls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sls)


def mk_row(spdx, score, tpl, cr, osi, osi_a, fsf, detail=None):
    return {'spdx': spdx, 'has_license': 1 if score >= 5 else 0,
            'template_match': tpl, 'copyright_ok': cr, 'osi_fsf_ok': osi,
            'osi_approved_ok': osi_a, 'fsf_libre_ok': fsf,
            'detail': detail if detail is not None else {'license_path': 'x'},
            'raw_json': '{}'}


def patch(rows_scores):
    """rows_scores: [(rel, score, row)] 依序返回"""
    sls.find_license_target = lambda p: ('folder', 'LICENSES', [r[0] for r in rows_scores])
    def fake_scan(repo_path, rel, work_dir, spdx_map, out_name):
        for r, s, row in rows_scores:
            if r == rel:
                return s, row
        raise AssertionError(rel)
    sls._scan_license_file = fake_scan


fails = []
def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond:
        fails.append(name)


# 用例1：driver 现实形态——两文件均 8 分（CANN 模板过/版权/OSI 未过；GPL 同分）
rows = [
    ('LICENSES/CANN-V2.0', 8.0, mk_row('cann-v2.0', 8, 1, 0, 0, 0, 0)),
    ('LICENSES/GPL-V2.0', 8.0, mk_row('GPL-2.0-only', 8, 1, 0, 1, 1, 1)),
]
patch(rows)
score, row = sls.scan_license('/repo', '/tmp', None, 1)
check('case1 min score = 8', score == 8.0)
check('case1 spdx joined', row['spdx'] == 'cann-v2.0、GPL-2.0-only')
check('case1 template AND = 1', row['template_match'] == 1)
check('case1 copyright AND = 0', row['copyright_ok'] == 0)
check('case1 osi AND = 0', row['osi_fsf_ok'] == 0)
check('case1 detail.template_id joined',
      row['detail']['template_id'] == 'cann-v2.0、GPL-2.0-only')
check('case1 detected_licenses 2 entries',
      [d['spdx'] for d in row['detail']['detected_licenses']] == ['cann-v2.0', 'GPL-2.0-only'])
pf = row['detail']['folder_files_scanned']
check('case1 per_file enriched', pf[0]['template_match'] == 1 and pf[1]['osi_fsf_ok'] == 1)
check('case1 no score key in row_fields', 'score' not in row)
check('case1 license_folder kept', row['detail']['license_folder'] == 'LICENSES')

# 用例2：分差聚合——CANN 5 分、GPL 10 分 → min=5，模板/版权/OSI 均 AND=0
rows = [
    ('LICENSES/CANN-V2.0', 5.0, mk_row('cann-v2.0', 5, 0, 0, 0, 0, 0)),
    ('LICENSES/GPL-V2.0', 10.0, mk_row('GPL-2.0-only', 10, 1, 1, 1, 1, 1)),
]
patch(rows)
score, row = sls.scan_license('/repo', '/tmp', None, 2)
check('case2 min score = 5', score == 5.0)
check('case2 all flags AND = 0',
      row['template_match'] == 0 and row['copyright_ok'] == 0 and row['osi_fsf_ok'] == 0)

# 用例3：一文件未识别出许可证（0 分）→ 整仓 0
rows = [
    ('LICENSES/CANN-V2.0', 0.0, {**sls._no_license_row(),
                                 'detail': {'reason': 'no_license_detected'}}),
    ('LICENSES/GPL-V2.0', 8.0, mk_row('GPL-2.0-only', 8, 1, 0, 1, 1, 1)),
]
patch(rows)
score, row = sls.scan_license('/repo', '/tmp', None, 3)
check('case3 min score = 0', score == 0.0)
check('case3 has_license = 0', row['has_license'] == 0)
check('case3 spdx = 仅可识别者', row['spdx'] == 'GPL-2.0-only')
check('case3 per_file 留痕含 reason',
      row['detail']['folder_files_scanned'][0]['reason'] == 'no_license_detected')

# 用例4：OSI 标志含 NULL（SPDX 清单不可用）→ AND = None
rows = [
    ('LICENSES/A', 8.0, mk_row('A-1.0', 8, 1, 1, None, None, None)),
    ('LICENSES/B', 8.0, mk_row('B-1.0', 8, 1, 1, 1, 1, 1)),
]
patch(rows)
score, row = sls.scan_license('/repo', '/tmp', None, 4)
check('case4 osi AND = None', row['osi_fsf_ok'] is None and row['osi_approved_ok'] is None)

# 用例5：单文件命中行为不变（走 file 分支）
sls.find_license_target = lambda p: ('file', 'LICENSE')
sls._scan_license_file = lambda *a, **k: (10.0, mk_row('MIT', 10, 1, 1, 1, 1, 1))
score, row = sls.scan_license('/repo', '/tmp', None, 5)
check('case5 single file unchanged', score == 10.0 and row['spdx'] == 'MIT'
      and 'folder_files_scanned' not in row['detail'])

print('\n' + ('ALL PASS' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
