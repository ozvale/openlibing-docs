# perm-group-postlaunch-fixes — 实现任务

## 进度: 7/7 complete

- [x] Task 1: query-groups 成员数按用户去重修正（commit d0a51807，后由 Task 5 升级为列表页同口径）
- [x] Task 2: 成员数口径对齐成员管理页 countProjectUser（commit bbcd73de，含外部账号计入默认组）
- [x] Task 3: 权限组操作日志接入 v2，新增 PermGroupLogHandler 覆盖 6 个写接口（commit 4179f477）
- [x] Task 4: 添加成员日志补逐账号失败明细（commit e0e1548b）
- [x] Task 5: 添加成员日志补账号清单与部分失败前缀（commit 89bec5f4）
- [x] Task 6: 评审意见修复——复制组口径对账、批量绑定资源摘要、账号清单超长防护（commit 47bb09d1）
- [x] Task 7: 批量绑定契约改为 resources 对象列表，日志展示名拼接、resource_display_info 落库（commit 29a590ec）
- [x] 环境配置：6 个操作级菜单创建 + URL 挂载（write_log=1）+ 角色授权 + 旧菜单 URL 去重（BETA 已完成并核验）
- [ ] 前端配套：batch-bind-resources 调用方改传 resources 对象列表（openlibing-web 仓，另行安排）
- [ ] 前端配套：复制来源 tooltip 与 toast 文案中性化（openlibing-web 仓，另行安排）
