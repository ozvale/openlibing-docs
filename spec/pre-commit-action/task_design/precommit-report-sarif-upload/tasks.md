# precommit-report-sarif-upload — 实现任务

## 进度: 14/14 complete

### pre-commit-action 仓（feat-precommit-report-upload）

- [x] Task 1: package.json 新增依赖 @openlibing/huaweicloud-oidc-client@0.0.5 + esdk-obs-nodejs@3.26.2 + undici@^5.28.4
- [x] Task 2: 扩展 index.js：报告目录读取（仅收集 *.sarif）+ PR 类型跳过回调 + OIDC 上传（ACL public-read）+ APIG 回调（业务码校验 + env-type 切换 + resolveBranch）
- [x] Task 3: action.yml 新增 report-dir / env-type / debug 输入声明（版本 1.0.30）
- [x] Task 4: 重新 ncc build dist/index.js（语法验证）
- [x] Task 5: README.md 同步新输入参数与报告上传契约
- [x] Task 6: 移除 sarif-converter.js（转换归属业务仓，插件不内置转换能力）

### openlibing-cicd-test 仓（feat-precommit-report）

- [x] Task 7: .pre-commit-config.yaml 配置 local 钩子 scripts/detect-secrets-report.sh（language: system，require_serial）
- [x] Task 8: 新增 scripts/detect-secrets-report.sh：扫描生成 detect-secrets.json + 调转换脚本 + 临时 baseline 拦截
- [x] Task 9: 新增 scripts/convert-detect-secrets-to-sarif.py（JSON → SARIF 2.1.0，含稳定指纹）
- [x] Task 10: 新建 .gitcode/workflows/pre-commit-report.yml（workflow_dispatch + id-token: write，引用 feat-precommit-report-upload 分支）

### openlibing-codecheck 仓（feat-codearts-check-tool-routing）

- [x] Task 11: StandardSarifParser.extractLocationHash 增加指纹兜底（primaryLocationLineHash 缺失时 sha256(uri|startLine|ruleId)）
- [x] Task 12: StandardSarifParserTest 新增兜底路径单测（无指纹 / 指纹为空白），全量用例通过

### 验证

- [x] Task 13: 转换脚本本地验证（detect-secrets JSON → SARIF 2.1.0，1 rule / 1 result / 64 位指纹）
- [x] Task 14: 端到端验证（OBS 上传成功 + APIG 回调；后端指纹兜底后 issue 正常入库，待后端发版部署确认）
