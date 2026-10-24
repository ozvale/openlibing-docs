# -*- coding: utf-8 -*-
# 分析 47 个木兰仓的 LICENSE 文本形态（35 本地 clone + 12 远端下载）
# 分类维度：
#   A. LICENSE 含"如何应用"声明块（Copyright 行 + "X is licensed under Mulan"行）
#      -> 新规则下走印刷模板分支；实测 extract_printed_template 能否提取
#   B. 纯官方木兰文本（无声明块）-> 新规则下走兜底集（木兰模板在其中）
import os, re, io, sys, json, importlib.util

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# repo_id -> repo_name（来自 sdi_repo_info）
REPO_NAMES = {
    400030: "openUBMC/webui", 401009: "openUBMC/devmon", 401010: "openUBMC/libmcpp",
    401011: "openUBMC/component_drivers", 401119: "opengauss/Plugin", 401148: "opengauss/openGauss-server",
    401250: "Ascend/MindIE-SD", 401515: "opengauss/oGRAC", 401629: "Ascend/msprof-analyze",
    401675: "Ascend/AgentSDK", 401676: "Ascend/IndexSDK", 401677: "Ascend/RAGSDK",
    401685: "Ascend/msserviceprofiler", 401704: "Ascend/msprof", 401708: "Ascend/msoptuner",
    401709: "Ascend/mskpp", 401710: "Ascend/msopgen", 401711: "Ascend/msopcom",
    401712: "Ascend/msdebug", 401713: "Ascend/mskl", 401714: "Ascend/msopprof",
    401715: "Ascend/mssanitizer", 401716: "Ascend/mstx", 401717: "Ascend/msinsight",
    401718: "Ascend/msmemscope", 401720: "Ascend/mspti", 401721: "Ascend/msmodelslim",
    401797: "openeuler/openeuler-jenkins", 401866: "openeuler/powerapi", 401881: "openeuler/eagle",
    402124: "openeuler/oeAware-manager", 402270: "openeuler/cache_tuner", 403106: "Ascend/msagent",
    403142: "kunpengcompute/kupl", 403148: "kunpengcompute/kudnn", 403149: "kunpengcompute/kuqcd",
    403150: "kunpengcompute/kunpeng-extension-for-pytorch", 403384: "openeuler/euler-copilot-shell",
    403399: "openeuler/oeDeploy", 403420: "openeuler/oeDevPlugin", 404047: "Ascend/msboost",
    404675: "openUBMC/sensor_mgmt", 404676: "openUBMC/event_mgmt", 404678: "openUBMC/ipmi_mgmt",
    405131: "Ascend/MultimodalSDK", 405515: "boostkit/Megascan", 405549: "Ascend/MindIE-Motor",
}
MULAN_REPOS = sorted(REPO_NAMES.keys())

LOCAL_ROOT = r"C:\Users\caoxiaolin\Desktop\openlibing\docs\0912\_test_repos"
REMOTE_DIR = os.path.join(os.environ["TEMP"], "mulan_remote")

# 加载生产脚本（extract_printed_template 实测）
SFS_PATH = r"C:\Users\caoxiaolin\Desktop\openlibing\docs\0912\security_file_scan.py"
spec = importlib.util.spec_from_file_location("sfs", SFS_PATH)
sfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfs)

# ===== 修复点：re.M 多行锚定 =====
SWNAME_RE = re.compile(r'^\s*(.+?)\s+is licensed under (?:the\s+)?Mulan', re.I | re.M)


def find_lic_local(d):
    # 根目录裸名候选（与 find_license_file 口径一致）
    for n in ["LICENSE", "LICENSE.md", "License", "LICENSE.txt", "Copying", "COPYING", "License.md"]:
        p = os.path.join(d, n)
        if os.path.isfile(p):
            return p
    for fn in os.listdir(d):
        if fn.lower() in ("license", "license.md", "license.txt", "copying", "copying.txt"):
            return os.path.join(d, fn)
    return None


def find_lic_remote(rid):
    if not os.path.isdir(REMOTE_DIR):
        return None
    for fn in os.listdir(REMOTE_DIR):
        if fn.startswith("repo_{0}_".format(rid)):
            p = os.path.join(REMOTE_DIR, fn)
            if os.path.getsize(p) > 100:
                return p
    return None


def classify(txt):
    """返回 (has_decl, decl_block_lines, sw_name, cr_line)"""
    lines = txt.split("\n")
    for i, ln in enumerate(lines):
        if not re.match(r'\s*Copyright', ln, re.I):
            continue
        window = "\n".join(lines[i:i + 5])
        m = SWNAME_RE.search(window)
        if not m:
            continue
        # 版权行需带年份或占位符
        if not (re.search(r'\d{4}', ln) or "[Year" in ln or "[yyyy]" in ln):
            continue
        block = [l.rstrip() for l in lines[i:i + 9]]
        # 截到 "See the Mulan" 行
        for j, b in enumerate(block):
            if re.search(r'See the Mulan', b, re.I):
                block = block[:j + 1]
                break
        return True, block, m.group(1).strip(), ln.strip()
    return False, None, None, None


def cr_style(cr_line):
    if re.search(r'\[Year of First Publication\]', cr_line, re.I):
        return "区间占位符[Year...-Year...]"
    if re.search(r'\[yyyy\]', cr_line, re.I):
        return "占位符[yyyy]"
    if '[' in cr_line:
        return "其他占位符:" + str(re.findall(r'\[[^\]]*\]', cr_line)[:2])
    return "已填年份(无占位符)"


results = {}
for rid in MULAN_REPOS:
    d = os.path.join(LOCAL_ROOT, "repo_{0}".format(rid))
    src = "local"
    lic_path = find_lic_local(d) if os.path.isdir(d) else None
    if lic_path is None:
        lic_path = find_lic_remote(rid)
        src = "remote"
    if lic_path is None:
        results[rid] = {"err": "no license file"}
        continue
    txt = open(lic_path, encoding="utf-8", errors="ignore").read()
    has_decl, block, sw, cr = classify(txt)
    r = {
        "src": src, "file": os.path.basename(lic_path), "has_decl": has_decl,
        "sw": sw, "cr": cr,
    }
    if has_decl:
        r["cr_style"] = cr_style(cr)
        r["sw_eq_repo"] = (sw.lower() == REPO_NAMES[rid].split("/")[-1].lower())
        # 印刷模板提取实测
        try:
            pt = sfs.extract_printed_template(txt)
        except Exception as e:
            pt = "ERR:{0}".format(e)
        r["printed"] = pt
        r["block"] = block
    results[rid] = r

# ===== 输出 =====
A = [rid for rid, v in results.items() if v.get("has_decl")]
B = [rid for rid, v in results.items() if v.get("has_decl") is False]
E = [rid for rid, v in results.items() if "err" in v]

print("总数: {0}  A类(有声明块): {1}  B类(纯官方文本): {2}  异常: {3}".format(
    len(MULAN_REPOS), len(A), len(B), len(E)))
if E:
    print("异常仓:", [(rid, results[rid]['err']) for rid in E])
print()

print("=" * 100)
print("A类仓明细（新规则下走印刷模板分支）")
print("=" * 100)
for rid in A:
    v = results[rid]
    print("\n--- {0} {1}  ({2}:{3}) ---".format(rid, REPO_NAMES[rid], v['src'], v['file']))
    print("  版权行风格: {0}".format(v['cr_style']))
    print("  软件名: {0!r}  == 仓名? {1}".format(v['sw'], v['sw_eq_repo']))
    pt = v["printed"]
    if pt is None:
        print("  extract_printed_template: None (提取不到)")
    elif isinstance(pt, str) and pt.startswith("ERR:"):
        print("  extract_printed_template: {0}".format(pt))
    else:
        print("  extract_printed_template: 提取成功, 长度={0}".format(len(pt)))
        print("  ---- 提取到的模板 ----")
        for l in pt.split("\n"):
            print("    | " + l)
    print("  ---- LICENSE 中的声明块 ----")
    for l in v["block"]:
        print("    | " + l)

print()
print("=" * 100)
print("B类仓清单（纯官方文本 -> 走兜底集含木兰模板）")
print("=" * 100)
for rid in B:
    v = results[rid]
    print("  {0}  {1:45s} {2}:{3}".format(rid, REPO_NAMES[rid], v['src'], v['file']))

# 汇总 JSON 落盘
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_classify_mulan_result.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({str(k): {kk: vv for kk, vv in v.items() if kk != "block"} or v
               for k, v in results.items()}, f, ensure_ascii=False, indent=1, default=str)
print("\n[result json] {0}".format(out))
