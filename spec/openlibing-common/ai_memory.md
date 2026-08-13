# openlibing-common AI Memory

本文档保存 `openlibing-common` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-common` 为公共组件 SDK 服务，为 OpenLiBing 平台各微服务提供统一的基础能力，后续系统级职责、工具边界、任务执行链路、安全约束需在 `system_design/` 中逐步补齐。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及 Agent 工具调用、权限、安全边界、外部系统访问时，必须补充设计说明后再实现。
- 需求完成后，必须在 `archive.md` 记录 AI 错误、人工修正和可复用规则。

## 常见 AI 错误与规避

| 错误模式                             | 规避规则                                                                                                                                            | 来源需求         |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| Spotless/CheckStyle import 顺序冲突  | 禁止使用通配符导入（`import java.util.*`），必须显式列出每个类；禁止使用 `import static *`，必须显式列出每个静态成员                                | 命令执行安全组件 |
| IDEA 自动格式化干扰 git 提交         | 提交前必须关闭 IDEA 的 "Optimize imports on the fly" 和 "Actions on Save" 中的自动格式化；正确流程：`mvn spotless:apply` → `git add` → `git commit` | 命令执行安全组件 |
| pre-commit hook 修改文件导致提交失败 | 不要在 hook 运行后检查工作区差异；先运行 `mvn spotless:apply` 格式化，再 `git add` 暂存格式化后的文件，最后 `git commit`                            | 命令执行安全组件 |

## 代码规范

### Import 语句规范

**禁止通配符导入**：

```java
// ❌ 错误
import java.util.*;
import static com.openlibing.common.constants.CmdValidatorConstants.*;

// ✅ 正确
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import static com.openlibing.common.constants.CmdValidatorConstants.BLOCKED_DIRS;
import static com.openlibing.common.constants.CmdValidatorConstants.BLOCKED_ENV_KEYS;
import static com.openlibing.common.constants.CmdValidatorConstants.MAX_WHITELIST;
```

**Import 顺序**（Spotless 要求）：

1. `static` 导入（按包名排序）
2. 空行
3. 第三方库（`com.*`, `org.*`, `lombok` 等，按包名排序）
4. 空行
5. `java.*` 和 `javax.*`（按包名排序）
6. 空行
7. 更多第三方库（如果有）

### 提交流程

**正确流程**：

```bash
# 1. 格式化代码
mvn spotless:apply

# 2. 暂存格式化后的文件
git add <files>

# 3. 提交
git commit -m "..."
```

**错误流程**（会导致反复失败）：

```bash
# ❌ 错误：直接 add 未格式化的文件
git add <files>
git commit -m "..."  # hook 会格式化文件，导致暂存区和工作区不一致
```

### IDEA 配置

**必须关闭的自动格式化选项**：

1. `File` → `Settings` → `Editor` → `General` → `Auto Import`
   - 取消勾选 `Optimize imports on the fly (for current project)`
2. `File` → `Settings` → `Tools` → `Actions on Save`
   - 取消勾选 `Reformat code`
   - 取消勾选 `Optimize imports`

**Import 折叠设置**（避免 IDEA 自动合并为通配符）：

1. `File` → `Settings` → `Editor` → `Code Style` → `Java` → `Imports`
2. `Class count to use import with '*'` → 设置为 `999`
3. `Names count to use static import with '*'` → 设置为 `999`

## 安全组件开发规范

### 命令执行安全

**必须遵循的安全实践**：

1. **命令白名单**：使用白名单限制可执行命令，未注册的命令必须拒绝
2. **参数注入**：参数通过占位符（`%s`）注入，禁止直接拼接用户输入
3. **参数校验**：使用黑名单拦截危险字符（shell 元字符、路径遍历、环境变量展开等）
4. **环境变量管控**：敏感环境变量（如 `LD_PRELOAD`）必须加入黑名单
5. **工作目录验证**：阻止敏感系统目录及其子目录（使用前缀匹配）
6. **输出限制**：设置最大输出行数（如 100,000 行），防止 OOM
7. **超时控制**：同步执行必须设置超时，防止命令卡死
8. **优雅销毁**：SIGTERM → 宽限期 → SIGKILL，避免强制杀死

### 跨平台开发

**Windows/Linux 兼容性注意事项**：

1. **环境变量大小写**：Windows 环境变量 key 大小写不敏感，需要特殊处理
2. **路径分隔符**：使用 `File.separator` 而非硬编码 `/` 或 `\`
3. **Shell 命令**：跨平台适配（Windows: `cmd /c`，Linux: `/bin/sh -c`）
4. **测试用例**：使用跨平台命令，避免平台特定语法

### 并发编程

**线程安全最佳实践**：

1. **读写锁**：读多写少场景使用 `ReentrantReadWriteLock`，性能优于 `synchronizedList`
2. **避免过时 API**：不使用 `Collections.synchronizedList`，使用现代并发工具
3. **线程超时**：线程 join 超时后记录日志并 interrupt，避免线程泄漏
4. **资源释放**：确保线程引用及时置 null，帮助 GC 回收

### 测试规范

**反射使用规范**：

1. **限制范围**：只在 `@BeforeEach` 中使用反射访问 private 字段
2. **避免暴露**：不要为了测试暴露生产 API（如 `clearWhiteList()`）
3. **使用 public API**：其他测试方法优先使用 public API（如 `getWhiteListSize()`）

**测试覆盖要求**：

1. **正常路径**：覆盖所有正常执行场景
2. **异常路径**：覆盖所有异常和边界情况
3. **跨平台**：确保测试在 Windows 和 Linux 都能通过
4. **并发场景**：测试多线程并发读写
