# 测试结果HTML文件拆分归档支持 — 实现任务

## 进度: 0/4 complete

- [x] Task 1: 修改 utils.py 的 get_case_log_urls 函数
  - 将 `html_file` 变量改为 `html_files` 列表
  - 收集所有HTML文件（不排序，保持原始顺序）
  - 返回 `run_log` 为URL列表（空列表表示无HTML文件）
  - 更新函数文档字符串说明返回结构变化

- [x] Task 2: 修改 executor.py 的结果处理逻辑
  - 在 [executor.py:656-681](file:///home/tzing/openlibing/openlibing-tep-executor/tepexecor_frame/executor.py#L656-L681) 处理 `run_log` 列表
  - 使用 `deepcopy(result)` 为每个HTML URL 创建独立记录
  - 添加类型检查和兼容性处理
  - 处理空列表和无HTML文件的场景

- [x] Task 3: 修改 utils.py 的 get_test_cases_dict 函数
  - 从只匹配 `---0.html` 后缀改为匹配所有 `.html` 文件
  - 使用 `split("---")` 提取用例名称，支持 `---0.html`, `---1.html` 等命名格式
  - 返回值从字符串改为列表，每个用例名对应一个文件路径列表

- [x] Task 4: 修改 uniautos.py 的 build_log_file 方法
  - 遍历 `get_case_result_logs()` 返回的文件列表
  - 移动所有 HTML 文件到目标目录

## 关键约束

- 必须保持向后兼容,不影响现有单HTML文件场景
- 必须确保所有拆分的HTML文件都能被用户访问
- 需要考虑HTML文件的命名规则和排序逻辑(如 `_1`, `_2` 后缀)
- 需要考虑URL展示方式,确保用户能理解有多个日志文件

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| tepexecor_frame/cte/utils.py | 修改 | get_case_log_urls 函数(约 20 行) + get_test_cases_dict 函数(约 10 行) |
| tepexecor_frame/executor.py | 修改 | get_results 方法(约 10 行) |
| tepexecor_frame/uniautos.py | 修改 | build_log_file 方法(约 5 行) |

## 验证方式

- 单HTML文件场景:只有一个HTML文件,验证URL生成正常
- 多HTML文件场景:有多个拆分的HTML文件(如 `TC_xxx_1.html`, `TC_xxx_2.html`),验证所有URL都能正确记录
- HTML文件排序:验证多个HTML文件按正确顺序排列(按文件名后缀数字排序)
- 检查测试结果JSON中的 `resultDownloadUrl` 字段是否包含完整的HTML日志信息