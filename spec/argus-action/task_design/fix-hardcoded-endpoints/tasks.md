# argus-action 硬编码公网端点收敛 — 实现任务

## 进度: 10/10 complete

- [x] 1. 基于 `upstream/master` 新建 `fix-argus-hardcoded-endpoints`
- [x] 2. `argus-scan.js` 收敛两个默认端点常量，删除重复字面量
- [x] 3. `action.yml` 增加默认值说明注释
- [x] 4. 补测试：默认端点 / CLI 覆盖 / Action 输入模式 / Summary 链接
- [x] 5. `zip.js` 打包前同步 `dist/index.js`
- [x] 6. 更新 README（OIDC、默认值、覆盖说明）
- [x] 7. `npm test` + `npm run build` + 产物校验
- [x] 8. `pre-commit`（含 gitleaks）全绿；打包产物路径加入 `.gitleaks.toml` allowlist
- [x] 9. 提交 commit，交付用户自测
- [x] 10. 用户反馈：Summary 改为「漏洞详情」超链接，不暴露裸 URL
