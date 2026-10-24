# -*- coding: utf-8 -*-
"""修复 metric-detail-conf-rule(-def)-update.sql 中 CAST('...' AS JSON) 字面量的
\\u003c/\\u003e/\\u0026 转义（同为经 Doris 执行的 SQL，存在反斜杠被吃风险）。
验证：0 残留 + 每个 CAST JSON 字面量 json.loads 合法。
"""
import json
import re
import sys

BASE = r"c:\Users\caoxiaolin\Desktop\openlibing\docs\0912"
TARGETS = [
    BASE + r"\metric-detail-conf-rule-def-update.sql",
    BASE + r"\metric-detail-conf-rule-update.sql",
]
REPL = [("\\u003c", "<"), ("\\u003e", ">"), ("\\u0026", "&")]
CAST_RE = re.compile(r"CAST\('(\{.*?\})' AS JSON\)")


def main():
    ok_all = True
    for path in TARGETS:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        counts = {seq: text.count(seq) for seq, _ in REPL}
        total = sum(counts.values())
        if total == 0:
            print(f"[SKIP] {path}")
            continue
        fixed = text
        for seq, ch in REPL:
            fixed = fixed.replace(seq, ch)
        residue = sum(fixed.count(seq) for seq, _ in REPL)
        bad = []
        for m in CAST_RE.finditer(fixed):
            try:
                json.loads(m.group(1).replace("''", "'"))
            except Exception as e:
                bad.append(str(e)[:80])
        status = "OK" if (residue == 0 and not bad) else "FAIL"
        if status == "FAIL":
            ok_all = False
        print(f"[{status}] {path}")
        print(f"    replaced: {counts} (total {total}), residue={residue}, bad_json={bad[:3]}")
        if status == "OK":
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(fixed)
            print("    written.")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
