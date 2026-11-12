# batch-acl-add — 实现任务

## 进度: 0/6 complete

- [ ] Task 1: 新建分支 `feat-batch-acl-add` 基于 origin/master
- [ ] Task 2: `base/config.py` 新增 Apollo 配置 `SWITCHER_ACL_PORT_ADD_CALLBACK_URL`（NS_XXX 命名空间按现有约定）
- [ ] Task 3: `hidevlab_blue_service.py` 新增 `async_batch_add_port_acl` 函数，遍历 machines → 调用 `add_port_acl_to_core_switcher` → 按 acl_number 聚合 ruleId → `sign_request` 回调
- [ ] Task 4: `hidevlab_blue_service.py` 新增 `/switcher/src/acl/port/add` 路由，解析入参 + 启动后台线程 + 立即返回
- [ ] Task 5: AST 语法检查 + commit
- [ ] Task 6: 用户自测后创建业务 PR + docs PR
