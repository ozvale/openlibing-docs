# argus-action 端点配置与出站 URL 安全加固 — 实现任务

> 覆盖 Issue：#2（硬编码公网端点）、#14（codecheck-ip/prefix SSRF 与签名请求外发）。

## 进度: 17/17 complete

### #2（已完成）

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

### #14（进行中）

- [x] 11. 实现 `codecheck-ip` 校验：HTTPS、拒绝 userinfo、IP、localhost、内网、query/fragment
- [x] 12. 实现 `codecheck-prefix` 校验与最终 URL origin 一致性校验
- [x] 13. `repositoryName` 使用 `encodeURIComponent`
- [x] 14. 补测试：http/IP/localhost/userinfo/`@` 前缀/query/编码
- [x] 15. README / action.yml 标注受信配置与禁止用法
- [x] 16. `npm test` + `npm run build` + `pre-commit`，提交 #14 commit
- [x] 17. 新增 `allowed-hosts` 受信主机列表（默认 `apig.openlibing.com`），最终 host 必须命中
