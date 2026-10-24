# -*- coding: utf-8 -*-
"""临时对比（测完即删）：我方 v2 scan_copyright vs 内部 copyright-tools 引擎
同一批真实文件、同一份模板文本，只比匹配逻辑差异。
他们的引擎调用方式忠实复刻 scanner.check_file L284-335（离线，不走 license fetch）。"""
import io, sys, re, json, os, random, importlib.util

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

THEIR_BACKEND = r"C:\Users\caoxiaolin\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6abb28483901592a2bc36506\copyright-tools\backend"
sys.path.insert(0, THEIR_BACKEND)
import header_engine as HE   # noqa: E402  他们的引擎（纯函数，无外部依赖）

spec = importlib.util.spec_from_file_location('sfs', r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\security_file_scan.py')
sfs = importlib.util.module_from_spec(spec); spec.loader.exec_module(sfs)

DEMO_DIR = r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\参考\版权合规明细示例'
BASE = r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\_test_repos'

meta = json.load(open(os.path.join(DEMO_DIR, 'copyright_demo_templates.json'), encoding='utf-8'))['templates']
TPL_TXT = {m['template_id']: m['content'] for m in meta}
tpl_meta = json.load(open(os.path.join(DEMO_DIR, 'copyright_demo_repos.json'), encoding='utf-8'))

# 复用生产模板配置（与 _test_copyright_v2_driver 相同的构建方式）
def build_cfg():
    enabled = [m for m in meta if m.get('template_type')]
    mulan, set41 = {}, []
    for m in enabled:
        if m['template_type'] == 'mulan':
            e = {'template_id': m['template_id'], 'pattern': sfs._tpl_pattern(m['content']),
                 'pattern_the': sfs._tpl_pattern(m['content'].replace('copy of Mulan', 'copy of the Mulan'))}
            for lid in m['license_ids']:
                mulan[lid] = e
        else:
            set41.append((m['template_id'], sfs._tpl_pattern(m['content']), m['match_priority']))
    set41.sort(key=lambda x: (x[2], x[0]))
    return {'mulan': mulan, 'set41': [(t, p) for t, p, _ in set41]}

CFG = build_cfg()
OWNER = 'Huawei Technologies Co., Ltd.'

def our_check(content, ext, branch):
    ok, reason, tid, line, banner = sfs.check_copyright_file(content, ext, branch, CFG)
    return ok, reason

def _strip_comment_markers(line):
    """照抄 scanner._strip_comment_markers（L108-114）"""
    line = line.strip()
    for prefix in ["//", "#", "REM", "/*", "*/", "*", '"""']:
        if line.startswith(prefix):
            line = line[len(prefix):]
            break
    return line.strip()

def their_check(content, ext, tpl_text, license_id, software_name=''):
    """复刻 scanner.check_file 核心（L284-335），模板=同一份种子文本"""
    current, _pre = HE.extract_header(content, ext)
    if not current:
        return 'missing', ''
    cur_style = HE.detect_comment_style(current, ext)
    # 从文件头动态提取年份/owner（L290-300）
    year_owner_map, cur_owners, effective_year = {}, [], ''
    for ln in current.split('\n'):
        m = re.search(r'(?i)copyright\s*(?:\(c\)|©)?\s*(\d{4})[,.\s]+(.+)', _strip_comment_markers(ln))
        if m:
            y, owner = m.group(1), m.group(2).strip().rstrip(',. ')
            if not re.match(r'(?i)all\s+rights', owner):
                year_owner_map[owner.lower()] = y
                cur_owners.append(owner)
                if not effective_year:
                    effective_year = y
    effective_owners = [OWNER]
    if cur_owners and {o.lower() for o in cur_owners} <= {OWNER.lower()}:
        effective_owners = cur_owners
    expected = HE.build_header(
        license_id=license_id, owners=effective_owners, year=effective_year, ext=ext,
        license_template='', default_template=tpl_text, header_style='',
        license_url='', license_name='', software_name=software_name,
        force_comment_style=cur_style, year_owner_map=year_owner_map)
    matched, warn, warnings = HE.check_header_match(current, expected, license_id)
    if matched and not warn:
        return 'match', ''
    if matched and warn:
        return 'match_warning', '；'.join(warnings)
    return 'mismatch', ''

def load_target(rdir):
    tracked = sfs.list_tracked_files(rdir)
    out = []
    for rel in tracked:
        _, ext = os.path.splitext(rel)
        if ext.lower() not in sfs.COPYRIGHT_EXTS:
            continue
        segs = rel.split('/')
        if 'test' in segs or 'tests' in segs:
            continue
        out.append((rel, ext.lower()))
    return out

def analyze(repo_dir, repo_json, tpl_id, license_id, software_name='', pass_sample=60, seed=42):
    rdir = os.path.join(BASE, repo_dir)
    targets = load_target(rdir)
    fails = {f['path']: f['reason'] for f in repo_json['fails']}
    branch = ('mulan', repo_json['mulan_license_id']) if repo_json['license_type'] == 'mulan' else ('set41',)
    tpl_text = TPL_TXT[tpl_id]

    random.seed(seed)
    pass_files = [p for p, e in targets if p not in fails]
    sample = set(random.sample(pass_files, min(pass_sample, len(pass_files))))
    files = [p for p, e in targets if p in fails or p in sample]

    stat = {'both_pass': 0, 'ours_fail_their_pass': [], 'ours_pass_their_fail': [], 'both_fail': 0}
    for rel in files:
        ext = os.path.splitext(rel)[1].lower()
        content = sfs.read_head_text(os.path.join(rdir, rel))
        if content is None:
            continue
        ok, reason = our_check(content, ext, branch)
        tv, twarn = their_check(content, ext, tpl_text, license_id, software_name)
        tpass = tv in ('match', 'match_warning')
        if ok and tpass:
            stat['both_pass'] += 1
        elif not ok and tpass:
            stat['ours_fail_their_pass'].append((rel, reason, tv))
        elif ok and not tpass:
            stat['ours_pass_their_fail'].append((rel, reason, tv))
        else:
            stat['both_fail'] += 1
    return stat, len(files)

def report(name, stat, n):
    print(f'\n===== {name}  (N={n}) =====')
    print(f"  双过            : {stat['both_pass']}")
    print(f"  仅我方判不合格   : {len(stat['ours_fail_their_pass'])}")
    print(f"  仅对方判不合格   : {len(stat['ours_pass_their_fail'])}")
    print(f"  双挂            : {stat['both_fail']}")
    for tag, lst in [('仅我方挂(对方过)', stat['ours_fail_their_pass']),
                     ('仅对方挂(我方过)', stat['ours_pass_their_fail'])]:
        from collections import Counter
        c = Counter(f'{r}|{t}' for _, r, t in lst)
        for k, v in c.most_common(6):
            print(f"    {tag} {k} × {v}")
        for rel, r, t in lst[:2]:
            print(f"      e.g. {rel[:70]}")

# --- 403209 pypto-gym: CANN 模板（混合协议，走 set41，最常见命中 custom-cann）---
r0 = next(r for r in tpl_meta if r['repo'] == 'repo_403209')
s, n = analyze('repo_403209', r0, 'custom-cann', 'CANN-2.0')
report('403209 pypto-gym (CANN模板)', s, n)

# --- 401492 ascend-boost-comm: CANN 模板 ---
r1 = next(r for r in tpl_meta if r['repo'] == 'repo_401492')
s, n = analyze('repo_401492', r1, 'custom-cann', 'CANN-2.0')
report('401492 boost-comm (CANN模板)', s, n)

# --- 401717 msinsight: 木兰模板 ---
r2 = next(r for r in tpl_meta if r['repo'] == 'repo_401717')
s, n = analyze('repo_401717', r2, 'mulan-psl-2.0', 'MulanPSL-2.0', software_name='MindStudio')
report('401717 msinsight (木兰模板)', s, n)
