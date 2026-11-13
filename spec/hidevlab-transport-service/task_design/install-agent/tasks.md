# install-agent — 实现任务

## 进度: 7/7 complete

- [x] Task 1: 在 `base/config.py` 新增 3 项 Apollo 配置（URL / x86 包名 / arm 包名）
- [x] Task 2: 在 `service/clab_agent.py` 实现 `install_agent` 主函数与 7 个子函数
- [x] Task 3: 适配 PXE 新机 tar 缺失场景（按 OS 自动 apt/dnf 安装）
- [x] Task 4: 给 wget 下载、tar 安装、服务状态检查加重试
- [x] Task 5: 将硬编码的包 URL/包名迁移到 Apollo 配置
- [x] Task 6: 拆分 `install_agent` 为子函数（`_get_host_arch` / `_download_agent_pkg` / `_ensure_tar_available` / `_extract_agent_pkg` / `_write_server_id_ip` / `_start_agent` / `_wait_for_service_active`）
- [x] Task 7: 在 `transport.py` 新增 `POST /install/agent` 路由
