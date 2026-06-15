# 代码仓管理公共账号正确性校验前置 — 实现任务

## 进度: 0/3 complete

- [ ] Task 1: 在RepoServiceImpl中新增validateAccessToken方法，调用/v5/user API校验token有效性，无效时返回明确错误信息
- [ ] Task 2: 在addRepoInfo方法中，createAndSaveRepoInfo调用前，当accessToken不为空时调用validateAccessToken进行前置校验
- [ ] Task 3: 在updateRepoInfo方法中，当isEditAccessToken为true且accessToken不为空时调用validateAccessToken进行前置校验
