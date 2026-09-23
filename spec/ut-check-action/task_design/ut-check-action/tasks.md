# ut-check-action — 实现任务

## 进度: 0/9 complete

- [ ] Task 1: 搭建仓库骨架（action.yml + package.json + ncc 构建 + README 草稿）
- [ ] Task 2: 实现 `lib/parse-surefire.js`（解析 target/surefire-reports/TEST-*.xml，统计用例/失败/错误/跳过/类数，空保护）
- [ ] Task 3: 实现 `lib/parse-jacoco.js`（解析 target/site/jacoco/index.html 行覆盖率，按 exclude-packages 过滤，空保护）
- [ ] Task 4: 实现 `lib/gate.js`（门禁判定：失败+错误>0 阻断 + 行覆盖率<门禁阻断 + Step Summary 组装）
- [ ] Task 5: 实现 `index.js` 主流程（解析 inputs → 校验 mvn → 执行 mvn clean test → 调解析/判定 → setFailed）
- [ ] Task 6: 编写单测（mock surefire/jacoco，覆盖统计、解析、判定边界：空报告/0行/超门禁）
- [ ] Task 7: 本地验证（对本地 java 仓样例跑通解析与判定，或 mock 数据跑测试）
- [ ] Task 8: ncc 打包生成 dist/index.js + 提交第一轮 AI 编码交付 commit
- [ ] Task 9: 本仓自测 workflow（.gitcode/workflows/ut-check.yml，会用插件扫描自己，验证 env 注入 + 门禁）

## 说明

- 语义增强已纳入 Task 4：**失败+错误用例数>0 → 不通过（阻断）**，作为显式门禁（`require-ut-pass` 默认 true）。
- 私仓凭证：插件不接收/不硬编码，依赖 workflow `env:` 注入 `OPENLIBING_MVN_REPO_USERNAME/PASSWORD` 透传给 mvn 子进程。
- settings 默认尊重项目级 `.mvn/maven.config`；`mvn-settings` 输入可显式覆盖。
- 单测要求：解析与判定核心逻辑必须有 mock 数据覆盖（对齐 oss-scan-action 单测范式）。
