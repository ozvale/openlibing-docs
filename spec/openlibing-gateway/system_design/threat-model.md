# 威胁模型：gateway 灰度染色（gray-release）

## 资产清单

| 资产                             | 分类        | 责任域                | 备注                     |
| -------------------------------- | ----------- | --------------------- | ------------------------ |
| 灰度配置（开关/比例/白名单）     | 内部        | nacos（gateway 消费） | 篡改可导致全量流量进灰度 |
| X-Release-Track header           | 内部        | gateway 注入          | 决定下游实例路由         |
| 用户 ID                          | 敏感（PII） | gateway JWT           | 白名单匹配依据           |
| 下游实例拓扑（metadata.version） | 内部        | nacos discovery       | 灰度/稳定实例标识        |

## 信任边界

- 浏览器/插件 → gateway：公网，JWT + CSRF（既有 AuthFilter），不信任任何客户端 header
- gateway → 下游服务：内网，信任 gateway 注入的 X-Release-Track
- gateway → nacos：CSE 托管，secure 连接，配置变更由运维审计

## 数据流

1. 请求带 JWT cookie → AuthFilter 校验并注入 `userId` 查询参数 → GrayReleaseFilter 判定 track → 注入 header → lb:// 路由按版本选实例
2. nacos 配置变更 → RefreshEvent → GrayReleaseConfig 动态生效

## STRIDE 评估

| 资产                   | S   | T   | R   | I   | D   | E   | 缓解措施                                                                                      |
| ---------------------- | --- | --- | --- | --- | --- | --- | --------------------------------------------------------------------------------------------- |
| X-Release-Track header | 高  | 高  | 低  | 低  | 低  | 中  | 入站 header 强制覆盖，客户端无法自选灰度；下游仅信任网关注入                                  |
| 灰度配置               | 中  | 中  | 低  | 低  | 低  | 高  | nacos 鉴权 + 变更审计（CSE）；ratio 钳位 [0,100]；开关默认 false（fail-safe）                 |
| 白名单                 | 低  | 中  | 低  | 低  | 低  | 中  | 懒解析缓存，脏数据仅导致不命中；异常兜底 stable                                               |
| 染色链路可用性         | 低  | 低  | 低  | 低  | 高  | 低  | 每请求仅 O(1) 判定（Set.contains + 随机数），无阻塞调用；无匹配实例时回退全部实例，不产生 503 |
| 用户 ID                | 低  | 低  | 低  | 中  | 低  | 低  | 日志仅 debug 级且脱敏（前 4 位）；不落结构化审计日志                                          |

## 关键决策

- 染色判定只在 gateway 完成（唯一染色入口），下游不二次判定 → 攻击面收敛到一处
- Fail-safe 方向：任何异常/配置缺失 → stable（回滚态），宁可全量稳定也不误入灰度
- 可用性优先于路由严格性：无版本匹配实例时回退全部实例（取舍：灰度未部署时灰度流量会打到稳定实例，可接受）
