# Proposal: sendcmd_interactive 返回值清理

## 背景

pytest-testkit 插件提供交互式 SSH 命令执行函数 `sendcmd_interactive`，当前返回值包含终端的所有原始输出，导致用户难以获取纯净的命令执行结果。

Issue: https://gitcode.com/openlibing/openlibing-pytest-executor/issues/13

## 问题分析

当前 `sendcmd_interactive` 函数使用 Paramiko 的交互式 shell 模式（invoke_shell），会收集所有终端输出，包括：

1. **ANSI 转义序列**：颜色编码、光标控制等（如 `\x1b[0m`、`\x1b[32m`）
2. **命令回显**：用户输入的命令本身会在终端回显
3. **Login Banner**：SSH 登录时显示的系统信息
4. **Prompt 提示符**：Shell 提示符如 `user@host:~#`

这些"多余信息"使得用户需要额外处理才能获取实际的命令输出内容。

## 需求范围

清理 `sendcmd_interactive` 返回值中的多余信息，提供纯净的命令输出。

### 清理目标

- ANSI 转义序列（颜色编码、控制字符）
- 命令回显（用户输入的命令本身）
- Login Banner 信息

### 保留内容

- 命令的实际输出结果
- 必要的换行符和格式

## 验收标准

1. `sendcmd_interactive` 返回值中不再包含 ANSI 转义序列
2. 返回值中不再包含用户输入的命令回显
3. 返回值中不再包含 login banner 信息
4. 保持向后兼容，不影响现有单命令场景
5. 相关测试通过
</-of内容的-cleanu>