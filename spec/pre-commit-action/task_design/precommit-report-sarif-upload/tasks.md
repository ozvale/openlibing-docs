# precommit-report-sarif-upload — 实现任务

## 进度: 0/8 complete

### pre-commit-action 仓（feat-precommit-report-upload）

- [ ] Task 1: package.json 新增依赖 @openlibing/huaweicloud-oidc-client@0.0.5 + esdk-obs-nodejs@3.26.2
- [ ] Task 2: 新增 sarif-converter.js（gitleaks JSON -> SARIF 2.1.0）
- [ ] Task 3: 扩展 index.js：报告目录读取 + PR 类型跳过回调 + SARIF 转换 + OIDC 上传 + APIG 回调
- [ ] Task 4: action.yml 新增 report-dir / debug 输入声明
- [ ] Task 5: 重新 ncc build dist/index.js（node -c 语法验证）
- [ ] Task 6: README.md 同步新输入参数与行为说明

### openlibing-cicd-test 仓（feat-precommit-report）

- [ ] Task 7: .pre-commit-config.yaml 为 gitleaks 增加报告输出 args（--report-path /tmp/pre-commit-reports/gitleaks.json --report-format json）
- [ ] Task 8: 新建 .gitcode/workflows/pre-commit-report.yml（push/schedule/workflow_dispatch + id-token: write，引用新版插件）

### 验证

- [ ] Task 9: 本地 node --check 语法验证 + sarif-converter 单测
- [ ] Task 10: 本地模拟运行（node dist/index.js + 环境变量）验证报告读取与转换
