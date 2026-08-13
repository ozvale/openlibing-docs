#  [Agent切换、自动化部署] 测试策略

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/hidevlab-transport-service/issues/66
- **需求名称**: Agent切换、自动化部署
- **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
- **开发责任人**: 张成
- **测试责任人**:刘万里

---

## 2. 测试维度确认

> **操作指南**：请依据需求分析阶段的标签勾选。勾选后，必须在“第 3 节”提供对应的测试用例或方案。

- [x] **功能自检测试**

> - **测试重点：** API 契约验证、业务逻辑分支覆盖、边界值测试。
> - **目的：** 确保功能实现符合设计预期。
> - **触发条件：** 强制执行,**可委托开发测试完成，测试完成验收**。

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

> 参考测试设计方向
>
> - 新增 HTTP 端点 /docker/installAgent：接收 machines（含 ip/username/password/containerNames）和 agentAddr 参数，异步触发多机多容器并发安装 新增宿主机侧安装脚本 script/install_clabagent_host.sh，接收容器名列表和下载地址 容器创建时集成 code-server 安装流程（setup_code_server 调度 + INSTALL_CODE_SERVER 开关 + CODESERVER_SHARE_DIR 配置）
> - 修复 shared_assets 挂载路径，调整用户存储挂载路径
> - 新增 DOCKER_INSTALL_AGENT_CALLBACK_URL 配置项用于安装结果回调

**1. Agent切换、自动化部署**:Agent切换、自动化部署

- **对应task(issueID)链接:** https://gitcode.com/openlibing/hidevlab-transport-service/issues/66
- **预期结果**: /docker/installAgent 端点可触发多机并发安装并回调结果 容器创建时按配置自动安装 code-server agent 安装结果通过回调通知上端


