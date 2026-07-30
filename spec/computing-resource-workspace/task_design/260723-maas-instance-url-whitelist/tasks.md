# 260723-maas-instance-url-whitelist - Tasks

## Phase 1：主机白名单校验

### Task 1: 新增 InstanceUrlWhitelistValidator 组件

- [x] 1.1 新建 `business/service/maas/InstanceUrlWhitelistValidator.java`（@Component）
- [x] 1.2 `@Value("${maas.instance.url-whitelist:}")` 注入，字段标记 `volatile`
- [x] 1.3 实现 `validate(String url, String healthCheckUrl, String metricsUrl)` 返回 `DataResult<Void>`
- [x] 1.4 解析白名单：split 逗号 + trim + 小写 + 过滤空 -> `Set<String>`；空集直接放行
- [x] 1.5 每个非空 URL 用 `java.net.URI(url).getHost()` 取 host 小写；host 为空或不在 Set 内 -> `DataResult.fail(400, "XX地址的域名 YY 不在允许访问的白名单内，请联系管理员")`
- [x] 1.6 前缀（http/https）校验仍由 `ModelInstanceServiceImpl.validateUrlFields` 负责，validator 只做白名单

### Task 2: ModelInstanceServiceImpl 接入

- [x] 2.1 注入 `InstanceUrlWhitelistValidator`
- [x] 2.2 `validateUrlFields` 末尾（前缀校验通过后）调用 `validator.validate(url, healthCheckUrl, metricsUrl)`，失败直接返回

## Phase 2：存量数据清理

### Task 3: maas-tables.xml 新增清理 changeSet

- [x] 3.1 新增 `20260723-017-purge-model-instance-data`，`<delete>` 清空 `workspace_model_instance` 和 `workspace_model_instance_health_history`
- [x] 3.2 加 `preConditions`（两表 `tableExists`，`onFail=MARK_RAN`）
- [x] 3.3 comment 注明「仅清数据不删表」

> 已在 design 阶段落地。

## Phase 3：测试与验证

### Task 4: 单元测试 InstanceUrlWhitelistValidatorTest

- [x] 4.1 精确域名命中 / 未命中
- [x] 4.2 精确 IP 命中 / 未命中
- [x] 4.3 空白名单 = 放行（不校验）
- [x] 4.4 host 异常（URL 解析为 null）= 拒绝
- [x] 4.5 大小写不敏感（host 与条目大小写不一致仍命中）
- [x] 4.6 三个地址分别校验，任一不在白名单即失败
- [x] 4.7 热刷新行为：修改白名单字段后，下次调用按新值校验（验证「调用时读字段」）

### Task 5: 验证

- [x] 5.1 编译通过：`mvn test-compile -s 全局 settings.xml`（exit 0）
- [x] 5.2 相关测试通过：`InstanceUrlWhitelistValidatorTest`(12) + `ModelInstanceServiceImplTest`(22) 全绿
- [x] 5.3 全量回归：672 tests, 0 failures, BUILD SUCCESS；`ModelInstanceServiceImplTest` 已注入 validator（空白名单 no-op）
