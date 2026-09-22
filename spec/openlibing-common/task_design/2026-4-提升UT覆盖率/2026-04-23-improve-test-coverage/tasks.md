# Tasks: 测试覆盖率提升任务清单

> **约束条件**: 不改动原代码，尽量使用Mock，缺少Mock条件的可跳过

---

## ✅ 可直接完成（不改动原代码）

### Task 1.1: 新增 CsvValidatorTest [✅ 可执行]
- **Priority**: High
- **Effort**: 0.5h
- **File**: `src/test/java/com/openlibing/common/validator/CsvValidatorTest.java`
- **Status**: 纯静态方法，无依赖，完全可测试
- **Test Cases**:
  - `testValidate_NullInput` - null 返回 false
  - `testValidate_EmptyInput` - 空字符串返回 false
  - `testValidate_ValidInput` - 正常文本
  - `testValidate_CsvInjectionChars` - `=+&\@"` 开头
  - `testConvertToHalfWidth_NullInput` - null 返回 null
  - `testConvertToHalfWidth_FullWidthChars` - 全角转半角
  - `testConvertToHalfWidth_FullWidthSpace` - 全角空格(0x3000)
  - `testConvertToHalfWidth_MixedChars` - 混合字符

### Task 1.2: 增强 ImageCheckUtilTest [✅ 可执行]
- **Priority**: High
- **Effort**: 1h
- **File**: `src/test/java/com/openlibing/common/utils/ImageCheckUtilTest.java`
- **Status**: 静态方法，可使用真实图片字节测试文件类型检测
- **Test Cases**:
  - `testUploadFileCheck_NullFile` - null文件返回true
  - `testUploadFileCheck_EmptyFile` - 空文件返回true
  - `testUploadFileCheck_NullCheckEntity` - null校验条件返回true
  - `testUploadFileCheck_ValidJpeg` - JPEG魔数(FFD8FF)测试
  - `testUploadFileCheck_ValidPng` - PNG魔数(89504E47)测试
  - `testUploadFileCheck_InvalidFileType` - 类型不匹配返回false
  - `testUploadFileCheck_FileSizeExceeded` - 超过大小限制
  - `testUploadFileCheckString_NullInput` - null返回false
  - `testUploadFileCheckString_EmptyInput` - 空字符串返回false

### Task 1.3: 增强 ExternalLinkCheckUtilsTest [✅ 可执行]
- **Priority**: High
- **Effort**: 0.5h
- **File**: `src/test/java/com/openlibing/common/utils/ExternalLinkCheckUtilsTest.java`
- **Status**: 已有ReflectionTestUtils模式，可直接扩展
- **Test Cases**:
  - `testReplaceMarkdown_ExternalLinkReplaced` - 外链替换为默认图片
  - `testReplaceMarkdown_InternalLinkKept` - 内源域名保持不变
  - `testReplaceMarkdown_MultipleImages` - 多图片混合场景
  - `testReplaceMarkdown_NoMarkdownFormat` - 非markdown文本保持不变

### Task 1.4: 增强 AESCipherTest [✅ 可执行]
- **Priority**: High
- **Effort**: 0.5h
- **File**: `src/test/java/com/openlibing/common/security/cipher/AESCipherTest.java`
- **Status**: `toXor` 是公开静态方法，可直接测试
- **Test Cases**:
  - `testToXor_DifferentLengthArrays` - 长度不同返回零数组
  - `testToXor_EmptyArrays` - 空数组测试
  - `testToXor_SelfXor` - 相同数组异或得零
  - `testToXor_AsymmetricXor` - 不对称异或测试

### Task 1.5: 增强 SecurityRandomTest [✅ 可执行]
- **Priority**: Medium
- **Effort**: 0.5h
- **File**: `src/test/java/com/openlibing/common/security/security/SecurityRandomTest.java`
- **Test Cases**:
  - `testGetRandomBytes_Length` - 验证长度
  - `testGetRandomBytes_Uniqueness` - 多次调用结果不同
  - `testGetRandomBase64_Format` - Base64格式验证
  - `testGetRandomHex_Format` - Hex格式验证
  - `testGetRandomBytes_ConcurrentSafety` - 并发安全测试

### Task 1.6: 重构 ObsUtilTest [✅ 可执行]
- **Priority**: High
- **Effort**: 1h
- **File**: `src/test/java/com/openlibing/common/utils/ObsUtilTest.java`
- **Status**: ObsUtil有构造函数接受ObsClient，可注入Mock
- **Test Cases**:
  - `testUploadString_Success` - Mock putObject成功
  - `testUploadString_ObsException` - Mock异常返回false
  - `testDownloadString_Success` - Mock getObject成功
  - `testDownloadString_ObsException` - Mock异常返回空字符串
  - `testDeleteString_Success` - Mock deleteObject成功
  - `testDeleteString_ObsException` - Mock异常返回false
  - `testUploadObject_Success` - Mock文件上传
  - `testDeleteObject_Success` - Mock文件删除

---

## ⚠️ 需mockito-inline静态Mock（添加依赖即可）

### Task 2.1: 添加 mockito-inline 依赖 [⚠️ 需添加依赖]
- **Priority**: High (阻塞后续任务)
- **Effort**: 0.1h
- **File**: `pom.xml`
- **Action**: 添加依赖声明（改动pom.xml是正常的）
```xml
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-inline</artifactId>
    <version>5.2.0</version>
    <scope>test</scope>
</dependency>
```

### Task 2.2: 重构 SecurityUtilTest [⚠️ 需mockito-inline]
- **Priority**: High
- **Effort**: 1h
- **File**: `src/test/java/com/openlibing/common/security/security/SecurityUtilTest.java`
- **Dependencies**: Task 2.1
- **Test Cases**:
  - `testEncryptDecrypt_WithMockedReadFileUtils` - 静态Mock完整链路
  - `testEncrypt_NullData` - null数据处理
  - `testDecrypt_NullData` - null数据处理

### Task 2.3: 增强 AESCipherTest (密钥链路) [⚠️ 需mockito-inline]
- **Priority**: High
- **Effort**: 0.5h
- **File**: `src/test/java/com/openlibing/common/security/cipher/AESCipherTest.java`
- **Dependencies**: Task 2.1
- **Test Cases**:
  - `testGetWorkKey_WithMockedReadFileUtils` - 静态Mock获取工作密钥
  - `testDecryptWorkKey_WithMockedReadFileUtils` - 静态Mock解密工作密钥

---

## ✅ Spring Mock（使用ReflectionTestUtils）

### Task 3.1: 新增 ConfigContextInitializerTest [✅ 可执行]
- **Priority**: Medium
- **Effort**: 0.5h
- **File**: `src/test/java/com/openlibing/common/config/ConfigContextInitializerTest.java`
- **Test Cases**:
  - `testInitialize_WithTrustStore` - Mock环境变量TRUST_STORE
  - `testInitialize_WithoutTrustStore` - 无环境变量

### Task 3.2: 新增 JasyptConfigTest [✅ 可执行]
- **Priority**: Medium
- **Effort**: 0.5h
- **File**: `src/test/java/com/openlibing/common/config/JasyptConfigTest.java`
- **Dependencies**: Task 2.1 (需要mock SecurityUtil静态方法)
- **Test Cases**:
  - `testJasyptStringEncryptor_EncryptDecrypt` - 测试StringEncryptor接口

### Task 3.3: 新增 LoggerAspectTest [✅ 可执行]
- **Priority**: High
- **Effort**: 2h
- **File**: `src/test/java/com/openlibing/common/aspect/logapi/LoggerAspectTest.java`
- **Status**: 使用ReflectionTestUtils注入@Value字段
- **Test Cases**:
  - `testRegisterLogHandler` - 注册处理器
  - `testDoBefore_WithLogHandler` - Mock JoinPoint正常流程
  - `testDoAfterReturning_SuccessResult` - Mock成功返回
  - `testDoAfterReturning_ExportResult` - 导出接口场景
  - `testDoAfterReturning_NullLogHandler` - 无处理器场景
  - `testDoAfterThrowing_Exception` - Mock异常
  - `testBuildRequestParamsMap_WithMethodSignature` - 参数映射

### Task 3.4: 新增 AbstractLogHandlerTest [✅ 可执行]
- **Priority**: High
- **Effort**: 2h
- **File**: `src/test/java/com/openlibing/common/aspect/logapi/AbstractLogHandlerTest.java`
- **Status**: 创建测试子类 + ReflectionTestUtils
- **Test Cases**:
  - `testSetApplicationContext` - ApplicationContext设置
  - `testGetOldDataJsonString` - 抽象方法调用
  - `testRecordLogs_WithRequestContext` - Mock请求上下文
  - `testRecordLogs_WithoutRequestContext` - 无请求上下文返回
  - `testParamValue_WithPathMatch` - 参数路径匹配
  - `testParamValue_WithoutPathMatch` - 参数路径不匹配
  - `testParamValue_EmptyParamName` - 无参数名返回整个实体

---

## ❌ 需跳过（无法在不改动原代码情况下测试）

### Task SKIP.1: PublishMessageUtilsTest [❌ 跳过]
- **Reason**: 静态方法内部直接构造 `SmnClient.newBuilder()...build()`
- **Note**: mockito-inline的MockConstruction理论上可以mock，但复杂度高，建议跳过
- **Alternative**: 如果后续必须测试，需重构源码增加依赖注入点

### Task SKIP.2: ObsUtil.createObsClient [❌ 跳过]
- **Reason**: 静态方法内部直接 `new ObsClient(ak, sk, endPoint)`
- **Note**: 同上，MockConstruction复杂度高
- **Coverage Impact**: 低，ObsUtil实例方法已通过Task 1.6覆盖

---

## Phase 4: 边界补充

### Task 4.1: 补充边界测试 [✅ 可执行]
- **Priority**: Low
- **Effort**: 1h
- **Files**: 多个测试文件
- **Test Cases**:
  - AESUtilTest - 空字符串加密、极长字符串
  - JwtUtilsTest - 过期token验证、无效格式token
  - KeyComponentUtilTest - 边界参数测试

### Task 4.2: 更新JaCoCo配置 [✅ 可执行]
- **Priority**: High
- **Effort**: 0.1h
- **File**: `pom.xml`
- **Action**: `<minimum>0.60</minimum>`

---

## 任务执行顺序

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         推荐执行顺序                                          │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: 基础测试（无需额外依赖）
───────────────────────────────────────────────────────────────────────────────
  1.1 CsvValidatorTest        → 新增
  1.2 ImageCheckUtilTest      → 增强
  1.3 ExternalLinkCheckUtilsTest → 增强
  1.4 AESCipherTest (toXor)   → 增强
  1.5 SecurityRandomTest      → 增强
  1.6 ObsUtilTest             → 重构（Mock ObsClient注入）

Step 2: 添加mockito-inline
───────────────────────────────────────────────────────────────────────────────
  2.1 pom.xml                 → 添加依赖

Step 3: 静态Mock测试
───────────────────────────────────────────────────────────────────────────────
  2.2 SecurityUtilTest        → 重构
  2.3 AESCipherTest (密钥链路) → 增强

Step 4: Spring Mock测试
───────────────────────────────────────────────────────────────────────────────
  3.1 ConfigContextInitializerTest → 新增
  3.2 JasyptConfigTest        → 新增
  3.3 LoggerAspectTest        → 新增
  3.4 AbstractLogHandlerTest  → 新增

Step 5: 收尾
───────────────────────────────────────────────────────────────────────────────
  4.1 边界测试                → 补充
  4.2 JaCoCo配置              → 更新阈值
```

---

## Summary

| Category | Tasks | Effort | Coverage Impact |
|----------|-------|--------|-----------------|
| ✅ 可执行 | 11 | 8h | +35-40% |
| ⚠️ mockito-inline | 3 | 1.5h | +5-8% |
| ❌ 跳过 | 2 | - | - |
| **Total 可执行** | **14** | **9.5h** | **+40-48%** |

**Expected Final Coverage**: 26% + 40-48% = **66%-74%**

**跳过影响分析**:
- PublishMessageUtils: 约20行代码，影响约1-2%
- ObsUtil.createObsClient: 约3行代码，影响约0.5%
- **总跳过影响 < 3%，不影响目标达成**