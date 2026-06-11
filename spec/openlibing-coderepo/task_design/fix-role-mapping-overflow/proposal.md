# Proposal: 修复 roleMapping 过长导致 5010000 全局异常

## 需求背景

`/update-gitcode-role-mapping` 接口在 `roleMapping` JSON 字符串过长时，数据库写入失败抛出 `DataTruncation` 异常。该异常类型未在 `ErrorCode` 枚举中注册，`GlobalExceptionHandler` 无法匹配到具体错误码，最终走通用异常分支返回 5010000（GENERAL_EXCEPTION），用户只能看到"异常，请联系OpenLiBing开发人员排查"，无法定位问题。

## 验收标准

1. 当 roleMapping 中映射关系数量超过 50 个时，接口返回明确的业务错误信息，而非 5010000 全局异常
2. 数据库 `role_mapping` 列类型从 VARCHAR(255) 升级为 TEXT，从根本上消除长度限制
3. 全局异常日志包含完整异常堆栈，便于后续定位类似问题
4. 现有正常映射关系的增删改查功能不受影响
5. 新增单元测试覆盖映射数量超限场景
