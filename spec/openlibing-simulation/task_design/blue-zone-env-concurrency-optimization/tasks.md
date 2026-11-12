# 蓝区环境创建并发优化 — 实现任务

## 进度: 8/9 complete

- [x] Task 1: 任务目录按 `{engineId}/{taskId}/` 隔离，脚本/配置分别落 `install/{taskId}/script|conf/`
- [x] Task 2: 端口分配改为 `qemu_port_ip_{ip}` 锁内完成扫描与分配，含等待重试
- [x] Task 3: 镜像加载、引擎/qcow 文件传输按 `qemu_image_{ip}_{version}` / `qemu_file_{ip}_{资源id}` 串行
- [x] Task 4: 关闭任务时增加禁止目录、canonical path 前缀、路径深度三重校验
- [x] Task 5: `t_server_using.config_path` changeset + 历史任务视图脏数据清理 changeset
- [x] Task 6: `QemuTaskServiceImplTest` 覆盖新增锁与目录隔离逻辑
- [x] Task 7: 回退子需求 2（运维指标）：移除 `micrometer-registry-prometheus` 依赖、`management.*` 配置，同步 `AGENTS.md`
- [x] Task 8: `mvn clean test` 验证通过（427 个用例，0 失败 0 错误），并修复原有单测漂移
- [ ] Task 9: 创建业务 PR（全量 `fork_1106` → `master`，关联 #65，打 `ai-assisted`）

> 说明：Task 1-6 的代码已在 `fork_1106` 分支完成（`91dfcaf..4bca5c6` 及 `9682507`/`921a7e9`），本次不再重写，仅做验证与指标方案回退。
