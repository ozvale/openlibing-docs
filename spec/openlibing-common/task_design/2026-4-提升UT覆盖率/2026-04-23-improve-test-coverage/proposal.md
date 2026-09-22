# Proposal: 提升测试覆盖率至65%-70%

## Summary

将 openlibing-common 项目的测试覆盖率从当前 26% 提升至 65%-70%，满足团队质量要求。

## Problem

- 当前测试覆盖率仅为 26%，远低于团队要求的 60% 最低标准
- 多个核心类缺少测试或测试不充分：
  - CsvValidator - 完全未测试
  - PublishMessageUtils - 完全未测试
  - SecurityUtil/AESCipher - 测试弱，依赖外部密钥文件无法完整运行
  - LoggerAspect/AbstractLogHandler - 完全未测试
  - ConfigContextInitializer/JasyptConfig - 完全未测试
- 华为云 SDK 依赖导致测试难以执行
- 密钥文件依赖链阻塞加密模块测试

## Solution

采用分阶段策略逐步提升覆盖率：

### Phase 1: 快速见效 (纯静态类) - +10-15%
- 新增 CsvValidatorTest
- 增强 AESCipherTest 边界测试
- 增强 HmacUtilTest 异常路径

### Phase 2: Mock重构 (工具类) - +15-20%
- 新增 PublishMessageUtilsTest (Mock SmnClient)
- 重构 ObsUtilTest (Mock ObsClient)
- 重构 SecurityUtilTest (静态Mock ReadFileUtils)
- 重构 AESCipherTest (静态Mock ReadFileUtils)

### Phase 3: Spring Mock (配置类和AOP) - +10-15%
- 新增 ConfigContextInitializerTest
- 新增 JasyptConfigTest
- 新增 LoggerAspectTest
- 新增 AbstractLogHandlerTest

### Phase 4: 边界补充 - +5-10%
- 补充异常路径测试
- 补充边界值测试
- 补充并发安全测试

## Scope

### In Scope
- 所有非 pojo/exception/constants/enums 包下的类
- 添加 mockito-inline 依赖支持静态方法 Mock
- 保持现有 JaCoCo 排除策略

### Out of Scope
- pojo/VO/Entity 类 (已排除)
- exception 类 (已排除)
- constants 类 (已排除)
- enums 类 (已排除)

## Success Criteria

- JaCoCo 指令覆盖率 ≥ 65%
- 所有新增测试通过
- pom.xml 中 minimum 阈值更新为 0.60

## Constraints

- **不改动原代码**: 所有测试必须在不修改源代码的前提下完成
- **尽量使用Mock**: 优先使用Mockito/mockito-inline进行依赖隔离
- **缺少Mock条件可跳过**: 部分静态方法内部直接构造对象的场景跳过（PublishMessageUtils、ObsUtil.createObsClient）

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| 静态Mock可能导致测试不稳定 | 中 | 使用 try-with-resources 确保 Mock 作用域正确 |
| 华为云SDK API变化 | 低 | Mock 不依赖具体实现细节 |
| 测试执行时间增加 | 低 | 全部使用 Mock，不启动真实服务 |
| 部分类无法完整测试 | 低 | PublishMessageUtils/ObsUtil.createObsClient跳过，影响<3% |

## Dependencies

- mockito-inline 5.2.0 (新增依赖，支持静态方法Mock)
- ReflectionTestUtils (已有，Spring Test提供，用于注入@Value字段)

## Timeline

- Phase 1: 1-2 小时
- Phase 2: 3-4 小时  
- Phase 3: 4-6 小时
- Phase 4: 2-3 小时
- Total: 10-15 小时