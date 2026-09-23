# openlibing-framework 依赖漏洞修复 — 技术设计

## 方案概述

基于安全扫描结果识别 framework 仓待修复依赖清单，按「直接依赖升级优先 + 传递依赖 `<dependencyManagement>` 锁定兜底」策略修复；API 不兼容依赖同步适配调用代码；回归验证全量测试通过。

## 架构决策

### 决策 1：直接依赖优先升级

**选择**：直接依赖优先升级到无漏洞版本；传递依赖通过 `<dependencyManagement>` 锁定版本兜底。

**原因**：直接依赖升级是根因修复；传递依赖锁定避免上游未及时升级造成的连带漏洞。

### 决策 2：API 不兼容依赖同步适配

**选择**：升级到 API 不兼容版本时同步适配调用代码（如 fastjson 1.x → 2.x，部分 API 签名变更）。

**原因**：避免编译失败；适配遵循既有调用语义，不引入新行为。

### 决策 3：不引入新依赖

**选择**：仅升级/锁定既有依赖，不引入新依赖替代。

**原因**：避免引入新攻击面与新依赖审查成本；保持依赖图稳定。

## 漏洞修复策略示例

```xml
<!-- 直接依赖升级 -->
<dependency>
  <groupId>com.alibaba</groupId>
  <artifactId>fastjson</artifactId>
  <version>2.0.53</version> <!-- 升级至无漏洞版本 -->
</dependency>

<!-- 传递依赖锁定 -->
<dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.yaml</groupId>
      <artifactId>snakeyaml</artifactId>
      <version>2.3</version> <!-- 锁定无漏洞版本 -->
    </dependency>
  </dependencies>
</dependencyManagement>
```

> 具体依赖与版本以上线 `pom.xml` 为准。

## 风险与缓解

| 风险                       | 影响     | 缓解                                                   |
| -------------------------- | -------- | ------------------------------------------------------ |
| API 不兼容导致编译失败     | 阻塞     | 同 PR 内适配调用代码；编译验证                         |
| 升级后行为变化导致测试失败 | 单测失败 | 修复测试预期；保留原有测试覆盖语义                     |
| 上游传递依赖再次引入漏洞   | 漏洞复发 | `<dependencyManagement>` 锁定兜底；CI 安全扫描持续监控 |

## 关联

- 业务 Issue: openlibing/openlibing-framework#106
- 业务 PR: openlibing/openlibing-framework（release_20260923_iter2 分支已合入）
