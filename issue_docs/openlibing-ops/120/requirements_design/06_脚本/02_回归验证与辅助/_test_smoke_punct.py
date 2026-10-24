# -*- coding: utf-8 -*-
"""临时冒烟（测完即删）：标点贴紧归一修复后，MindIE-SD 合法填写文件应翻盘命中，
同时验证 xla-npu（https 归一）与 AgentSDK（版权行错位，应维持不命中）不回退。"""
import importlib.util
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location('sfs', os.path.join(BASE, 'security_file_scan.py'))
sfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfs)

for rid, nm, expect in [
    ('repo_401250', 'MindIE-SD', '应大量命中'),
    ('repo_402260', 'xla-npu', '应命中38/53'),
    ('repo_401675', 'AgentSDK', '应维持0（版权行错位）'),
]:
    repo = os.path.join(BASE, '_test_repos', rid)
    _, lic_text = sfs.find_license_file(repo)
    pat = sfs.extract_printed_template(lic_text)
    tracked = sfs.list_tracked_files(repo)
    hit = miss = 0
    miss_samples = []
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
            miss += 1
            if len(miss_samples) < 2:
                miss_samples.append(rel)
            continue
        if pat.search(sfs._norm_text('\n'.join(lines))):
            hit += 1
        else:
            miss += 1
            if len(miss_samples) < 2:
                miss_samples.append(rel)
    print(f'{nm}({rid}) [{expect}]: 命中 {hit} / 未中 {miss}')
    for s in miss_samples:
        print(f'   未中样本: {s}')
