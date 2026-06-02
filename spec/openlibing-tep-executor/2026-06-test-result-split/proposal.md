# 测试结果HTML文件拆分归档支持

## 需求背景

当单个测试用例或步骤的输出内容过长时,系统会强制进行拆分处理,生成多个HTML文件(如 `TC_xxx_1.html`, `TC_xxx_2.html` 等)。当前在构建测试结果日志URL时,`get_case_log_urls` 函数只取第一个HTML文件,忽略了其他拆分文件,导致部分测试日志内容无法正常显示。

**问题根源**:
- [utils.py:1371](file:///home/tzing/openlibing/openlibing-tep-executor/tepexecor_frame/cte/utils.py#L1371) 在处理HTML文件时,只取第一个文件:
  ```python
  elif file_name.lower().endswith(('.html', '.htm')):
      # 防止多个html文件,仅取第一个
      if html_file is None:
          html_file = file_name
  ```
- 当测试用例输出过长被拆分成多个HTML文件时,只有第一个文件的URL被记录到 `run_log` 字段
- 其他拆分的HTML文件被忽略,导致用户无法查看完整的测试日志

## 功能描述

修复 `get_case_log_urls` 函数,确保拆分的多个HTML文件能够正确记录并显示。

**做什么**:
- 修改 `utils.py` 的 `get_case_log_urls` 函数,支持处理多个HTML文件
- 将多个HTML文件的URL正确记录到测试结果中
- 确保用户能够访问所有拆分的HTML日志文件

**不做什么**:
- 不修改测试执行框架的HTML拆分逻辑
- 不改变HTML文件的命名和存储策略
- 不影响其他模块的结果处理流程

## 验收标准

- [ ] 当用例目录下存在多个拆分的HTML文件时,所有HTML文件的URL都能正确记录
- [ ] 测试结果中的 `resultDownloadUrl` 字段能够展示所有拆分的HTML日志
- [ ] 用户能够访问所有拆分的HTML日志文件,查看完整测试输出
- [ ] 不影响单HTML文件场景的正常工作(向后兼容)
- [ ] 相关日志输出正确记录HTML文件处理信息

## 影响范围

**受影响的模块**:
- `tepexecor_frame/cte/utils.py` - 日志URL生成逻辑
- `tepexecor_frame/executor.py` - 测试结果数据结构(可能需要调整)

**受影响的文件**:
- utils.py 的 `get_case_log_urls` 函数(约 30 行修改)
- 可能需要调整 `resultDownloadUrl` 字段的数据结构(从单URL变为URL列表或合并URL)

## 技术约束

- 必须保持向后兼容,不影响现有单HTML文件场景
- 必须确保所有拆分的HTML文件都能被访问
- 需要考虑URL的展示方式(多个URL如何呈现给用户)
- 需要考虑HTML文件的命名规则和排序逻辑

## 关联 Issue

- 业务 Issue: https://gitcode.com/openlibing/openlibing-tep-executor/issues/14