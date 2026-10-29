# Tasks：【openLiBing】ICSL安全送检排查及整改（openlibing-coderepo 侧）

> 图例：`[x]` 已合入；`[ ]` 在途/待办。PR 链接均为 openlibing/openlibing-coderepo。

## 阶段一：凭据与敏感数据全链路（L4）

- [x] #163 SENINFO 公网地址入仓 → API 域名配置化、清理 `@Value` 内联默认值（[!209](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/209)，`4a507220`）
- [x] #164 Gitee accessToken 走 URL 查询参数 → 改请求头 + URL 日志脱敏（[!211](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/211)，`22df481b`）
- [x] #165 PR 同步明文令牌入 MQ → MQS 去明文、改传引用（[!231](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/231)，`6f77f3bb`）
- [x] #182 三平台 API 客户端 URL 拼接未编码 → builder 分段编码（[!227](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/227)，`59626d65`）
- [x] #185 MQ 消费者日志整包输出 → 脱敏器关键字包含匹配（[!252](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/252)，`b2c28bc4`）
- [x] #187 Redis 令牌缓存键 hashCode → SHA-256 派生（[!261](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/261)，`44366c44`）
- [x] #194 Token 变更日志含 token → 异常栈脱敏 + 截断报文遮盖（[!263](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/263)，`22924a82`）
- [x] #224 异常消息原样回显 → 固定文案映射（[!251](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/251)，`6f173390`）
- [x] #245 webhook 签名/令牌头入 MQ → headerMap 剔除凭据头（[!269](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/269)，`76353ab5`）
- [ ] #192 SMTP 未配 TLS → 强制 STARTTLS（[!253](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/253)，在途；上线前需运维确认中继）

## 阶段二：鉴权与越权（L3）

- [x] #173 UT 覆盖率文件明细接口缺失授权校验 → 补归属校验（[!221](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/221)，`febb632b`）
- [x] #177 分支/平台所有者查询端点缺失归属校验 → 补归属校验（[!224](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/224)，`f386484f`）
- [x] #179 写型同步复用读菜单鉴权 → 切换写菜单 URL 锚点（[!225](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/225)，`582c00bd`）

## 阶段三：注入、输入校验与日志可信（L2）

- [x] #180 用户可控参数未过滤 CRLF → 分层防线（[!226](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/226)，`37adcfb4`；同批 !212 对应缺陷 #167，非本安全清单项）
- [x] #239 仓库地址白名单子串匹配可绕过 → host 精确匹配（[!268](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/268)，`a2b422ed`）
- [x] #242 Excel 导出公式注入 → 单元格前缀转义（[!267](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/267)，`281e0156`）
- [x] #263 Webhook 出站 URL 路径段注入 → `WebhookUrlUtil` 分段编码 + 段级白名单 + 录入入口收紧（[!274](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/274)，`399545e3`）
- [x] #246 XFF 可伪造操作者 IP → 删除死代码 `getUserIpAddress`，IP 采集移交 common `OperationLogClientIp`（[!271](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/271)，`1674d5ad`）

## 阶段四：拒绝服务与资源上限（L5）

- [x] #172 OBS 中转链路无大小限制 → 大小上限 + 计数流兜底 + 流式解析（[!220](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/220)，`6ffc6d97`）
- [x] #210 pageSize 无上限/全量加载 → 5 链路收口 + SQL 下推（[!256](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/256)，`9dffb16f`）
- [x] #211 大字段长度无校验 → `PayloadSizeConstants` 字节预算（[!266](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/266)，`1883fa0d`）
- [x] #223 limit 拼接逻辑反向 → LIMIT 条件修正为 `pageSize >= 1`（[!254](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/254)，`c60b0c2d`）
- [x] #226 分页乘法 int 溢出 → `PaginationUtil` long 计算（[!255](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/255)，`f8bd858b`）
- [x] #184 逐请求新建 OkHttpClient → 单例复用 + 死代码清理（[!262](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/262)，`f51e89d2`）

## 阶段五：Webhook 安全基线与幂等（L6）

- [x] #169 Webhook 签名无时间戳/重放防护 → 投递 ID 两层幂等（[!217](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/217)，`94e60582`）
- [x] #181 HMAC 非常量时间比较 → `MessageDigest.isEqual`（[!217](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/217)）
- [x] #176 去重锁 Redis 异常 fail-open → 降级本地锁（[!223](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/223)，`6dac5a2d`）

## 阶段六：登记接受项（跟踪）

- [ ] #174 MQ 消费者重试耗尽死信不可达（需 MQ 侧能力，登记接受）
- [ ] #175 pre-commit CI 检出 fork PR 不可信代码（转 CI 仓）
- [ ] #178 Docker 构建 JRE 动态下载未固定版本（转构建侧）
- [ ] #225 swagger 生产暴露（**加固项（未关闭）**；补偿控制：端点经网关转发且菜单仅 admin/platform_operater 可访问；加固动作 prod 关闭 springdoc 端点，确认责任方：环境侧（运维），随 11 月送检窗口闭合）
- [ ] #252 不安全协议/加密套件（Mongo 主机名校验、非 prod MQ 明文；登记接受，确认责任方：环境侧（运维），随 11 月送检窗口确认 TLS 能力后评估）

## 阶段七：归档与送检材料

- [x] issue 评论区补齐修改方案（26 项已合并全部有评论）
- [x] 各 PR 描述关联 FE 需求 openlibing-codecheck#372
- [x] spec 归档到 openlibing-docs（proposal / design / tasks / archive）
- [ ] 送检材料汇总（本 spec + 威胁分析报告 + 复扫结论）打包提交
