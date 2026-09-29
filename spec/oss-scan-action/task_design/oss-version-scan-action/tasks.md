# oss-version-scan-action — 实现任务

## 进度: 8/8 complete（共享核心 + PR/version 薄入口 + 单测 + dist + workflow + README 已完成）

- [x] Task 1: 抽取 `shared/index.js`（从 oss-pr-scan-action 抽离扫描/解析/判定/summary 纯逻辑）
- [x] Task 2: 重构 `oss-pr-scan-action/index.js` 为薄入口（引用 shared）+ 跑原单测回归
- [x] Task 3: 新建 `oss-version-scan-action/`（package.json + action.yml + index.js 薄入口）
- [x] Task 4: 编写 shared/version 单测（mock trivy 输出：有高危/全部通过/空结果/缺字段）

* [x] Task 4.5: Maven 依赖预解析（方案 A）随 shared 一并下发：`findMavenProjectDir` +
      `runMavenResolve` 单测补到 version 测试文件（commit `8cc3159`）

- [x] Task 5: ncc 构建两个插件 dist（commit `8cc3159` 已重建含 mvn 预解析）
- [x] Task 6: `oss-version-scan-action/README.md`（附 maven 环境前提 + 四级别门禁参数）
- [x] Task 7: `.gitcode/workflows/oss-version-scan.yml`（自测：workflow_dispatch，含 8 个门禁 inputs）

* [x] Task 7.5: 四级别门禁随 shared 下发：judge 四级别判定 + extractRiskCounts 四级别计数 +
      action.yml/workflow 8 个 `*-limit` 参数 + version 单测（22 例全绿）
      （commit master `3855f73` / main `e828128`）

- [x] Task 8: 质量门禁（npm test PR 27/version 22 全绿 + pre-commit 通过）+ 提交 commit

## 验证方式

- 单测：PR 级既有用例（8 个）改引 shared 后全部通过；version 复跑
- 本地构建：两个插件 `npm run build`
- workflow 自测：`workflow_dispatch` 触发 version 扫描（版本级执行机 `oss=version`）看 Step Summary
- 钩子：pre-commit（yaml/json/md + gitleaks）

## 生成前约束

- [ ] 只修改 openlibing-test/oss-scan-action + openlibing-docs/spec/oss-scan-action
- [ ] shared 抽取时 PR 级行为不变（原单测全绿）
- [ ] 无硬编码凭据 / 敏感信息（插件不接收 token）
- [ ] 版本级插件不实现 create-issue（与扫描解耦）
- [ ] Commit 规范：type(scope) + Co-authored-by + Generated-by
