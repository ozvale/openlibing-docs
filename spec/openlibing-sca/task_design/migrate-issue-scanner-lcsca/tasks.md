# Tasks: migrate-issue-scanner-lcsca

- **业务 Issue**: openlibing/openlibing-sca#78
- **交付 PR**: https://gitcode.com/openlibing/openlibing-sca/pull/313（dev_scanner -> release_20260923，11 commits，已合入）
- **分支**: dev_scanner（业务仓）

## T1 源码迁移（commit 1: `ada506c1`）

- [x] T1.1 创建 `tools/issue-scanner/src/` 目录结构（reposca/、reposca/config/、util/）
- [x] T1.2 拷贝 `command.py`
- [x] T1.3 拷贝 reposca 8 个 py + `__init__.py`（commSca、prSca、itemLicSca、analyzeSca、sourceAnalyze、licenseCheck、repoDb、takeRepoSca）
- [x] T1.4 拷贝 `reposca/config/Licenses.yaml`
- [x] T1.5 拷贝 util 8 个 py（authApi、catchUtil、downUtil、extractUtil、formateUtil、popUtil、postOrdered、stack）
- [x] T1.6 写入裁剪版 `requirements.txt`（初版 19 项，见 design.md §3.3）
- [x] T1.7 `python -m py_compile` 验证全部迁移文件语法
- [x] T1.8 确认未带入 token.yaml / **pycache** / temp 等无关文件
- [x] T1.9 commit：`feat(tools): 引入 issue-scanner lcsca 最小闭包源码`（ada506c1）

## T2 Dockerfile（commit 2: `5cb5d0ff`）

- [x] T2.1 删除 git credential 写入与 git clone 步骤（L76-79）
- [x] T2.2 替换为 `COPY ./tools/issue-scanner` + pip install（清华源）
- [x] T2.3 删除 GIT_USERNAME / GIT_PASSWORD 的 ARG 声明
- [x] T2.4 文本检查：Dockerfile 无 clone / git-credentials / GIT_USERNAME / GIT_PASSWORD 残留
- [x] T2.5 commit：`build(docker): 移除 issue-scanner git clone，改用 tools 目录 COPY`（5cb5d0ff）

## T3 Java 常量与单测（commit 3: `dc862567`）

- [x] T3.1 `DMContastName.ISSUESCANNER`: `"issue-scanner"` → `"tools/issue-scanner"`（后随 T6.3 重命名为 tools/license-scanner）
- [x] T3.2 `PrCommonName.ISSUESCANNER`: 同步改值
- [x] T3.3 更新 `DMContastNameTest` 断言（L24、L52）
- [x] T3.4 更新 `PrCommonNameTest` 断言（L31、L55）
- [x] T3.5 核对 `OpenPersonDMScanDMServiceImplTest` 相关用例是否依赖 workdir 具体值（不依赖：测试走两参重载，workdir 由参数传入）
- [x] T3.6 运行 `python scripts/run-mvn.py` 受影响测试类，全部通过（4/4）
- [x] T3.7 commit：`feat(scanner): 容器内 issue-scanner 路径改至 tools/issue-scanner`（dc862567）

## T4 迁移验证修复（commits 4-6）

- [x] T4.1 删除与 scancode-toolkit 31.0.1 冲突的 commoncode pin（commit `dc38260f`）
- [x] T4.2 删除 `CommSca.__init__` 中 lcsca 路径用不到的 DB init（MYSQL_* 未配置时 TypeError；commit `68dacc3a`）
- [x] T4.3 Dockerfile 构建期预创建 `/home/repo/tempRepo` 并 chown 非 root 用户（PermissionError → stdout null；commit `1a8e5600`）

## T5 依赖升级与死代码清理（commits 7-8，2026-09-23 补充范围）

- [x] T5.1 升级漏洞依赖 pin：requests 2.34.2 / setuptools 80.10.2 / urllib3 2.8.0（1.x → 2.x）/ GitPython 3.1.62 / pdfminer.six 20260107（42 个 High/Critical 归零；commit `7c84168c`）
- [x] T5.2 修正 Dockerfile 尾部 pdfminer.six 降级覆盖安装问题
- [x] T5.3 删除 DB 死代码：repoDb / prSca / itemLicSca / takeRepoSca 四模块 + command.py `-m pr` 入口 + commSca 对 itemLicSca 的模块级 import（commit `3d93edb9`）
- [x] T5.4 requirements 移除 PyMySQL / DBUtils / SQLAlchemy（19 → 16 项）；py_compile 通过 + src 下零残留引用

## T6 目录重命名与交付（commits 10-11）

- [x] T6.1 `tools/issue-scanner` → `tools/license-scanner` 目录重命名（commit `731f5ba2`）
- [x] T6.2 Java 常量（DMContastName / PrCommonName）、测试断言、Dockerfile COPY 路径同步为 `tools/license-scanner`
- [x] T6.3 全量自检：文件清单比对（最终 15 源文件 + requirements 16 项）、Docker 构建通过
- [x] T6.4 生成前约束自检（范围、风格、无敏感信息、测试覆盖）
- [x] T6.5 业务 PR 创建并合入（#313，ai-assisted / ci-pipeline-passed / lgtm / approved 标签）

## 遗留项

- [ ] 容器内执行 `python src/command.py -m lcsca` 端到端扫描验证（PR #313 测试计划遗留项；urllib3 1.x → 2.x 等升级需实扫确认）

## T7 归档（用户触发）

- [ ] T7.1 archive.md 写入 openlibing-docs（本目录）
- [ ] T7.2 docs PR：spec 沉淀至 openlibing-docs 主干
