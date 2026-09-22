# case-info-custom-attrs — 实现任务

## 进度: 0/6 complete

### Task 1: 重构 _get_item_case_info 函数
- [ ] 修改函数返回值从 tuple 改为 dict
- [ ] 将所有 kwargs 参数（除 template）都作为自定义属性
- [ ] 合并 template 文件中的属性和 mark 中的属性（mark 优先）
- [ ] 更新函数文档字符串
- **涉及文件**: pytest_testkit/plugin.py
- **测试方式**: 单元测试验证返回 dict 结构

### Task 2: 重构 _get_inifile_info 函数
- [ ] 修改函数返回值从 tuple 改为 dict
- [ ] 使用 cfg.items('case_info') 遍历所有属性
- [ ] 保持 include_ids 和 exclude_ids 的处理逻辑不变
- [ ] 更新函数文档字符串
- **涉及文件**: pytest_testkit/plugin.py
- **测试方式**: 单元测试验证返回 dict 结构

### Task 3: 重构 _collect_case_with_inifile 函数
- [ ] 使用字典遍历替换硬编码的 level/type 检查
- [ ] 实现通用属性匹配逻辑：ini 中配置则精确匹配，未配置则通配
- [ ] 用例缺少某属性时，该属性不参与筛选
- [ ] 更新日志信息，显示所有筛选属性
- **涉及文件**: pytest_testkit/plugin.py
- **测试方式**: 集成测试验证筛选逻辑

### Task 4: 补充单元测试
- [ ] 创建 test_plugin_case_info.py 测试文件
- [ ] 测试 _get_item_case_info 返回 dict 结构
- [ ] 测试 template 和 mark 属性合并逻辑
- [ ] 测试 _get_inifile_info 返回 dict 结构
- [ ] 测试属性筛选逻辑
- **涉及文件**: tests/test_plugin_case_info.py（新增）
- **测试方式**: 运行 pytest 验证测试通过

### Task 5: 更新 README 文档
- [ ] 在 pytest-testkit/README.md 中添加自定义属性使用示例
- [ ] 更新 case_info mark 语法说明
- [ ] 更新 pytest.ini 配置示例
- **涉及文件**: pytest-testkit/README.md
- **测试方式**: 手动验证文档清晰度

### Task 6: 运行完整测试验证
- [ ] 运行 pytest-testkit/tests 下所有测试
- [ ] 确保现有测试不因重构而失败
- [ ] 验证新测试全部通过
- **涉及文件**: pytest-testkit/tests/
- **测试方式**: pytest 命令行执行