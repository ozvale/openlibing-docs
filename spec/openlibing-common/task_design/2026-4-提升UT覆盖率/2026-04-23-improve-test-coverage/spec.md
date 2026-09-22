# Spec: test-coverage-improvement

> Capability ID: `test-coverage-improvement`
> Version: 1.0.0
> Status: Archived

## Overview

提升 openlibing-common 项目单元测试覆盖率，满足团队质量标准要求。

---

## Quality Specifications

### Coverage Targets

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Instruction Coverage | 26% | 70% | ≥65% |
| Branch Coverage | ~20% | 67% | ≥60% |
| Line Coverage | ~25% | 66% | ≥60% |
| JaCoCo Minimum Threshold | 0.20 | 0.60 | 0.60 |

### Test Class Requirements

| Package | Required Tests | Status |
|---------|---------------|--------|
| `com.openlibing.common.validator` | CsvValidatorTest | ✓ Added |
| `com.openlibing.common.utils` | ImageCheckUtilTest, ExternalLinkCheckUtilsTest, ObsUtilTest | ✓ Enhanced |
| `com.openlibing.common.security.cipher` | AESCipherTest | ✓ Enhanced |
| `com.openlibing.common.security.security` | SecurityRandomTest, SecurityUtilTest | ✓ Added/Refactored |
| `com.openlibing.common.config` | ConfigContextInitializerTest, JasyptConfigTest | ✓ Added |
| `com.openlibing.common.aspect.logapi` | LoggerAspectTest, AbstractLogHandlerTest | ✓ Added |

### Test Count Target

- Before: ~150 tests
- After: ~230 tests
- Net Addition: ~80 tests

---

## Technical Specifications

### Testing Patterns

#### Pattern 1: Pure Unit Test (No Mock)
```java
@DisplayName("测试validate方法")
@Test
void testValidate_ValidInput() {
    assertTrue(CsvValidator.validate("normal_text"));
}
```

#### Pattern 2: Static Method Mock
```java
try (MockedStatic<ReadFileUtils> mocked = mockStatic(ReadFileUtils.class)) {
    mocked.when(ReadFileUtils::readWorkKey).thenReturn("mock_key");
    // Test SecurityUtil.encrypt/decrypt
}
```

#### Pattern 3: SDK Dependency Mock
```java
ObsClient mockClient = mock(ObsClient.class);
when(mockClient.putObject(any())).thenReturn(mock(PutObjectResult.class));
ObsUtil util = new ObsUtil(mockClient, "endpoint");
```

#### Pattern 4: Spring Context Mock
```java
ReflectionTestUtils.setField(handler, "successCode", "200");
ReflectionTestUtils.setField(handler, "openlibingDomain", "https://openlibing.com");
```

#### Pattern 5: Request Context Mock
```java
MockHttpServletRequest request = new MockHttpServletRequest();
ServletRequestAttributes attrs = new ServletRequestAttributes(request);
RequestContextHolder.setRequestAttributes(attrs);
```

### Dependencies Required

| Dependency | Version | Purpose |
|------------|---------|---------|
| mockito-inline | 5.2.0 | Static method mocking |
| spring-mock-web | (existing) | HttpServletRequest mock |
| junit-jupiter | 5.x | Test framework |

---

## Exclusion Specifications

JaCoCo exclusions (unchanged):

```xml
<excludes>
    <exclude>**/pojo/**</exclude>
    <exclude>**/exception/**</exclude>
    <exclude>**/constants/**</exclude>
    <exclude>**/enums/**</exclude>
</excludes>
```

---

## Skipped Items

| Class | Reason | Coverage Impact |
|-------|--------|-----------------|
| PublishMessageUtils | Internal `new SmnClient()` construction | <1% |
| ObsUtil.createObsClient | Internal `new ObsClient()` construction | <0.5% |

**Total Skip Impact: <2%** - Does not affect target achievement.

---

## Constraints

1. **No Source Code Modification**: Tests must work without changing production code
2. **Mock Preference**: Use Mockito/mockito-inline for dependency isolation
3. **Credential Safety**: No hardcoded Huawei Cloud credentials in tests
4. **Style Consistency**: Use `@DisplayName("中文描述")` pattern

---

## Validation Criteria

### Build Verification
```bash
mvn verify  # Must pass with JaCoCo check
```

### Coverage Verification
```bash
mvn test jacoco:report
# Check target/site/jacoco/index.html for ≥65% coverage
```

### Test Execution
```bash
mvn test  # All 230+ tests must pass
```

---

## Implementation Summary

### Completed Tasks

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1 | 6 tasks (CsvValidator, ImageCheck, ExternalLink, AESCipher, SecurityRandom, ObsUtil) | ✓ |
| Phase 2 | 2 tasks (mockito-inline, SecurityUtil) | ✓ |
| Phase 3 | 4 tasks (ConfigContext, Jasypt, LoggerAspect, AbstractLogHandler) | ✓ |
| Phase 4 | 2 tasks (Boundary tests, JaCoCo config) | ✓ |

### Files Modified

| File | Change |
|------|--------|
| `pom.xml` | Added mockito-inline 5.2.0, updated JaCoCo minimum to 0.60 |
| 10 new test files | Added complete test coverage |

### Final Result

- **Coverage Achieved**: 70% (exceeded target)
- **All Tests Passing**: 231 tests, 0 failures
- **Build Status**: SUCCESS with JaCoCo verification