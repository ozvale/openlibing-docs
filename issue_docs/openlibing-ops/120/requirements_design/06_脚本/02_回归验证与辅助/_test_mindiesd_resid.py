# -*- coding: utf-8 -*-
"""临时抽查（测完即删）：MindIE-SD 未命中文件的原因分布。"""
import importlib.util
import io
import os
import re
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location('sfs', os.path.join(BASE, 'security_file_scan.py'))
sfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfs)

repo = os.path.join(BASE, '_test_repos', 'repo_401250')
_, lic_text = sfs.find_license_file(repo)
pat = sfs.extract_printed_template(lic_text)
print('pattern[:150]:', pat.pattern[:150])
tracked = sfs.list_tracked_files(repo)
reasons = Counter()
samples = {}
for rel in tracked:
    _, ext = os.path.splitext(rel)
    if ext.lower() not in sfs.COPYRIGHT_EXTS:
        continue
    segs = rel.split('/')
    if 'test' in segs or 'tests' in segs:
        continue
    content = sfs.read_head_text(os.path.join(repo, rel))
    if content is None:
        continue
    lines = sfs._clean_header_lines(sfs.extract_header(content, ext.lower()))
    cl = sfs._find_copyright_line(lines) if lines else None
    if cl is None and ext.lower() == '.py':
        ds = sfs._clean_header_lines(sfs.extract_docstring_header(content))
        if ds:
            cl = sfs._find_copyright_line(ds)
            lines = ds
    if not lines or cl is None:
        reasons['no_copyright_line'] += 1
        samples.setdefault('no_copyright_line', rel)
        continue
    if pat.search(sfs._norm_text('\n'.join(lines))):
        reasons['hit'] += 1
    else:
        reasons['template_mismatch'] += 1
        if 'template_mismatch' not in samples:
            jn = sfs._norm_text('\n'.join(lines))
            print('mismatch 样本:', rel)
            print('  版权行:', cl.strip()[:110])
            print('  归一化头[:240]:', jn[:240])
        samples.setdefault('template_mismatch', rel)
print('分布:', dict(reasons))
