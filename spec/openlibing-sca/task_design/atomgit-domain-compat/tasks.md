# atomgit-domain-compat — 实现任务

## 进度: 0/6 complete

- [ ] Task 1: 新增 `common/utils/GitcodeUrlUtil.java`（`gitcode.domains` 注入 + `isGitcodeUrl` / `stripDomain`）
- [ ] Task 2: 新增 `GitcodeUrlUtilTest`
- [ ] Task 3: `IntegrationApiServiceImpl` 移除 `ATOMGIT_URL` / `replaceAtomgitDomain`，17 处判定替换，`getCodeHostingPlatformFlag` 兼容 atomgit
- [ ] Task 4: `DownLoadFilesUtils#deleteRepoFromGitcode` 判定替换
- [ ] Task 5: 更新 `IntegrationApiServiceImplTest`（删旧用例 + 补双域名用例）
- [ ] Task 6: 编译 + 相关测试验证（`python scripts/run-mvn.py test -Dtest=GitcodeUrlUtilTest,IntegrationApiServiceImplTest`）
