# ISSUE-001 测试用例

> **Issue编号**: ISSUE-001
> **Issue标题**: 流水线模板功能
> **创建日期**: 2026-08-05
> **用例总数**: 4
> **手工用例**: 1
> **自动化用例**: 3

---

## 用例列表

| 用例编号 | 用例标题 | 用例类型 | 优先级 | 脚本位置 | 状态 |
|----------|----------|----------|--------|----------|------|
| TC-ISSUE001-001 | 保存流水线为模板（API） | auto_api | P0 | src/tests/openlibing/openlibing-cicd/pipeline/test_template_save_001.py | active |
| TC-ISSUE001-002 | 基于模板创建流水线（API） | auto_api | P0 | src/tests/openlibing/openlibing-cicd/pipeline/test_template_create_001.py | active |
| TC-ISSUE001-003 | 模板保存表单校验（UI 手工） | manual | P1 | — | active |
| TC-ISSUE001-004 | 模板越权访问（API） | auto_api | P0 | src/tests/openlibing/openlibing-cicd/pipeline/test_template_authz_001.py | active |

---

## 手工用例详情

### TC-ISSUE001-003: 模板保存表单校验（UI 手工）

- **用例类型**: 手工执行 (manual)
- **优先级**: P1
- **前置条件**: 已登录且存在一条流水线
- **测试步骤**:
  1. 进入流水线详情页，点击"保存为模板"
  2. 模板名留空，点击保存
  3. 模板名输入超长字符（>64），点击保存
- **预期结果**: 留空时提示"模板名不能为空"；超长时提示"模板名长度不能超过64"

---

## 自动化用例详情

### TC-ISSUE001-001: 保存流水线为模板（API）

- **用例类型**: 自动化-API (auto_api)
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_template_save_001.py`
- **优先级**: P0
- **前置条件**: 存在一条已配置完成的流水线
- **测试步骤**:
  1. 调用保存模板接口，传入 pipeline_id、模板名、可见范围
  2. 校验返回 code == 0
  3. 查询模板列表，确认新模板存在
- **预期结果**: 模板保存成功，列表可见，字段与原流水线一致

### TC-ISSUE001-002: 基于模板创建流水线（API）

- **用例类型**: 自动化-API (auto_api)
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_template_create_001.py`
- **优先级**: P0
- **前置条件**: 存在可用模板
- **测试步骤**:
  1. 调用基于模板创建接口，传入 template_id、项目 ID
  2. 校验返回 pipeline_id
  3. 查询新流水线配置，与模板逐字段比对
- **预期结果**: 新流水线创建成功，配置字段与模板完全一致

### TC-ISSUE001-004: 模板越权访问（API）

- **用例类型**: 自动化-API (auto_api)
- **脚本位置**: `src/tests/openlibing/openlibing-cicd/pipeline/test_template_authz_001.py`
- **优先级**: P0
- **前置条件**: 用户 A 创建私有模板 T1
- **测试步骤**:
  1. 用户 B 调用模板查询接口，传入 T1 的 template_id
  2. 用户 B 调用基于模板创建接口，传入 T1 的 template_id
- **预期结果**: 查询接口返回 403/不存在；创建接口返回 403

---

## 用例汇总

| 类型 | 数量 | 通过 | 失败 | 跳过 |
|------|------|------|------|------|
| 手工用例 | 1 | 0 | 0 | 0 |
| 自动化-API | 3 | 0 | 0 | 0 |
| **合计** | **4** | **0** | **0** | **0** |
