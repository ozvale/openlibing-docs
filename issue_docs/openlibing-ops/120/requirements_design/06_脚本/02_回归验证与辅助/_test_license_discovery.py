# -*- coding: utf-8 -*-
"""scorecard v5.5.0 license.go 移植回归测试（官方 license_test.go 用例表 + 本项目边界 +
发现层 find_license_target E2E 模拟）。2026-10-10 LICENSE 定位改版的回归资产：
DS 重新部署生产脚本后可跑本文件确认移植无回归。"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    'lic_scan',
    r'c:\Users\caoxiaolin\Desktop\openlibing\docs\0912\security_license_scan.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# ---- scorecard v5.5.0 checks/raw/license_test.go 官方用例表（shouldFail=false 即命中）----
HIT = [
    'LICENSE', 'LICENCE', 'COPYING', 'MIT-LICENSE-MIT', 'MIT-COPYING',
    'LPPL-1.3clicences', 'LICENSE_LPPL-1.3c', 'PATENTS',
    'APACHE_LICENSETEXT.md', 'COPYRIGHT', 'COPYRIGHT.txt',
    'GPL-2.0-LICENSE', 'GPL-LICENSE', 'GPL2LICENCES', 'GPLLICENCE', 'LICENCES',
    'LICENSE-ASL.txt', 'LICENSE-MPL-2.0', 'license-CC-BY-4.0', 'LICENSE-binary',
    'LICENSE-junit.txt', 'LICENSE.txt', 'LICENSES.txt', 'LICENSES/Apache-2.0.txt',
    'LICENSE_RELEASE', 'Licenses/GPL-3.0.md', 'MIG_kjahdskhaskjdhk_LICENSE',
    'MIT-License', 'MIT_.0_LICENSE', 'MIT_kjahdskhaskjdhk_LICENSE', 'UNLICENSE.md',
    'license.md', 'mit-2-0-0-LICENSE', 'mit-2.0.0-LICENSE', 'mit.2.0.0.LICENSE',
    'mit_2_0_0_LICENSE', 'mit_2_0_LICENSE', 'unlicense',
]
REJECT = [
    'OFL', 'Artistic-1.0-Perl LICENSE', 'GPL',
    '.actions/ASFLicenseHeaderMarkdown.txt', '.baseline/copyright/001_apache-2.0.txt',
    '.copyrightignore', '.dependency_license', '.github/testForLicenseHeaders.sh',
    '.github/workflows/ci_check_license.yml', '.github/workflows/license-check.yaml',
    '.github/workflows/license-check.yml', '.github/workflows/license-checker.yml',
    '.github/workflows/license-eyes.yml', '.github/workflows/license.yml',
    '.github/workflows/licensecheck.yml', '.github/workflows/licenses.yml',
    '.idea/copyright/Eclipse.xml', '.idea/copyright/Winery.xml',
    '.licenserc.yaml',
    '.yarn/cache/spdx-license-ids-npm-3.0.5-cb028e9441-b1ceea3f87.zip',
    'Docgen/business/features/org.polarsys.kitalpha.doc.gen.business.core.feature/license.html',
    'Documentation/doc_infocenter/com.ibm.ism.doc/Reference/SpecialCmd/cmd_imaserver_get_licensedusage.dita',
    'LICENSE,', 'content/dev/apply-license.md',
    'deprecated/3.3/features/org.eclipse.egf.portfolio.genchain.ecoretools.feature/license.html',
    'examples-trunk/LICENSE',
    'jetty-artifact-remote-resources/src/main/resources/META-INF/LICENSE',
    'license.yaml', 'licenserc.yaml', 'python-phoenixdb/LICENSE',
    'static/fonts/OFL.txt', 'VotoSerifGX-OFL/Fonts/VotoSerifGX-VarTTF/OFL.txt',
]
# 本项目补充边界（HIT 中的 licenserc/LICENSEX.md/mylicenses.md 为 scorecard R6
# 宽松性确认——Go 源码同判定；GPL-3.0.md 无核心词，Go 同拒绝）
HIT += ['License', 'licenses', 'patents', 'LICENSES/', 'LICENSES/CANN-V2.0',
        'LICENSES/GPL-V2.0', 'LICENSE/', 'license/', 'NOTALICENSE', 'licences',
        'licenserc', 'LICENSEX.md', 'mylicenses.md']
REJECT += ['README.md', 'readme', 'NOTICE', 'GPL-3.0.md',
           'src/LICENSE', 'LICENSES/sub/x.txt']

fails = 0
for name in HIT:
    path, _ = mod.check_license_name(name)
    if not path:
        fails += 1
        print(f'FAIL(expected hit): {name!r}')
for name in REJECT:
    path, _ = mod.check_license_name(name)
    if path:
        fails += 1
        print(f'FAIL(expected reject): {name!r} -> {path!r}')

# ---- 发现层（find_license_target）E2E：模拟目录 ----
import os
import tempfile

def check_target(desc, setup, expected):
    """setup(dir) 造目录；expected 为期望返回值（None / ('file', rel) / folder 元组首二元素+候选包含判断）"""
    global fails
    d = tempfile.mkdtemp()
    try:
        setup(d)
        got = mod.find_license_target(d)
        ok = False
        if expected is None:
            ok = got is None
        elif expected[0] == 'file':
            ok = got is not None and got[0] == 'file' and got[1] == expected[1]
        elif expected[0] == 'folder':
            ok = (got is not None and got[0] == 'folder' and got[1] == expected[1]
                  and sorted(got[2]) == sorted(expected[2]))
        if not ok:
            fails += 1
            print(f'FAIL(discovery): {desc}: expected {expected!r}, got {got!r}')
        else:
            print(f'OK(discovery): {desc} -> {got!r}')
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)

def touch(base, rel, content='x'):
    p = os.path.join(base, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)

# 1. 裸名大小写不敏感（msmemscope 形态）——本次修复主目标
check_target('bare License (msmemscope)',
             lambda d: touch(d, 'License', 'MulanPSL2'), ('file', 'License'))
# 2. 裸名 LICENSE + 混入无关文件
check_target('LICENSE among others',
             lambda d: [touch(d, x) for x in ('README.md', 'LICENSE', 'setup.py')],
             ('file', 'LICENSE'))
# 3. 带修饰变体（现网 LICENSE.md 形态）
check_target('LICENSE.md only',
             lambda d: [touch(d, x) for x in ('README.md', 'LICENSE.md')],
             ('file', 'LICENSE.md'))
# 4. 优先级：裸名 COPYING 与 License 并存 → LICENSE 族优先（拍板 B-ii）
check_target('COPYING vs License priority',
             lambda d: [touch(d, x) for x in ('COPYING', 'License')],
             ('file', 'License'))
# 5. 优先级：裸名 > 带修饰
check_target('bare vs decorated priority',
             lambda d: [touch(d, x) for x in ('LICENSE-MIT.txt', 'COPYING')],
             ('file', 'COPYING'))
# 6. 文件夹命中（cann/driver 形态，拍板 A-b）
check_target('LICENSES folder (driver)',
             lambda d: [touch(d, x) for x in ('README.md', 'LICENSES/CANN-V2.0', 'LICENSES/GPL-V2.0')],
             ('folder', 'LICENSES', ['LICENSES/CANN-V2.0', 'LICENSES/GPL-V2.0']))
# 7. 文件夹候选受全路径正则约束：LICENSES/sub/ 子目录与非法名不入选
check_target('folder inner filtering',
             lambda d: [touch(d, x) for x in ('LICENSES/GPL-V2.0', 'LICENSES/sub/x.txt',
                                             'LICENSES/notes.yaml', 'LICENSES/README.md')],
             ('folder', 'LICENSES', ['LICENSES/GPL-V2.0', 'LICENSES/README.md']))
# 8. 隐藏条目排除（拍板 C-ii）：.LICENSE 不参与，.licenses/ 目录不参与
check_target('hidden entries excluded',
             lambda d: [touch(d, x) for x in ('.LICENSE', 'README.md')],
             None)
check_target('hidden folder excluded',
             lambda d: [touch(d, '.licenses/Apache-2.0'), touch(d, 'README.md')],
             None)
# 9. 无任何命中
check_target('nothing', lambda d: touch(d, 'README.md'), None)
# 10. 旧口径回归：license/ 子目录里的 LICENSE 现按文件夹口径命中（候选为其中过正则的文件）
check_target('license/ dir as folder',
             lambda d: [touch(d, x) for x in ('license/Apache-2.0.txt', 'README.md')],
             ('folder', 'license', ['license/Apache-2.0.txt']))
# 11. 文件优先于文件夹
check_target('file beats folder',
             lambda d: [touch(d, x) for x in ('LICENSES/GPL-V2.0', 'LICENSE')],
             ('file', 'LICENSE'))

print(f'\ncase total: {len(HIT) + len(REJECT)} + 11 discovery, failures: {fails}')
sys.exit(1 if fails else 0)
