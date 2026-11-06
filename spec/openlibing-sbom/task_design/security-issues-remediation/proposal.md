# openlibing-sbom 安全 Issue 集中整改（spec）

> 关联 Issue：openlibing-sbom #170 / #158 / #92 / #90 / #89 / #100（安全标签批次），关联需求 openlibing-coderepo#401
> 分支：`fix-security-issue`（业务仓）→ 已合入 `sbom-dev`
> 模式：Light（多点小改、单仓、无接口/数据模型变化）

## 一、需求背景

openlibing-sbom 批量安全扫描（SENINFO / SpotBugs+findsecbugs / SecBinaryCheck / bandit）产出一批安全 Issue。本需求对其中 6 个主 Issue 做集中定性 + 整改，并对整改过程中暴露的工具链问题（pre-commit 门禁、依赖治理副作用）一并修复。

## 二、范围

| Issue | 问题                                     | 定性                                                                   | 处理                       |
| ----- | ---------------------------------------- | ---------------------------------------------------------------------- | -------------------------- |
| #170  | 导出失败回执泄露异常原文（内网信息泄露） | 真问题                                                                 | 修代码                     |
| #158  | 全局 1GB 出站响应解码缓冲（内存放大）    | 真问题                                                                 | 修代码                     |
| #92   | PATH_TRAVERSAL_IN 解压路径穿越           | 告警代码已删                                                           | 无需整改，评论定性         |
| #90   | SecBinaryCheck 漏洞依赖清单              | 部分真问题                                                             | 依赖治理                   |
| #89   | SENINFO 公网地址硬编码（78 项命中）      | 混合：A 类运行时配置（16 项）+ B 类代码常量（1 项）+ C 类噪音（61 项） | A/B 修、C 定性归档         |
| #100  | 弱口令 + uvp 测试地址硬编码              | 地址：真问题；口令：环境侧                                             | 修地址外置，口令环境侧改密 |

## 三、验收标准

1. 导出失败回执不透传 `IOException`/未知 `RuntimeException` 的 `e.getMessage()`；业务异常（SbomRuntimeException）文案保留；新增单测覆盖两条收敛路径。
2. 全仓不存在游离于配置治理之外的 1GB 级出站响应解码上限，统一走 `spring.codec.max-in-memory-size`（256MB，经评估的业务决策）配置；大文件下载流式化、出站并发限流等残余 DoS 面登记为遗留待办，不在本项闭环范围。
3. 生产源码（`src/main`）中不再含明文运行时域名；`@Value` 注入均可由 Nacos 按环境覆盖；缺省空值不影响应用启动。验证：beta/gamma 已随镜像实测通过（17/17）；启动期 fail-fast 域名非空校验未实施，登记为遗留待办。
4. 依赖树中无 sshd-core；关键 CVE 组件升级至修复版本；升级前后依赖树对比无意外增减。
5. pre-commit（SpotBugs+findsecbugs+bandit 等 14 钩子）全绿；CRLF/COMMAND_INJECTION 误报以注解+exclude 基线精确豁免，白名单检测保持在线。
6. 各 Issue 评论区发布整改/定性记录。

## 四、非目标

- #105（生产 Swagger UI 收敛）：swagger url 环境差异项单独处理。
- #149（H 级：CI 不可信 PR 检出与凭证注入）：挂起，另行立项。
- #53（LogSanitizer 残留）：LogSanitizer 已删除，待确认关闭。
- CVE 子 Issue（#77/#70/#69/#66/#59/#48/#33/#19）：随 #90 结论归档关闭。
