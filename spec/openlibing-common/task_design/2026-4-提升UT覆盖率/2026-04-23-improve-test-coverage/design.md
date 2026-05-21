# Design: 测试覆盖率提升技术设计

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         测试分层策略                                          │
└─────────────────────────────────────────────────────────────────────────────┘

Layer 1: 纯单元测试 (无Mock)
───────────────────────────────────────────────────────────────────────────────
  CsvValidator ──────────────► CsvValidatorTest
  (静态方法, 无外部依赖)

Layer 2: SDK Mock 测试
───────────────────────────────────────────────────────────────────────────────
  PublishMessageUtils ───────► Mock SmnClient
  ObsUtil ───────────────────► Mock ObsClient

Layer 3: 静态方法 Mock 测试
───────────────────────────────────────────────────────────────────────────────
  SecurityUtil ──────────────► Mock Static ReadFileUtils
  AESCipher ─────────────────► Mock Static ReadFileUtils
  (使用 mockito-inline)

Layer 4: Spring Mock 测试
───────────────────────────────────────────────────────────────────────────────
  ConfigContextInitializer ──► Mock ConfigurableApplicationContext
  JasyptConfig ──────────────► Mock SecurityUtil (static)
  LoggerAspect ──────────────► Mock JoinPoint, HttpServletRequest
  AbstractLogHandler ────────► Mock HttpServletRequest, ApplicationContext
```

## Key Technical Decisions

### 1. Mockito-inline 集成

**Decision**: 使用 mockito-inline 替代标准 mockito-core

**Rationale**: 
- SecurityUtil/AESCipher 依赖 ReadFileUtils 静态方法
- 标准 mockito 不支持静态方法 Mock
- mockito-inline 提供 `MockedStatic` API

**Implementation**:
```xml
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-inline</artifactId>
    <version>5.2.0</version>
    <scope>test</scope>
</dependency>
```

### 2. 密钥文件 Mock 策略

**Challenge**: 
```
SecurityUtil.encrypt()
    → AESCipher.getWorkKey()
        → ReadFileUtils.readWorkKey() ──► 密钥文件 (不存在)
            → ReadFileUtils.readPart2() ──► 密钥文件
            → ReadFileUtils.readPart3() ──► 密钥文件
```

**Solution**: 使用静态 Mock 模拟密钥文件内容
```java
try (MockedStatic<ReadFileUtils> mocked = mockStatic(ReadFileUtils.class)) {
    mocked.when(ReadFileUtils::readWorkKey).thenReturn("base64_encoded_work_key");
    mocked.when(ReadFileUtils::readPart2).thenReturn("base64_encoded_part2");
    mocked.when(ReadFileUtils::readPart3).thenReturn("base64_encoded_part3");
    
    // 设置环境变量模拟 rootSalt
    System.setProperty("rootSalt", "mock_salt_value");
    
    // 现在可以完整测试加密链路
    String encrypted = SecurityUtil.encrypt("test", "part1");
    String decrypted = SecurityUtil.decrypt(encrypted, "part1");
    assertEquals("test", decrypted);
}
```

### 3. RequestContextHolder Mock 策略

**Challenge**: LoggerAspect/AbstractLogHandler 依赖 Servlet 环境

**Solution**: 手动设置 Mock 请求上下文
```java
@BeforeEach
void setUp() {
    HttpServletRequest mockRequest = mock(HttpServletRequest.class);
    when(mockRequest.getCookies()).thenReturn(new Cookie[]{
        new Cookie("token", "test_token")
    });
    when(mockRequest.getMethod()).thenReturn("POST");
    when(mockRequest.getRequestURI()).thenReturn("/api/test");
    
    ServletRequestAttributes attrs = new ServletRequestAttributes(mockRequest);
    RequestContextHolder.setRequestAttributes(attrs);
}

@AfterEach
void tearDown() {
    RequestContextHolder.resetRequestAttributes();
}
```

### 4. AbstractLogHandler 测试策略

**Challenge**: AbstractLogHandler 是抽象类

**Solution**: 创建测试专用子类
```java
private static class TestLogHandler extends AbstractLogHandler {
    @Override
    protected String getOldData(String operation, Map<String, Object> paramsMap) {
        return "test_old_data";
    }
    
    @Override
    protected void encapsulatingLogsDetailVO(String operation, 
            String oldDataJsonString, LogsDetailVO logsDetailVO, Map resultMap) {
        // 测试实现
    }
    
    @Override
    protected void saveLog(String tableName, LogsDetailVO logsDetailVO) {
        // 测试实现 - 不实际保存
    }
}
```

### 5. 华为云 SDK Mock 策略

**Constraint**: 华为云凭证不能明文出现

**Solution**: 使用 Mock 完全隔离 SDK
```java
// PublishMessageUtilsTest
SmnClient mockClient = mock(SmnClient.class);
when(mockClient.publishMessage(any(PublishMessageRequest.class)))
    .thenReturn(new PublishMessageResponse());

// ObsUtilTest
ObsClient mockObs = mock(ObsClient.class);
when(mockObs.putObject(any(PutObjectRequest.class)))
    .thenReturn(new PutObjectResult());
```

## Test Code Style

遵循现有风格规范:
- 使用 `@DisplayName("中文描述")`
- 使用 JUnit 5 (`@Test`, `@BeforeEach`, `@AfterEach`)
- 测试方法命名: `test{MethodName}_{Scenario}`
- 使用 `assertThrows` 测试异常场景

## JaCoCo Configuration

维持现有排除策略:
```xml
<excludes>
    <exclude>**/pojo/**</exclude>
    <exclude>**/exception/**</exclude>
    <exclude>**/constants/**</exclude>
    <exclude>**/enums/**</exclude>
</excludes>
```

更新覆盖率阈值:
```xml
<minimum>0.60</minimum>  <!-- 从 0.20 提升至 0.60 -->
```

## File Structure

新增测试文件位置:
```
src/test/java/com/openlibing/common/
├── validator/
│   └── CsvValidatorTest.java          (新增)
├── utils/
│   ├── PublishMessageUtilsTest.java   (新增)
│   ├── ObsUtilTest.java               (重构)
│   └── SecurityUtilTest.java          (重构)
├── security/
│   ├── cipher/
│   │   ├── AESCipherTest.java         (重构)
│   │   └── ReadFileUtilsTest.java     (增强)
│   └── security/
│       ├── HmacUtilTest.java          (增强)
│       └── SecurityUtilTest.java      (重构)
├── config/
│   ├── ConfigContextInitializerTest.java (新增)
│   └── JasyptConfigTest.java          (新增)
└── aspect/logapi/
    ├── LoggerAspectTest.java          (新增)
    └── AbstractLogHandlerTest.java    (新增)
```