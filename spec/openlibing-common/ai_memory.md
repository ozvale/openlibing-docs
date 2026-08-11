# openlibing-common AI Memory

本文档保存 `openlibing-common` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-common` 为公共组件 SDK 服务，为 OpenLiBing 平台各微服务提供统一的基础能力，后续系统级职责、工具边界、任务执行链路、安全约束需在 `system_design/` 中逐步补齐。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及 Agent 工具调用、权限、安全边界、外部系统访问时，必须补充设计说明后再实现。
- 需求完成后，必须在 `archive.md` 记录 AI 错误、人工修正和可复用规则。

## 常见 AI 错误与规避

| 错误模式 | 规避规则 | 来源需求 |
| --- | --- | --- |
| Spotless/CheckStyle import 顺序冲突 | 禁止使用通配符导入（`import java.util.*`），必须显式列出每个类；禁止使用 `import static *`，必须显式列出每个静态成员 | 命令执行安全组件 |
| IDEA 自动格式化干扰 git 提交 | 提交前必须关闭 IDEA 的 "Optimize imports on the fly" 和 "Actions on Save" 中的自动格式化；正确流程：`mvn spotless:apply` → `git add` → `git commit` | 命令执行安全组件 |
| pre-commit hook 修改文件导致提交失败 | 不要在 hook 运行后检查工作区差异；先运行 `mvn spotless:apply` 格式化，再 `git add` 暂存格式化后的文件，最后 `git commit` | 命令执行安全组件 |

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
