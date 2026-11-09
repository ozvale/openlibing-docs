# tasks.md — oneway-acl-add

- [x] 1. `service/network_isolation.py` 新增 `add_oneway_acl_in_core_switcher`：参数校验、回读快照幂等检查、ID 分配、单次 SSH 下发、回读校验
- [x] 2. `hidevlab_blue_service.py` 新增路由 `POST /switcher/core/cross/oneway/add`（ip_list 长度校验、switch_ip 选择目标交换机、日志脱敏）并补充 import
- [x] 3. 语法检查（python -m py_compile）
- [x] 4. 提交 commit
- [x] 5. 输出接口文档
- [ ] 6. 用户自测验证（重复调用幂等、switch_ip 切换、回读校验）
