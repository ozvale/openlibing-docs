#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""回归自测：_check_status_na 对 gcheck 两种 errors 形态的兼容性。

背景（2026-10-13 生产事故）：security_gcheck_scan.py 新的 exit=3 分 check 落分路径
首次触达 inconclusive check 的 diagnostics.errors，其元素是 {scope, message} 字典
（gcheck render.py 同构），旧代码按纯字符串 join 抛 TypeError，整仓 FAIL。
修复后须验证：字典形态 / 字符串形态 / 空列表 三种输入均产出正确 NA 消息，且与 gcheck
render 的 scope/message 拼装口径一致。只做纯函数级回归（不跑 gcheck、不连 Doris）。
"""
import sys
import os

# security_gcheck_scan.py 顶层无副作用（main 有 __main__ 守卫），可安全 import
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))        # _test_gcheck/
PARENT = os.path.dirname(HERE)                            # 0912/
spec = importlib.util.spec_from_file_location(
    'gscan', os.path.join(PARENT, 'security_gcheck_scan.py'))
gscan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gscan)

# ① 字典形态（gcheck 真实结构，对应 401480 生产事故数据）
check_dict = {
    'check': 'pinned-deps', 'status': 'inconclusive',
    'diagnostics': {'errors': [
        {'scope': 'shards', 'message': '2 shard files not scanned'},
        {'scope': 'ci', 'message': 'workflow fetch failed'},
    ]}}
reason, msg = gscan._check_status_na(check_dict)
assert reason == 'gcheck_inconclusive', reason
assert msg == ('gcheck status=inconclusive: shards: 2 shard files not scanned; '
               'ci: workflow fetch failed'), msg
print('PASS dict-form errors ->', msg)

# ② 字典形态：message 缺失时的兜底（scope 兜底用 check 名）
check_nomsg = {'check': 'pinned-deps', 'status': 'error',
               'diagnostics': {'errors': [{'scope': 'x'}]}}
reason, msg = gscan._check_status_na(check_nomsg)
assert reason == 'gcheck_error', reason
assert msg == 'gcheck status=error: x: 原因未知', msg
print('PASS dict-form without message ->', msg)

# ③ 字典形态：scope/message 全缺失（兜底 check 名 + 原因未知）
check_bare = {'check': 'fuzzing', 'status': 'inconclusive',
              'diagnostics': {'errors': [{}]}}
reason, msg = gscan._check_status_na(check_bare)
assert msg == 'gcheck status=inconclusive: fuzzing: 原因未知', msg
print('PASS bare dict ->', msg)

# ④ 纯字符串形态（历史容错：万一 gcheck 未来输出纯文本错误）
check_str = {'check': 'pinned-deps', 'status': 'inconclusive',
             'diagnostics': {'errors': ['plain error text']}}
reason, msg = gscan._check_status_na(check_str)
assert msg == 'gcheck status=inconclusive: plain error text', msg
print('PASS str-form errors ->', msg)

# ⑤ 空错误列表 / 正常状态：不受影响
check_ok = {'check': 'pinned-deps', 'status': 'findings', 'diagnostics': {}}
assert gscan._check_status_na(check_ok) is None
check_noerr = {'check': 'pinned-deps', 'status': 'inconclusive',
               'diagnostics': {'errors': []}}
reason, msg = gscan._check_status_na(check_noerr)
assert (reason, msg) == ('gcheck_inconclusive', 'gcheck status=inconclusive'), msg
print('PASS clean/findings & empty errors ->', reason, msg)

print('ALL PASS')
