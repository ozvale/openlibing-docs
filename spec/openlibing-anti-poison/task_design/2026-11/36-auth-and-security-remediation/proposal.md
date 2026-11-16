# 36-auth-and-security-remediation — 需求背景与验收标准

## 背景

项目未引入 spring-boot-starter-security，全站无统一身份认证，userId 直接取自客户端请求参数可任意伪造冒充 admin，违反红线 B-01（越权/未授权访问）与 B-02（认证须服务端完成）。在此基础上一并排查出命令注入、SSRF、凭据保护（红线 A2-01/A2-05）、SQL 注入隐患、DoS、传输安全等共 16 项问题。

关联业务 Issue：openlibing/openlibing-anti-poison#36

## 需求范围

- P0 红线：引入服务端统一鉴权，userId 服务端化；命令执行去 sh -c 拼接；token 禁入命令行/URL；版本库移除公网 Nacos 地址
- P1 高危：出网请求协议白名单 + 内网 IP 校验；关闭 shutdown 端点；token 改 Header 传递；RequestMapping 限定 HTTP 方法
- P2 中低：tableName 白名单、MongoDB TLS 校验、安全响应头、POI 公式注入转义、fastjson2 配置更正、依赖版本锁定、密钥管理评估

## 验收标准

- [x] 16 项问题闭环（含红线 B-01/B-02、A2-01/A2-05），已随业务 PR openlibing/openlibing-anti-poison#139 交付（safe_202611 分支）

## 风险

鉴权接入影响全部接口，需与前端/网关联动回归。
