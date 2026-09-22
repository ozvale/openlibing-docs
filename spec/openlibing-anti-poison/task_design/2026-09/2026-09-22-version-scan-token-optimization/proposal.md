# 需求提案：防投毒版本扫描 token 改为各社区项目 token

## 需求背景

openlibing-anti-poison 版本级防投毒扫描执行时需要调用 GitCode/Gitee 平台接口（下载 PR 增量文件、创建检查等），此前统一使用**配置中心**（Apollo）中的全局平台账号 token。该方案存在两个问题：

1. **token 粒度粗**：所有项目共用一个平台账号 token，单个项目 token 失效或权限变更会影响全部项目的扫描；且无法满足按项目隔离权限的诉求。
2. **token 泄露面大**：配置中心 token 明文参与扫描流程，任何项目使用同一凭证，泄露后波及面广。

需求来源 issue：**防投毒版本扫描的替换成各个社区的 token，不再使用配置中心的 token**，即扫描时应优先使用**项目公共账号表**（按 projectId 关联）中配置的 token，配置中心 token 仅作为降级兜底。

## 目标

1. **项目 token 优先**：`getPlatformPassworandUserName` 增加 `projectId` 入参，按 projectId 从项目公共账号表查询 token，优先使用项目 token。
2. **配置中心降级兜底**：项目 token 为空或解密失败时，降级使用平台配置 token，保证老项目（未配置项目 token）扫描不受影响。
3. **扫描目录与空结果容错**：扫描前确保报告目录存在，避免目录缺失导致扫描失败；扫描结果为空时抛出明确异常而非 NPE。

## 验收标准

### 功能验收

| 功能点          | 验收标准                                                                         |
| --------------- | -------------------------------------------------------------------------------- |
| 项目 token 优先 | 项目公共账号表存在该平台 token 时，使用项目 token（解密后）                      |
| 降级兜底        | 项目 token 为空/解密失败时，降级使用平台配置 token，并记录 warn 日志             |
| 全空返回 null   | 平台配置 token 也缺失/解密失败时返回 null，调用方报「get platformInfo error」    |
| 密码解密容错    | 平台密码解密失败返回 null，不再抛未捕获异常                                      |
| 目录自动创建    | 扫描前 `Files.createDirectories` 创建扫描结果目录，目录缺失不导致扫描失败        |
| 空结果异常      | 扫描结果为空时抛 `IOException("scan result is missing or empty...")`，不产生 NPE |

### 质量验收

| 质量指标 | 目标                                                                                 |
| -------- | ------------------------------------------------------------------------------------ |
| 代码规范 | 通过 checkstyle 检查                                                                 |
| 兼容性   | 未配置项目 token 的老项目行为与升级前一致（降级走配置中心）                          |
| 日志规范 | 解密失败/降级均记录 error/warn 日志，含 projectId 与 platform，**不打印 token 明文** |

## 影响范围

- **业务仓**：`openlibing-anti-poison`
- **核心改动文件**：`AntiServiceImpl.java`（token 获取逻辑重构 + 扫描容错）
- **关联改动**：`.gitignore`（忽略扫描引擎运行时产物目录 `tools/softwareFile/`）、`pom.xml`（openlibing-common SDK 1.0.20.4 → 1.0.21.0）、`PoisonPRController.java`（清理无用 javadoc @throws）
- **接口**：无外部接口契约变化，均为内部能力增强
- **数据**：仅读取项目公共账号表，无 schema 变更

## 关联 Issue

- [https://gitcode.com/openlibing/openlibing-anti-poison/issues/29](https://gitcode.com/openlibing/openlibing-anti-poison/issues/29)
