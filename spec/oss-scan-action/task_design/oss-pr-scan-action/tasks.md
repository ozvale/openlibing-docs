# oss-pr-scan-action — 实现任务

## 进度: 10/10 complete（PR 级插件已完成并由 workflow 实跑验证）

- [x] Task 1: 搭建插件目录骨架（oss-pr-scan-action/ + package.json + action.yml + .gitignore）
- [x] Task 2: 实现 index.js 核心（inputs 解析 + trivy 探测/扫描 + JSON 解析统计 + 阈值判定 + Step Summary + core.setFailed）
- [x] Task 3: 编写单测（mock trivy 输出：有高危/全部通过/空结果/部分字段缺失）
- [x] Task 4: ncc 构建 dist/index.js
- [x] Task 5: README.md（用法 + 输入参数 + 判定规则）
- [x] Task 6: `.pre-commit-config.yaml`（代码规范钩子）
- [x] Task 7: `.gitcode/workflows/oss-pr-scan.yml`（push:master + workflow_dispatch + pull_request 自测）
- [x] Task 8: 质量门禁（npm test 通过 + pre-commit 通过）+ 提交 commit
- [x] Task 9: Maven 依赖预解析（方案 A）：shared 新增 `findMavenProjectDir` + `runMavenResolve`
      （先离线 -o 后在线，超时 600s，失败/缺失/mvn 不存在均降级不阻断），
      扫描目标含 pom.xml 时在 trivy 前执行，补齐传递依赖解析；补单测 +
      重建两插件 dist（commit `8cc3159`）
- [x] Task 10: 四级别门禁参数：judge 改为 CRITICAL/HIGH 超门禁阻断（默认 0）、MEDIUM/LOW
      超门禁仅提示（默认 1000）、UNKNOWN 不统计；extractRiskCounts 增四级别计数；
      action.yml/workflow 增 8 个 `*-limit` 参数（废弃 ignore-vuln-count / ignore-license-count）；
      summary 增四级别计数表 + 提示行；补单测（PR 27/version 22 全绿）并重建 dist
      （commit master `3855f73` / main `e828128`）

### 开发中补充/修正（已并入）

- [x] 执行机 trivy 环境确认（版本级机 a959 vs PR 级机 7dbc，见 design.md）
- [x] 移除 `--skip-db-update`，对齐原脚本，漏洞库过期由 trivy 自动更新（commit `468b4c8`）
- [x] 定位老分支漏报根因（详见对话回顾：测试跑错执行机 + 扫全量分支而非预合并）
- [x] 运行时依赖解析漏检根因定位 + 方案 A 修复：公共 Maven Central 限流(429)/私有构件
      404 → 传递依赖解析不出 → 漏洞漏检 → maven 预解析填充 `~/.m2`（详见 design.md"运行时
      依赖解析漏检问题"章节，a959 验证 10→255 包 / 0→50 漏洞，commit `8cc3159`）
- [x] 四级别门禁参数（用户确认：不创建业务 Issue；实现见 Task 10，master `3855f73` / main `e828128`）
- [ ] 版本级插件 `oss-version-scan-action`（待开发完成，确认分支/是否建 issue 语义）

## 验证方式

- 单测：`npm test`（覆盖解析与判定逻辑）
- 本地构建：`npm run build`（ncc 打包 dist）
- workflow 自测：push 到 master 触发 oss-pr-scan.yml，在 openlibing-test 仓跑通扫描并看 Step Summary
- 钩子：pre-commit（yaml/json/md 格式 + gitleaks）

## 生成前约束

- [ ] 只修改 openlibing-test/oss-scan-action + openlibing-docs/spec/oss-scan-action
- [ ] 遵循 pre-commit-action 的 node 调 CLI 风格（execFileSync，不用 docker）
- [ ] 无无关重构 / 格式化 churn
- [ ] 无硬编码凭据 / 敏感信息
- [ ] 行为变化有单测覆盖（解析 & 判定核心逻辑）
- [ ] Commit 规范：type(scope) + Co-authored-by + Generated-by
