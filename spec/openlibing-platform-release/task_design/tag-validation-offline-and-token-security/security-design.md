# 安全设计：tag 校验下线与 token 权限校验增强

## 1. 资产与信任边界

### 资产清单

| 资产                       | 分类 | 存储位置                                            | 本次变更影响                          |
| -------------------------- | ---- | --------------------------------------------------- | ------------------------------------- |
| GitCode access_token       | 机密 | DB 加密存储（`SecurityUtil.decrypt(token, part1)`） | 增强 scope 校验 + 评估轮换            |
| 制品包 commitId            | 敏感 | `ReleaseSoftwareBuildDataEntity`                    | 不再参与 tag 校验，仅保留为构建元数据 |
| tag commitId               | 内部 | GitCode API 返回（不持久化）                        | 不再查询对比                          |
| `tagValidationResult` 字段 | 内部 | `ReleaseReviewVirusScanEntity`                      | **删除**                              |
| `tagValidationDetail` 字段 | 内部 | `ReleaseReviewVirusScanEntity`                      | **删除**                              |

### 信任边界

| 边界                   | 穿越点                    | 鉴权方式               | 本次处理            |
| ---------------------- | ------------------------- | ---------------------- | ------------------- |
| 用户 → API 网关        | HTTP 请求                 | 网关鉴权（现有）       | 不变                |
| API 网关 → 业务服务    | 内网 HTTP                 | 网关透传 userId        | 不变                |
| 业务服务 → GitCode API | HTTPS，token 在 URL query | `validateGitcodeToken` | **增强 scope 校验** |
| DB → 业务服务          | 内网，加密读取            | `SecurityUtil.decrypt` | **评估轮换策略**    |

## 2. 威胁建模（STRIDE）核心发现

详细 STRIDE 表见 [threat-model.md](./threat-model.md)，本节列出需在编码时落实的关键缓解：

| 威胁                         | 严重度 | 缓解措施                                                              | 落实位置               |
| ---------------------------- | ------ | --------------------------------------------------------------------- | ---------------------- |
| Token 在 URL query 泄露      | 高     | 本次不改传输方式（用户未选），但增加 scope 校验确保即使泄露也无写权限 | `validateGitcodeToken` |
| Token 无 scope 显式校验      | 高     | 显式校验 `write_repository` scope，403 时明确报"权限不足"而非"无效"   | `validateGitcodeToken` |
| Token 无轮换机制             | 高     | 输出轮换操作手册，支持泄露后快速吊销                                  | 运维文档 + 配置        |
| Tag 校验下线后失去一致性控制 | 中     | 保留 `createTags` 兜底（tag 已存在时报错）+ SHA256 校验               | `executeVirusScan`     |
| 401/403 错误信息泄露         | 中     | 错误信息已脱敏（不含 token），保持现状                                | `validateGitcodeToken` |

## 3. 认证与授权设计

### 3.1 Token 权限范围校验（核心增强）

**现状**：`validateGitcodeToken` 仅判断 HTTP 200/201 为有效，403 时统一报"权限不足"，
但未**显式校验** token 是否有 `write_repository` scope。一个"有效但无写权限"的 token
在 200 响应时会被放行，到打 tag 时才报错，延迟暴露问题。

**增强设计**：

```java
public void validateGitcodeToken(String accessToken) throws BusinessException {
  // 1. 空值校验（现有，保留）
  if (StringUtils.isBlank(accessToken)) {
    throw new BusinessException("Gitcode访问令牌获取失败", 400);
  }

  // 2. 有效性校验（现有，保留）
  String validateUrl = GITCODE_URL_PREFIX + "user?access_token=" + accessToken;
  // ... 200/201 判有效，401 判无效 ...

  // 3. 【新增】权限范围显式校验
  //    GitCode /user 接口 200 返回体含 scopes 数组，校验是否含 write_repository
  //    若返回体无 scopes 字段（老版本 token），降级为"不校验 scope，仅记警告"
  try {
    JsonObject userJson = new Gson().fromJson(responseString, JsonObject.class);
    if (userJson.has("scopes")) {
      JsonArray scopes = userJson.getAsJsonArray("scopes");
      boolean hasWriteScope = false;
      for (JsonElement scope : scopes) {
        if ("write_repository".equals(scope.getAsString())) {
          hasWriteScope = true;
          break;
        }
      }
      if (!hasWriteScope) {
        throw new BusinessException(
          "Gitcode访问令牌权限范围不足：缺少 write_repository scope，无法创建 tag",
          403);
      }
    }
    // scopes 字段缺失时降级：不阻断，但在日志记 warning（token 可能是老版本）
  } catch (BusinessException e) {
    throw e;
  } catch (Exception e) {
    // scope 解析异常不阻断主流程，仅记日志
    log.warn("Token scope 校验异常，降级为不校验: {}", e.getMessage());
  }
}
```

**选型理由**：

- GitCode `/user` 接口返回体含 `scopes` 数组（GitCode API v5 规范）
- 不额外增加 API 调用，复用现有 `/user` 响应体
- 降级策略：scopes 字段缺失时不阻断，避免老 token 误杀

**替代方案对比**：

| 方案                               | 优点                 | 缺点                         | 是否采纳            |
| ---------------------------------- | -------------------- | ---------------------------- | ------------------- |
| 复用 /user 响应体 scopes 字段      | 零额外调用，实现简单 | 依赖 GitCode API 返回格式    | ✅ 采纳             |
| 单独调 /repos/.../permissions 接口 | 精确到仓库级权限     | 额外 API 调用，需仓库 URL    | ❌ 过度设计         |
| 仅靠 403 错误区分                  | 零改动               | 延迟暴露问题，错误信息不精确 | ❌ 现状，不满足需求 |

### 3.2 Token 加密存储评估（评估，不重构）

**现状双解密路径**：

| 调用点                                         | 解密方式                             | 密钥分量                                   |
| ---------------------------------------------- | ------------------------------------ | ------------------------------------------ |
| 提交评审 `addReleaseReview`                    | `SecurityUtil.decrypt(token, part1)` | `part1` 来自 `@Value("${security.part1}")` |
| 异步打 tag `createTags`                        | `SecurityManagerUtil.decrypt`        | 不同密钥分量                               |
| gitcode Release `handleArtifactGitcodeRelease` | `SecurityUtil.decrypt(token, part1)` | 同提交评审                                 |
| gitee Release `handleArtifactGiteeRelease`     | `SecurityUtil.decrypt(token, part1)` | 同提交评审                                 |

**风险评估**：

| 风险                 | 严重度 | 说明                                                                                                                  |
| -------------------- | ------ | --------------------------------------------------------------------------------------------------------------------- |
| 双解密路径不一致     | 中     | `SecurityUtil` 和 `SecurityManagerUtil` 可能用不同算法/密钥，若 tag 创建用 A 解密但发布用 B 解密，会导致 token 不一致 |
| `part1` 硬编码在配置 | 中     | `@Value("${security.part1}")` 来自 Apollo，Apollo 权限管控是关键防线                                                  |
| 无轮换机制           | 高     | token 一旦泄露，需联系 GitCode 平台手动吊销，无系统化轮换流程                                                         |

**轮换策略建议（文档化，不编码实现）**：

```markdown
# Token 轮换操作手册

## 触发条件

- 定期轮换：每 90 天
- 应急轮换：token 疑似泄露（access log 异常、安全事件）

## 轮换步骤

1. 在 GitCode 平台生成新 token（勾选 write_repository scope）
2. 用新 token 加密：SecurityUtil.encrypt(newToken, part1)
3. 更新 DB 中该仓库的加密 token 字段
4. 运行 validateGitcodeToken(newToken) 验证新 token
5. 旧 token 在 GitCode 平台吊销

## 回滚方案

- DB 保留旧加密 token 备份（加密态），新 token 异常时可回滚
- 回滚后立即在 GitCode 平台吊销新 token
```

**不重构的理由**：用户选"评估"而非重构。双解密路径虽不一致，但各自调用点已稳定运行，
贸然统一改动影响面大。本次仅输出评估报告和轮换手册，后续迭代再统一。

## 4. 输入与输出安全

### 4.1 Tag 校验下线后的输入清理

| 输入                                   | 现状     | 下线后处理                                     |
| -------------------------------------- | -------- | ---------------------------------------------- |
| `tagValidationResult` 参数（前端提交） | 可能传入 | 前端移除该字段后端接口忽略，不报错（向后兼容） |
| `tagValidationDetail` 参数             | 可能传入 | 同上，忽略                                     |
| Tag 名称（发布时 `createTags` 用）     | 保留     | **不变**，仍走现有 tag 创建流程                |

### 4.2 Token 校验错误输出

**保持现状**（用户未要求改）：

| HTTP 状态 | 错误信息                                                                 | 是否脱敏      |
| --------- | ------------------------------------------------------------------------ | ------------- |
| 401       | "Gitcode访问令牌无效或已过期: <GitCode返回的message>"                    | ✅ 不含 token |
| 403       | "Gitcode访问令牌权限不足，请确认已勾选 write_repository 权限: <message>" | ✅ 不含 token |

**约束**：错误信息中的 `errorMessage` 来自 GitCode 响应体，不能包含 token；
日志中只记 `validateResponse.code()` 和脱敏后的 `errorMessage`，**禁止**记 token。

## 5. 数据保护

### 5.1 DB 字段清理

| 表                             | 字段                  | 处理 | Liquibase 变更 |
| ------------------------------ | --------------------- | ---- | -------------- |
| `ReleaseReviewVirusScanEntity` | `tagValidationResult` | 删除 | `dropColumn`   |
| `ReleaseReviewVirusScanEntity` | `tagValidationDetail` | 删除 | `dropColumn`   |

**历史数据处理**：已有数据随字段删除一并清除，不单独迁移（用户要求完全删除）。

### 5.2 Token 加密存储（保持现状 + 评估）

| 维度             | 现状                                   | 评估结论                           |
| ---------------- | -------------------------------------- | ---------------------------------- |
| 加密算法         | `SecurityUtil`（对称加密，AES 或类似） | 算法强度足够，不改                 |
| 密钥分量 `part1` | Apollo 配置 `security.part1`           | 依赖 Apollo 权限管控，不改         |
| 双解密路径       | `SecurityUtil` + `SecurityManagerUtil` | 不一致但不改，输出风险记录         |
| 轮换机制         | 无                                     | **本次输出轮换手册**，后续迭代实现 |

### 5.3 日志脱敏

| 日志内容         | 脱敏要求                                                           | 落实位置                        |
| ---------------- | ------------------------------------------------------------------ | ------------------------------- |
| Token 校验日志   | 禁止记 token 明文，只记 `校验结果 + HTTP code + 脱敏 errorMessage` | `validateGitcodeToken`          |
| Tag 校验下线日志 | 不再产生 tag 校验日志                                              | `executeVirusScan` 删除相关代码 |
| 发布决策日志     | 不变                                                               | `ReleaseDecisionServiceImpl`    |

## 6. 依赖与供应链

本次变更**不引入新依赖**，不涉及第三方库升级。

| 依赖            | 用途                   | 变更                        |
| --------------- | ---------------------- | --------------------------- |
| `okhttp3`       | HTTP 调用 GitCode API  | 不变                        |
| `gson`          | 解析 GitCode 响应 JSON | 不变（新增 scope 解析复用） |
| `commons-lang3` | `StringUtils.isBlank`  | 不变                        |

## 7. 部署与运行时安全

### 7.1 配置管理

| 配置项                        | 来源   | 变更                 |
| ----------------------------- | ------ | -------------------- |
| `security.part1`              | Apollo | 不变（评估，不重构） |
| `openlibing.ci.gitcode.token` | Apollo | 不变                 |
| `openlibing.bot.gitee.token`  | Apollo | 不变                 |

### 7.2 审计日志（最小集合）

| 事件         | 字段                                                                                                             | 保留期  |
| ------------ | ---------------------------------------------------------------------------------------------------------------- | ------- |
| Token 校验   | `timestamp` / `actor(userId)` / `repoUrl` / `result(valid/invalid/scope-insufficient)` / `httpCode` / `sourceIP` | ≥180 天 |
| Tag 校验下线 | `timestamp` / `actor` / `action(offline)` / `reason`                                                             | ≥180 天 |
| Token 轮换   | `timestamp` / `operator` / `repoUrl` / `oldTokenMasked` / `newTokenMasked`                                       | ≥180 天 |

**约束**：

- 所有审计日志写入后只追加不修改
- token 字段脱敏：只留前 4 位 + `***`（如 `G7x3***`）
- 禁止记录请求体/响应体原文

### 7.3 异常告警

| 告警             | 触发条件                                  | 等级          |
| ---------------- | ----------------------------------------- | ------------- |
| Token 失效突增   | 单位时间 401 响应数突增                   | P1（IM 工单） |
| Token 权限不足   | 403 + scope 不足频繁出现                  | P1            |
| Tag 校验下线异常 | 下线后仍有调用 tag 校验代码（死代码残留） | P2（日报）    |

## 8. 失败模式与应急

### 8.1 Fail Secure 策略

| 场景                         | 失败动作                            | 安全状态                                   |
| ---------------------------- | ----------------------------------- | ------------------------------------------ |
| Token scope 校验异常         | 降级为不校验 scope，记 warning 日志 | ⚠️ 降级，不阻断主流程（避免老 token 误杀） |
| Token 解密失败               | 抛 BusinessException，阻断发布      | ✅ 默认拒绝                                |
| GitCode API 超时             | 抛 BusinessException，阻断发布      | ✅ 默认拒绝                                |
| Tag 校验字段删除后旧数据查询 | 字段不存在，MyBatis 返回 null       | ✅ 无异常，向后兼容                        |

### 8.2 应急响应

| 事件                   | 响应步骤                                                                       |
| ---------------------- | ------------------------------------------------------------------------------ |
| Token 泄露             | 1. GitCode 平台吊销 → 2. 按轮换手册生成新 token → 3. 更新 DB → 4. 审计日志记录 |
| Tag 校验下线后发布事故 | 1. 回滚代码到含校验版本 → 2. 评审是否恢复校验 → 3. 若恢复，重新加字段          |

## 9. 验证计划

### 9.1 单元测试

| 测试用例                                                 | 覆盖场景                               | 验证方式                                   |
| -------------------------------------------------------- | -------------------------------------- | ------------------------------------------ |
| `validateGitcodeToken_withWriteScope_success`            | token 有效 + 有 write_repository scope | 返回正常                                   |
| `validateGitcodeToken_withoutWriteScope_throw403`        | token 有效但无 write_repository scope  | 抛 BusinessException，信息含"权限范围不足" |
| `validateGitcodeToken_scopesFieldMissing_degradeNoBlock` | 响应体无 scopes 字段                   | 降级不阻断，记 warning                     |
| `validateGitcodeToken_401_throwInvalid`                  | token 无效                             | 抛 BusinessException，信息含"无效或已过期" |
| `executeVirusScan_tagValidationRemoved`                  | tag 校验逻辑已删除                     | executeVirusScan 不再调用 tag 校验方法     |

### 9.2 集成测试

| 场景                                    | 验证点                                                                 |
| --------------------------------------- | ---------------------------------------------------------------------- |
| 提交评审单（有效 token + write scope）  | 正常提交，token 校验通过                                               |
| 提交评审单（有效 token 无 write scope） | 提交时即报"权限范围不足"，不等到打 tag 才暴露                          |
| 提交评审单（无效 token）                | 报"令牌无效或已过期"                                                   |
| 发布流程（tag 校验下线后）              | executeVirusScan 不再产生 tagValidationResult，发布不因 tag 不匹配阻断 |

### 9.3 事后审查（交由 gitcode-security-check）

| 约束                       | 验证方式                                                       |
| -------------------------- | -------------------------------------------------------------- |
| Token 不在日志明文         | 搜索 access log 和应用日志中 token 正则                        |
| tagValidation 字段彻底清除 | grep 代码库无 `tagValidationResult`/`tagValidationDetail` 引用 |
| scope 校验覆盖所有调用点   | 4 个调用点都走增强后的 `validateGitcodeToken`                  |
| 轮换手册存在               | 文档在 openlibing-docs 可查                                    |

## 10. 归档说明

- 本文档归档到 `openlibing-docs/spec/openlibing-platform-release/task_design/tag-validation-offline-and-token-security/`
- 通过 `spec-openlibing-platform-release-tag-validation-offline-and-token-security` 分支提 PR
- 业务 PR 描述引用本文档时使用 GitCode permalink（commit SHA URL）
- 事后由 `gitcode-security-check` 验证实现是否符合本设计
