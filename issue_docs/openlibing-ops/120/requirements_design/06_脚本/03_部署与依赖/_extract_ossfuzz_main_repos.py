"""从本地解压的 google/oss-fuzz projects/ 中提取全部 main_repo，
生成 ossfuzz_main_repos.txt（gcheck --ossfuzz-status 文本表形态）。

用法：python _extract_ossfuzz_main_repos.py <oss-fuzz解压目录> <输出txt>
目录结构要求：<目录>/projects/*/project.yaml
"""
import datetime
import glob
import os
import re
import sys


def main():
    src_root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.environ['TEMP'], 'ossfuzz_extract', 'oss-fuzz-master')
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'ossfuzz_main_repos.txt')

    projects_dir = os.path.join(src_root, 'projects')
    files = (glob.glob(os.path.join(projects_dir, '*', 'project.yaml'))
             + glob.glob(os.path.join(projects_dir, '*', 'project.yml')))
    if not files:
        print(f'ERROR: 未找到任何 project.yaml，检查目录: {projects_dir}')
        sys.exit(1)

    vals = set()
    skipped = []
    for f in files:
        try:
            text = open(f, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        m = re.search(r'^\s*main_repo:\s*(.+?)\s*$', text, re.M)
        if not m:
            skipped.append(os.path.basename(os.path.dirname(f)))
            continue
        v = m.group(1).strip()
        if len(v) >= 2 and v[0] in '"\'' and v[-1] == v[0]:
            v = v[1:-1]
        if not v or v in ('|', '>', '|-', '>-'):
            skipped.append(os.path.basename(os.path.dirname(f)))
            continue
        vals.add(v)

    header = [
        '# OSS-Fuzz main_repo snapshot (for gcheck --ossfuzz-status)',
        '# source: https://github.com/google/oss-fuzz projects/*/project.yaml main_repo',
        '# generated: ' + datetime.datetime.now().strftime('%Y-%m-%d')
        + '  projects=' + str(len(vals))
        + '  skipped_no_main_repo=' + str(len(skipped)),
    ]
    with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(header + sorted(vals)) + '\n')

    print(f'projects scanned = {len(files)}')
    print(f'main_repo values = {len(vals)}')
    print(f'skipped (no main_repo) = {len(skipped)}')
    print(f'output = {out_path} ({os.path.getsize(out_path)} bytes)')
    for probe in ('ffmpeg', 'openssl', 'curl'):
        hits = [v for v in vals if v.rstrip('/').endswith('/' + probe)
                or v.rstrip('.git').rstrip('/').endswith('/' + probe)]
        print(f'  probe {probe}: {hits[:2] if hits else "NOT FOUND"}')


if __name__ == '__main__':
    main()
