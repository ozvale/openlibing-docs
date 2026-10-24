# -*- coding: utf-8 -*-
"""本地核心链路自测驱动：不连 Doris，验证 run_gcheck -> 解析 -> 打分 -> detail 组装。
对照基准（gcheck-integration-handover.md §三，repo_400030 = openUBMC/webui）：
  fuzzing=findings（17 判据全 miss -> 0 分）、pinned-deps=not-applicable（-> NA）、
  binary-artifacts=clean（-> 10 分）
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import security_gcheck_scan as m


class Args:
    gcheck_src = os.path.join(m.SCRIPT_DIR, '参考', 'gcheck', 'gcheck', 'src')
    scorecard_bin = os.path.join(m.SCRIPT_DIR, '_test_gcheck', 'scorecard.exe')
    ossfuzz_status = None
    gcheck_timeout = 900
    max_detail_paths = 200


def run_case(repo_dir, repo_url, repo_id):
    repo = {'repo_id': repo_id, 'repo_url': repo_url, 'platform': 'gitcode'}
    print(f"\n{'=' * 70}\nCASE repo_id={repo_id} {repo_url}\n  dir={repo_dir}")
    if not os.path.isdir(repo_dir):
        print('  SKIP: dir not found')
        return
    results = m.scan_one_repo(repo, repo_dir, Args())
    for code in m.METRIC_CHECK_MAP:
        score, is_na, detail = results[code]
        print(f"  {code:18s} score={score} is_na={is_na}")
        print(f"    detail: {json.dumps(detail, ensure_ascii=False)[:700]}")


if __name__ == '__main__':
    base = os.path.join(m.SCRIPT_DIR, '_test_repos')
    # 基准仓：openUBMC/webui（handover §三 有实测基准结论）
    run_case(os.path.join(base, 'repo_400030'),
             'https://gitcode.com/openUBMC/webui.git', 400030)
    # 第二个真实仓：任选一个，看是否有 binary/fuzz 命中差异
    run_case(os.path.join(base, 'repo_401712'),
             'https://gitcode.com/Ascend/example.git', 401712)
