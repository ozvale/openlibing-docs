# fix-vuln-dependency-tree — 实现任务

## 进度: 0/5 complete

## 前置

- [x] 业务 Issue 已确认：#2（开源软件清单输出，含展示增强）
- [x] docs spec 分支已建：`spec/oss-scan-action/fix-vuln-dependency-tree`
- [x] proposal.md / design.md 已落盘

## 实现任务

- [ ] Task 1: `shared/index.js` 重构 `buildVulnDependencyTree`（反图 BFS + 同根合并 + severity 取最高 + 孤列）
- [ ] Task 2: `shared/index.js` 新增 `findPythonDepFiles` 并在 scan() 中插入 Summary/日志提示
- [ ] Task 3: `dependencyTreeToText` 兼容孤列节点；`oss-version-scan-action/README.md` + `oss-pr-scan-action/README.md` 补语言能力说明
- [ ] Task 4: 补单测（多根 pnpm 样例 / 同根合并 / Python 孤列 / severity 最高级别 / 依赖环）/ `npm test` 两套全绿
- [ ] Task 5: `npm run build` 重建两插件 dist；docs 分支 tasks.md 勾选

## 验证方式

```bash
cd oss-scan-action
npm test                                   # 根目录无 test 脚本则分别跑两插件
cd oss-version-scan-action && npm test && npm run build
cd oss-pr-scan-action && npm test && npm run build
```

## 验收映射

| 验收标准                           | 对应任务 |
| ---------------------------------- | -------- |
| 多根漏洞组件均展示引入链且同根合并 | Task 1,4 |
| Maven 单根输出与现状一致           | Task 1,4 |
| severity 取最高级别                | Task 1,4 |
| Python 组件孤列不报错              | Task 1,3 |
| Python 依赖文件出现 lock 提示      | Task 2,4 |
| README 语言能力说明                | Task 3   |
