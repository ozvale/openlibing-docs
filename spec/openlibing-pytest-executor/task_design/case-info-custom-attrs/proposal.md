# case-info-custom-attrs — 支持自定义属性

## 需求背景

当前 `pytest.mark.case_info` 只支持 `level` 和 `type` 两种固定属性，限制了测试用例分类和筛选的灵活性。在实际测试场景中，团队往往需要按更多维度筛选用例，例如：
- 按模块筛选（module）
- 按标签筛选（tags）
- 按环境筛选（env_type）

Issue #14 要求扩展 `case_info` mark，支持自定义属性，以满足多样化的用例筛选需求。

## 功能描述

### 做什么

1. **重构属性处理逻辑**
   - 将 `level` 和 `type` 从特殊属性重构为普通自定义属性，统一处理逻辑
   - 所有 `case_info` mark 的 kwargs 参数都作为自定义属性处理

2. **扩展 mark 语法**
   - 支持任意 kwargs 参数：`@pytest.mark.case_info(level='P1', owner='team1', module='auth', tags='perf')`
   - 保持与 `template` 参数的兼容性（template 文件中的属性也作为默认值）

3. **扩展 pytest.ini 配置**
   - `[case_info]` section 支持任意属性配置
   - 未配置的属性或配置为通配符（WILDCARD）则不参与筛选

4. **统一筛选逻辑**
   - ini 中配置的属性必须精确匹配用例的属性值
   - ini 中未配置的属性（或配置为通配符）则通配所有用例
   - 用例缺少某属性时，该属性不参与筛选（视为不匹配）

### 不做什么

- 不改变现有的 `env` mark 和 `remote_run` mark
- 不改变 `test_ids` 的 include/exclude 逻辑
- 不支持属性值的正则匹配或模糊匹配
- 不支持属性值的多值匹配（如 `owner = team1,team2`）
- 不改变 template 文件的 JSON 格式（只是扩展支持更多属性字段）

## 验收标准

- [ ] `@pytest.mark.case_info(level='P1', owner='team1', module='auth')` 能正确识别所有属性
- [ ] pytest.ini 中 `[case_info]` section 支持 `level`、`type`、`module` 等任意属性
- [ ] ini 中配置的属性精确匹配，未配置的属性通配
- [ ] 用例缺少某属性时，该属性不参与筛选（视为不匹配）
- [ ] template 文件中的属性能作为默认值被正确读取
- [ ] 补充相关单元测试验证功能正确性

## 影响范围

- **模块**: pytest-testkit/pytest_testkit/plugin.py
- **函数**:
  - `_get_item_case_info` - 重构为返回属性字典而非 (level, type) tuple
  - `_get_inifile_info` - 重构为返回属性字典而非 (level, type, ...) tuple
  - `_collect_case_with_inifile` - 重构筛选逻辑为字典遍历
- **配置**: pytest.ini `[case_info]` section 格式扩展
- **数据**: template JSON 文件支持更多属性字段
- **仓库**: openlibing-pytest-executor（业务仓） + openlibing-docs（spec 仓）

## 关联 Issue

- 业务 Issue: https://gitcode.com/openlibing/openlibing-pytest-executor/issues/14