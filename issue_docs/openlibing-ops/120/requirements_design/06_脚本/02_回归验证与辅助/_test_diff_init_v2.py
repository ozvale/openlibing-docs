# -*- coding: utf-8 -*-
"""对比 init 与 v2 两个 conf 文件的真实版本差异（排除转义差异）。"""
import json
import re

BASE = r"c:\Users\caoxiaolin\Desktop\openlibing"
INS_RE = re.compile(r"^VALUES \('([A-Z_]+)',\s*$")
LIT_RE = re.compile(r"^'(\{.*\})',\s*$")


def extract(path):
    lits = {}
    code = None
    for line in open(path, encoding="utf-8"):
        m = INS_RE.match(line.strip())
        if m:
            code = m.group(1)
            continue
        m = LIT_RE.match(line.rstrip("\r\n"))
        if m and code:
            lits[code] = m.group(1)
            code = None
    return lits


def main():
    a = extract(BASE + r"\openlibing-docs\spec\openlibing-ops\task_design\2026-09-23_安全合规评分看板接口\detail-conf-init.sql")
    b = extract(BASE + r"\openlibing-docs\spec\openlibing-ops\task_design\2026-09-23_安全合规评分看板接口\detail-conf-init-v2.sql")
    print("init metrics:", len(a), "v2 metrics:", len(b))
    print("only in init:", sorted(set(a) - set(b)))
    print("only in v2:", sorted(set(b) - set(a)))
    for code in sorted(set(a) & set(b)):
        ja, jb = json.loads(a[code]), json.loads(b[code])
        if ja != jb:
            print(f"--- {code}: differs")
            for k in sorted(set(ja) | set(jb)):
                if ja.get(k) != jb.get(k):
                    print(f"    key [{k}] differs")


if __name__ == "__main__":
    main()
