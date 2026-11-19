# EDEVOPS 设计文档 — sbom-detail-link-output

## 需求名称

【openlibing-sbom】sbom-action返回产物详情地址

## 需求背景

sbom-action 插件输出仅有任务 ID，使用者无法从流水线直接跳转 SBOM 产物详情，也无法感知本次上报的包规模。需要在输出结果中展示产物详情地址与包初步分析（包数量、关系数量），展示形态对齐 code-metrics-action 的任务结果面板。

## 领域模型

| 实体/概念                          | 说明                                             | 本次变化                                              |
| ---------------------------------- | ------------------------------------------------ | ----------------------------------------------------- |
| sbom Product                       | SBOM 产品（名称唯一），productType == 平台项目名 | 无 schema 变化                                        |
| 平台项目（framework project_info） | 项目主数据，projectId 为权威 id                  | 零改动，被 sbom-web 只读消费                          |
| coderepo ProjectNameVo             | gitUrl 反查候选（projectId, projectName）        | 零改动，仅用于 productType 裁决（现有）               |
| PublishSbomResponse                | addAndPublishProduct 响应                        | 新增 detailLink 字段（向后兼容，纯增量）              |
| 插件 outputs                       | task-id / sbom-file                              | 新增 detail-link / package-count / relationship-count |

## 数据流与契约变化

```
addAndPublishProduct 响应契约（APIG 外部接口）：
  { success: true, taskId: UUID }  →  { success: true, taskId: UUID, detailLink?: string }
  纯增量字段，旧调用方不受影响。
```

新依赖调用（sbom-web → framework，内网 feign）：
`GET /internal-server/get-project?projectName=<productType>&pageNum=1&pageSize=1`，精确匹配，响应 `{total, data:[{projectId, projectName, ...}]}`。

## 安全设计

| 维度 | 评估                                                                                              |
| ---- | ------------------------------------------------------------------------------------------------- |
| 鉴权 | 机机接口 `/internal-server` 同现有鉴权域，无新增暴露面；detailLink 落地页受平台现有登录/权限控制  |
| 输入 | productName 反查前经现有 validateProductType 白名单校验；URL 拼接前 URLEncoder.encode，防参数注入 |
| 注入 | 插件侧 detailLink 过 sanitize（剥 CR/LF），防流水线日志/面板换行注入（对齐 code-metrics Ref #64） |
| 凭证 | 无新增凭证；域名走既有 Nacos 配置项                                                               |

## 可观测性

- projectId 反查失败：ERROR 日志（含 productType 与原因），响应 errorInfo 透出
- domain 未配置：WARN 日志提示配置项缺失
- 插件：detailLink 缺失时不输出链接行，保留概览组可观测

## 部署与发布影响

| 项       | 说明                                                                                                                                                           |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 配置     | test/prod Nacos 需配置 `sbom.service.website.domain=https://www.openlibing.com`（sbom-web 既有配置项，若未配置则 detailLink=null，功能降级但不影响上报主流程） |
| 数据库   | 无                                                                                                                                                             |
| 服务依赖 | sbom-web → framework 新增只读调用（内网），framework 零改动零重启                                                                                              |
| 发布顺序 | sbom-web 先发（响应新增字段），插件后发（消费新字段）；顺序颠倒时插件仅退化为无链接输出，不报错                                                                |
| 前端     | 与后端解耦，可独立发布；未发时 detailLink 落地列表页不自动定位（打开后手动搜索）                                                                               |

## 回滚方案

- 后端：回滚 sbom-web 即恢复原响应（detailLink 字段消失，插件退化为无链接输出）
- 插件：回滚插件版本即可
- 前端：回滚 web 部署即可
- 各仓独立回滚，无数据迁移，无跨仓强耦合

## 兼容性矩阵

| 后端新 \ 插件旧                   | 后端新 \ 插件新 | 后端旧 \ 插件新                                  |
| --------------------------------- | --------------- | ------------------------------------------------ |
| detailLink 被忽略，仅 taskId 输出 | 完整功能        | 插件读不到 detailLink → 不输出链接行，概览组正常 |
