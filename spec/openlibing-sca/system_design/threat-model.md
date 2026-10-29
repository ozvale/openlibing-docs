# 威胁模型：notice-scan-status-multifilter

## 资产清单

| 资产                                       | 分类 | 责任域          | 备注                 |
| ------------------------------------------ | ---- | --------------- | -------------------- |
| NOTICE 扫描状态（tbl_project_notice_scan） | 内部 | openlibing-sca  | 仅读，无个人敏感信息 |
| SBOM 制品名清单                            | 内部 | openlibing-sbom | 经 internal-api 获取 |
| SBOM internal-api 可用性                   | 内部 | openlibing-sbom | SCA 为消费方         |
| OBS 内部地址（merged_oss_url 等）          | 内部 | openlibing-sca  | 不对外透出           |

## 信任边界

- 前端 → 网关：公网/办公网，网关统一认证（既有，本需求不变更）。
- 网关 → openlibing-sca：内网。
- openlibing-sca → openlibing-sbom internal-api：内网 HTTP，地址由 `${sca.to.sbom.url}` 配置固定，不由请求方指定（无 SSRF 注入面）。
- openlibing-sca → MySQL：内网，MyBatis 参数化。

## 数据流

1. 前端 → SCA：POST body（productType/filters/sortField/sortDir/pageNum/pageSize），纯查询数据，无凭证字段。
2. SCA → SBOM：同构 body 透传至 internal-api；SBOM 服务层对 filters key 做白名单校验。
3. SCA → MySQL：制品名 IN 参数化查询。
4. SCA → 前端：仅 productName/status/statusName 三个字段。

## STRIDE 评估

| 威胁       | 场景                                          | 等级  | 缓解措施                                                                                                                 |
| ---------- | --------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------ |
| S 身份伪造 | 未认证调用本接口                              | 低    | 与同 Controller 既有接口一致由网关认证，SCA 不新增绕过点；内网直连 7979 属既有部署面，不在本需求扩大                     |
| T 篡改     | filters/制品名注入 SQL                        | 低    | Mapper 全参数化（`#{}` + `<foreach>`），无字符串拼接；filters 仅透传 SBOM，其服务层有 key 白名单                         |
| R 抵赖     | 查询行为无审计                                | 低    | 只读、非敏感操作；沿用既有 info 级入参日志（与兄弟接口一致）                                                             |
| I 信息泄露 | 返回 OBS 内部地址 / SBOM 错误详情             | 低-中 | VO 仅 3 字段；Feign 异常统一转为业务失败提示，不透出异常堆栈与内网细节                                                   |
| D 拒绝服务 | 超大 filters 触发超大 IN 查询 / SBOM 全量返回 | 低-中 | productType 前置校验拒绝无效调用；SBOM 白名单限制过滤维度；量级预估千级内（见 design.md §5），万级以上需分批（已知边界） |
| E 越权     | 水平越权读取其他产品状态                      | 低    | 状态数据非敏感、产品维度无属主模型；与既有 /info 接口同等信任级别，本需求不引入新的越权面                                |

## 关键决策

- 不新增 SCA 侧鉴权逻辑：与同 Controller 既有 4 个接口一致，认证由网关承担；如需收紧属平台级横切需求，不在本需求范围。
- SBOM 地址走 `${sca.to.sbom.url}` 服务端配置，请求方无法控制出站目标（无 SSRF）。
- 失败安全：SBOM 调用失败返回业务失败，不降级为无过滤查询、不缓存脏结果。
