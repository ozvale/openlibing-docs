# sbom-output-list — 实现任务

## 进度: 0/7 complete

## 前置

- [x] 业务 Issue 已创建：https://gitcode.com/openlibing/trivy-action/issues/2
- [x] docs spec 分支已建：`spec/oss-scan-action/sbom-output-list`
- [x] proposal.md / design.md 已落盘

## 实现任务

- [ ] Task 1: `shared/index.js` 新增 `extractPackageList(resultJson)`（提取组件列表，按 Name 去重+排序，含 direct/indirect 统计）
- [ ] Task 2: `shared/index.js` 新增 `packageListToTable(pkgs, maxRows=500)` 与 `packageListToCode(pkgs, maxRows=500)`（含截断+提示行）
- [ ] Task 3: `shared/index.js` scan() 中解析 `sbom-output` / `sbom-output-type` 参数；在统计/明细后插入清单输出（Summary 截断 + 日志全量）；exports 补充
- [ ] Task 4: `oss-pr-scan-action/action.yml` + `oss-version-scan-action/action.yml` 声明两输入
- [ ] Task 5: 两插件 test 补充单测：参数解析（null/list/非法值）+ 清单生成（table/code/截断/统计行）
- [ ] Task 6: 运行 `npm test`（PR/version 两套）全绿；`npm run build` 重建 dist
- [ ] Task 7: README ×2 补充参数说明；docs 本分支 tasks.md 勾选完成

## 验证方式

```bash
# 单测（mock trivy 输出，不发真实请求）
cd oss-scan-action && npm test
# 构建
cd oss-pr-scan-action && npm run build
cd oss-version-scan-action && npm run build
```

## 验收映射

| 验收标准                          | 对应任务   |
| --------------------------------- | ---------- |
| sbom-output 默认 null / list 生效 | Task 1,3   |
| sbom-output-type table/code       | Task 2,3,5 |
| 统计 + group:artifact + 版本      | Task 1,2,5 |
| ≥500 截断 + 日志全量              | Task 2,3,5 |
| action.yml 声明                   | Task 4     |
| 测试全绿                          | Task 6     |
