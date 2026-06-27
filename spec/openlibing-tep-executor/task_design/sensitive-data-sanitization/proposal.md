# sensitive-data-sanitization

## 需求背景

在测试执行过程中，日志打印会包含敏感信息（如密码、token、API key 等），导致敏感数据泄露风险。具体问题包括：

1. **HTTP 响应日志泄露**：`send_cmd/send_requets` 函数打印 HTTP 响应内容时，可能包含 `access_token`、`password` 等敏感字段
2. **Ansible 密码明文写入**：`unified.py` 中使用 `os.system` 将密码通过 shell 命令写入文件，存在进程列表泄露风险
3. **kwargs 日志泄露**：`test_set.py` 中打印 kwargs 参数可能包含敏感配置
4. **正则匹配缺陷**：原有正则表达式无法正确处理 JSON 格式和包含空格的敏感值

## 功能描述

### 做什么

1. 实现 `_sanitize_sensitive_data` 函数，支持多种数据类型脱敏
2. 实现 `_sanitize_sensitive_data_str` 辅助函数，处理字符串类型的正则匹配
3. 修复 Ansible hosts 文件写入方式，使用 Python 文件操作替代 `os.system`
4. 添加完整的单元测试覆盖

### 不做什么

- 不修改现有日志系统架构
- 不处理文件内容中的敏感信息（仅处理日志打印）
- 不修改第三方库的日志行为

## 验收标准

- [ ] HTTP 响应日志中的敏感字段（password, token, api_key, access_key 等）被替换为 "***"
- [ ] Ansible hosts 文件使用安全方式写入，密码不通过 shell 命令传递
- [ ] kwargs 日志中的敏感数据被脱敏
- [ ] 支持 dict/list/str/tuple/set 等多种数据类型
- [ ] 支持 JSON 格式字符串解析和脱敏
- [ ] 正则表达式正确处理包含空格的敏感值
- [ ] 单元测试覆盖所有边界场景

## 影响范围

| 模块 | 影响程度 |
|------|---------|
| `cte/utils.py` | 核心修改（新增脱敏函数） |
| `unified.py` | 安全修复（Ansible 文件写入） |
| `test_set.py` | 日志脱敏调用 |
| `tests/test_sanitize_sensitive_data.py` | 新增测试文件 |