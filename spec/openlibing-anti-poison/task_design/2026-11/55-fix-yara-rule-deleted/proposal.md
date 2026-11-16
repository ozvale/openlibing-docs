# 55-fix-yara-rule-deleted — 需求背景与验收标准

## 背景

提交 d44d927（本意删除废弃接口）误删了 `tools/SoftwareSupplyChainSecurity-v1/java_scan/` 下 3 个 YARA 编译规则文件（download_exec、info_leak、runtime_reverse_shell 的 .yar.cp），而 `java_scan.yaml` 与 `all_rules.yaml` 仍引用这些规则。扫描器 `_get_yara_rule` 在规则缺失时返回 None，`run_jobs` 静默跳过（fail-open），导致 Java 仓库 download_exec（下载执行木马）与 info_leak（敏感信息外传）检测 100% 静默失效，投毒样本可无告警通过版本扫描与 PR 门禁。`.yar` 源文件从未入库，恢复需依赖发布制品/备份。Argus 高危漏洞（CWE-16）。

关联业务 Issue：openlibing/openlibing-anti-poison#55

## 需求范围

- 从发布制品/备份恢复 java_scan 下 download_exec、info_leak（及 runtime_reverse_shell）YARA 规则文件
- 修复 yara_scan.py 的 fail-open 行为：规则文件缺失时显式报错/告警，不再静默跳过
- 排查 password_scan 等目录的同类悬挂引用（all_rules.yaml、ruleYaml/common.yaml 引用的规则缺失问题）

## 验收标准

- [ ] java_scan 规则文件恢复，配置引用与实际规则集合一致（issue 仍 open，待验收）
- [ ] 规则缺失时扫描入口不再静默放行（fail-closed 或明确告警）

## 风险

高危防护盲点；恢复的规则文件需与历史编译产物核对一致性，防止引入被篡改规则。
