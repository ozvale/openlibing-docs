# 55-fix-yara-rule-deleted — 实现任务

## 进度: 0/4 complete

- [ ] Task 1: 从发布制品/备份恢复 java_scan/{download_exec,info_leak,runtime_reverse_shell} 规则文件并入库
- [ ] Task 2: 校验恢复的规则与 java_scan.yaml、all_rules.yaml 引用一致（静态核验脚本通过）
- [ ] Task 3: 修改 yara_scan.py，规则缺失时 fail-closed（报错/告警而非静默 continue）
- [ ] Task 4: 排查并修复 password_scan 等同类悬挂引用，增加规则存在性门禁
