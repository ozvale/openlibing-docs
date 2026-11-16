# request-param-log-whitelist — 技术设计

## 方案概述

在日志参数拼接入口做"默认不记录"：`LoggerAppend.create` 只输出白名单内的非敏感标识参数，
其余参数无论键名如何一律跳过。白名单为静态 `Set`，匹配前统一转小写，避免调用方大小写差异导致漏记或漏拦。

## 数据流（修复后）

```
DefaultExceptionHandler.@ExceptionHandler（28 处）
  └─ LoggerAppend.create(request, LoggerType.ERROR)
       ├─ append(prefix, "error")
       ├─ append(requestURI, request.getRequestURI())
       └─ for entry in request.getParameterMap()
            ├─ isLoggableParameter(name) == false → continue（不落盘）
            └─ true → append(name, value)
                 ├─ values == null/0 → "key:null"
                 ├─ values.length == 1 → "key:value"
                 └─ values.length > 1 → "key:[v1, v2]"
```

## 架构决策

| 决策                                           | 理由                                                                                      |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------- |
| D1 白名单（allow-list）而非黑名单（deny-list） | 黑名单需要穷举 `token`/`password`/`secret`/`code` 等变体，新增参数即失效；白名单默认可控  |
| D2 白名单只收录"用于定位问题的非敏感标识"      | 18 项均为 ID、分页、平台、版本、类型、hash 类字段，可用于串联调用链，不涉及凭证与个人信息 |
| D3 匹配前 `toLowerCase(Locale.ROOT)`           | HTTP 参数名大小写由调用方决定（`scanId` / `scanid`），统一大小写避免合法参数被漏记        |
| D4 非白名单参数直接 `continue`，不输出空占位   | 避免通过键名本身泄露接口内部参数结构，同时减小日志体积                                    |
| D5 保留 `prefix` 与 `requestURI` 输出          | 二者是异常日志的定位骨架，`requestURI` 不含 query，无凭证风险                             |
| D6 不改调用方与日志格式                        | 改动面最小；`#` / `:` 分隔符与既有日志解析规则保持一致                                    |

## 涉及文件

| 文件                                                                | 操作 | 说明                                                                                                                |
| ------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/common/log/LoggerAppend.java`     | 修改 | 新增 `LOGGABLE_PARAMETERS`（18 项）与 `isLoggableParameter`；`create` 增加过滤；新增 `Locale`、`Set` 导入（+41 行） |
| `src/test/java/com/openlibing/sca/common/log/LoggerAppendTest.java` | 新增 | 5 个用例：前缀/URI、白名单命中、敏感参数过滤、多值、空值（82 行）                                                   |

不涉及 `DefaultExceptionHandler`：28 处调用签名不变。

## 风险 & 缓解

| 风险                                                       | 缓解                                                                                   |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 白名单遗漏后续新增的合法排查参数，导致排障信息不足         | 白名单集中定义并附注释；新增参数时同步补充并加单测；如需临时排查，可查看其他结构化日志 |
| 白名单中的 `repoUrl` 类字段是否应记录（当前未纳入）        | 明确不纳入：`repoUrl` 可能含 `user:pass@`，属敏感项（单测显式断言被过滤）              |
| 参数名大小写混用导致误判                                   | `toLowerCase(Locale.ROOT)` 归一，用例覆盖 camelCase                                    |
| 仅覆盖 `LoggerAppend` 路径，其他日志语句仍可能打印敏感参数 | 本 issue 范围限定该入口；全仓日志审查属后续治理项（未覆盖）                            |

## 跨仓影响

无。仅影响本服务 ERROR 日志内容，不涉及接口、配置或数据。
