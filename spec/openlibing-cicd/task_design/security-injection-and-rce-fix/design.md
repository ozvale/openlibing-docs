# security-injection-and-rce-fix — 技术设计

## 漏洞定位

**Sink**：`PipelineFailEmailConsumer.java:511-512`

```java
// 修复前
Yaml yaml = new Yaml();
Map<String, Object> root = yaml.load(yamlContent);
```

**Source**：`PipelineFailEmailConsumer.java:327-328`

```java
// yamlContent 来自仓库文件 API
String yamlContent = repoFileService.readFileContent(fileReq);
```

`fileReq.filePath` 固定为常量 `NOTIFY_FILE_PATH = ".notification.yaml"`，但文件内容完全由 GitCode/Gitee 仓库控制。

## 攻击链

```
RabbitMQ 消息 → handlePipelineFailEmail
  → 解析 messageJson
  → DB 查询 pipelineInfo（pipelineId/runId 来自不可信消息）
  → resolveRecipients(pipelineInfo)
    → extractRepoUrl() / resolveSourceInfo() / extractBranch()
    → repoFileService.readFileContent(.notification.yaml)
  → parseRecipients(yamlContent)          ← Sink：new Yaml().load(yamlContent)
  → 触发 CVE-2022-1471 → RCE
```

## 修复方案

### 方案对比

| 方案 | 改动量 | 风险 | 推荐度 |
|---|---|---|---|
| SafeConstructor | 3 行 | 低，标准做法 | ⭐⭐⭐ 推荐 |
| LoaderOptions + TagInspector 白名单 | 5 行 | 低 | ⭐⭐ 更强 |
| 升级 SnakeYAML ≥ 2.0 | 依赖变更 | 传递依赖版本冲突 | ⭐ 不推荐 |

采用 **方案 1：SafeConstructor**（最小改动 + 修复彻底）。

### 修复代码

```java
// 修复后
LoaderOptions loaderOptions = new LoaderOptions();
Yaml yaml = new Yaml(new SafeConstructor(loaderOptions), loaderOptions);
Map<String, Object> root = yaml.load(yamlContent);
```

### 关键决策

1. **不升级 SnakeYAML 版本**：避免 Spring Boot 3.4.4 / spring-amqp 传递依赖版本冲突。
2. **不使用 TagInspector 白名单**：业务只需解析 `Map<String, Object>`，SafeConstructor 已足够。
3. **保留 catch YAMLException 逻辑**：YAMLException 现在仅在 YAML 语法错误时抛出（SafeConstructor 拒绝 Tag 时抛 YAMLException，已被 catch 吞掉，返回空列表）。

## 测试设计

### 7 个测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| 1 | 正常 YAML（含 notifications 块 + pipeline_fail + emails 列表） | 返回邮箱列表 |
| 2 | 恶意 YAML（`!!javax.script.ScriptEngineManager []`） | 抛异常（被 catch 吞掉返回空列表） |
| 3 | 恶意 YAML（`!!java.net.URLClassLoader []`） | 抛异常 |
| 4 | null / 空字符串 | 返回空列表 |
| 5 | 非法 YAML 语法 | 返回空列表（不抛异常） |
| 6 | 无 `notifications` 键 | 返回空列表 |
| 7 | notifications 块不含 `pipeline_fail` 类型 | 返回空列表 |

### 测试方式

通过 `ReflectionTestUtils.invokeMethod` 反射调用 `private` 方法 `parseRecipients`，避免将方法暴露为 package-private 影响封装。

## 影响范围

| 文件 | 行数变化 |
|---|---|
| `PipelineFailEmailConsumer.java` | +3 / -1（import +2、代码 +1 / -1） |
| `PipelineFailEmailConsumerTest.java`（新建） | +111 / -0 |

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| SafeConstructor 拒绝过多类型导致正常 YAML 解析失败 | 测试用例 1 已覆盖正常 YAML 路径 |
| 业务依赖其他 Tag（如自定义 Java Bean） | 本场景业务仅使用 Map/List/String，SafeConstructor 完全满足 |
| 传递依赖引入更低版本 SnakeYAML | maven-enforcer-plugin 可加，但本次仅做最小修复 |

## 跨仓影响

- **业务仓 openlibing-cicd**：仅修改 1 个文件 + 新增 1 个测试
- **docs 仓 openlibing-docs**：本 PR 提交
- **其他仓**：无影响
