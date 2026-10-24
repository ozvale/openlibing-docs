# -*- coding: utf-8 -*-
"""修复 init SQL 文件中的 \u003c/\u003e/\u0026 转义损坏（2026-10-16）。

背景：detail-conf-init*.sql 中 6 个指标的 conf_json 含 JSON unicode 转义
（\u003c 等），经 MySQL 协议执行时反斜杠被吃，落库成裸 "u003c"，
导致引擎 when 条件解析失败、failItems 全部失效。
修复：源文件中这三个转义序列直接替换为真实字符 < > &
（SQL 字符串与 JSON 中均无需转义），防止再次从源文件灌入损坏数据。

验证：
1. 替换后 0 残留转义；
2. 文件内全部 conf_json 逐条 json.loads 合法；
3. 6 个受影响指标的字面量与 detail-conf-fix-escape.sql 逐字节一致。
"""
import json
import re
import sys

BASE = r"c:\Users\caoxiaolin\Desktop\openlibing"
TARGETS = [
    BASE + r"\openlibing-docs\spec\openlibing-ops\task_design\2026-09-23_安全合规评分看板接口\detail-conf-init.sql",
    BASE + r"\openlibing-docs\spec\openlibing-ops\task_design\2026-09-23_安全合规评分看板接口\detail-conf-init-v2.sql",
    BASE + r"\docs\0912\2026-09-23_安全合规评分看板接口模版SQL\detail-conf-init-v2.sql",
]
FIX_FILE = BASE + r"\docs\0912\2026-09-23_安全合规评分看板接口模版SQL\detail-conf-fix-escape.sql"

REPL = [("\\u003c", "<"), ("\\u003e", ">"), ("\\u0026", "&")]

# conf_json 行形态：整行 = '...'（单引号包裹的 JSON 字面量），前一非空行为 VALUES ('CODE',
INS_RE = re.compile(r"^VALUES \('([A-Z_]+)',\s*$")
LIT_RE = re.compile(r"^'(\{.*\})',\s*$")


def extract_lits(text):
    """提取 (metric_code, conf_json_literal) 列表（literal 含转义原文）。"""
    out = []
    code = None
    for line in text.split("\n"):
        m = INS_RE.match(line.strip())
        if m:
            code = m.group(1)
            continue
        m = LIT_RE.match(line.rstrip("\r"))
        if m and code:
            out.append((code, m.group(1)))
            code = None
    return out


def main():
    # 基准：fix 文件中 6 个指标的 conf_json（unescape 后的标准内容）
    with open(FIX_FILE, encoding="utf-8", newline="") as f:
        fix_text = f.read()
    fix_lits = dict(extract_lits(fix_text))
    print(f"fix file metrics: {sorted(fix_lits)}")

    ok_all = True
    for path in TARGETS:
        # v2 是并行修订版（18 指标内容与 init 有真实版本差异），只做转义替换，
        # 不要求与 fix 文件（源自 init）逐字节一致
        is_v2 = path.endswith("detail-conf-init-v2.sql")
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        counts = {seq: text.count(seq) for seq, _ in REPL}
        total = sum(counts.values())
        if total == 0:
            print(f"[SKIP] {path}: no escape residue")
            continue
        fixed = text
        for seq, ch in REPL:
            fixed = fixed.replace(seq, ch)
        # 验证 1：0 残留
        residue = sum(fixed.count(seq) for seq, _ in REPL)
        # 验证 2：全部 conf_json JSON 合法（先按 SQL 字面量还原：'' -> '）
        bad = []
        for code, lit in extract_lits(fixed):
            try:
                json.loads(lit.replace("''", "'"))
            except Exception as e:
                bad.append((code, str(e)))
        # 验证 3（仅 init 基线文件）：与 fix 文件逐字节对比
        diff = []
        if not is_v2:
            new_lits = dict(extract_lits(fixed))
            for code, lit in new_lits.items():
                if code in fix_lits and lit != fix_lits[code]:
                    diff.append(code)
        status = "OK" if (residue == 0 and not bad and not diff) else "FAIL"
        if status == "FAIL":
            ok_all = False
        print(f"[{status}] {path}")
        print(f"    replaced: {counts} (total {total}), residue={residue}, bad_json={bad}, diff_vs_fix={diff}")
        if status == "OK":
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(fixed)
            print("    written.")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
