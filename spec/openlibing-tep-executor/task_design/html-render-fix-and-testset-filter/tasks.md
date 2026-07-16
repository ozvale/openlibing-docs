# HTML渲染修复与XML路径过滤功能增加 — 实现任务

## 进度: 0/8 complete

### UniAutosPython3框架仓任务

- [ ] Task 1: 新增LogFormat._read_static_file静态方法
  - 位置: `src/Framework/Dev/lib/UniAutos/Log/LogFormat.py`
  - 功能: 读取html目录下的静态资源文件(CSS/JS)
  - 异常处理: 文件不存在时记录错误日志并返回空内容
  - 预估: 10分钟

- [ ] Task 2: 修改LogFormat.formatHtmlHead和新增formatHtmlBodyScript方法
  - 位置: `src/Framework/Dev/lib/UniAutos/Log/LogFormat.py`
  - 功能:
    - `formatHtmlHead`: jquery使用百度外网CDN,CSS内嵌到`<head>`
    - `formatHtmlBodyScript`: Main.js内嵌到`</body>`前,Main日志额外内嵌echarts
  - 逻辑: TestCase日志外网CDN jquery + 内嵌CSS+Main.js; Main日志额外内嵌echarts
  - 模板变更: `{script}`改为`{headScript}`, `htmlTail`新增`{bodyScript}`
  - 预估: 20分钟

- [ ] Task 3: Appender.py调用formatHtmlBodyScript
  - 位置: `src/Framework/Dev/lib/UniAutos/Log/Appender.py`
  - 功能: 在`__init__`中调用`formatHtmlBodyScript`生成bodyScript,传入htmlTail模板
  - 预估: 5分钟

- [ ] Task 4: UniAutosPython3本地测试验证
  - 测试: 生成TestCase日志HTML和Main日志HTML
  - 验证: 外网环境可正常显示(样式/交互/图表)
  - 对比: HTML文件体积差异(TestCase≈21KB增加, Main≈993KB增加)
  - 预估: 30分钟

- [ ] Task 5: UniAutosPython3提交PR并发布新版本
  - 分支: 基于master新建分支`feat-html-embed-css-js`
  - PR标题: `feat(Log): use external CDN jquery and embed CSS/Main.js for external network rendering`
  - 关联Issue: `Refs openlibing/openlibing-tep-executor#18`
  - 发布版本: 标注版本号(如v1.2.0)
  - 预估: 1小时(含审核时间)

### openlibing-tep-executor业务仓任务

- [ ] Task 6: executor新增test_xml_paths成员变量和accept_para解析
  - 位置: `tepexecor_frame/executor.py`
  - 功能:
    - 新增`self.test_xml_paths = []`
    - `accept_para`方法解析配置JSON中的`testXmlPaths`字段
    - 多config场景合并testXmlPaths
  - 预估: 15分钟

- [ ] Task 7: executor._get_all_testset_files增加路径过滤逻辑
  - 位置: `tepexecor_frame/executor.py`
  - 功能:
    - 获取所有testset xml后,根据test_xml_paths过滤
    - 路径匹配逻辑: 前缀匹配(类似`_is_file_path_in_test_paths`)
    - 过滤后文件为空时记录警告日志
  - 预估: 20分钟

- [ ] Task 8: executor本地测试验证testXmlPaths功能
  - 测试场景:
    - testXmlPaths为空:验证处理所有testset xml
    - testXmlPaths配置单个路径:验证过滤生效
    - testXmlPaths配置错误路径:验证metadata.xml为空
  - 验证: 查看metadata.xml内容是否按路径过滤
  - 预估: 30分钟

- [ ] Task 9: openlibing-tep-executor提交PR
  - 分支: 继续在tzing_dev分支开发
  - PR标题: `feat(executor): add testXmlPaths config for testset xml path filtering`
  - PR描述: 关联Issue #18 + 变更摘要 + 验证结果
  - 标签: 打上`ai-assisted`标签
  - 预估: 1小时(含审核时间)

### 验证与文档任务(可选)

- [ ] Task 10: 集成测试验证
  - 测试: 同时启用HTML内嵌和testXmlPaths过滤
  - 验证: 向后兼容(旧配置文件仍可运行)
  - 预估: 30分钟

- [ ] Task 11: 文档同步更新
  - UniAutosPython3 README: 说明jquery外网CDN + CSS/Main.js内嵌的变化
  - executor README: 说明testXmlPaths配置用法
  - 配置示例文档: 提供含testXmlPaths的JSON示例
  - 预估: 1小时

## 实现顺序建议

**推荐顺序**:
1. Task 1-5: 先完成UniAutosPython3框架仓修改和发布
2. Task 6-9: 再完成openlibing-tep-executor业务仓修改
3. Task 10-11: 最后集成测试和文档同步

**原因**: executor依赖UniAutosPython3新版本框架,需先发布框架仓

## 依赖关系

```
UniAutosPython3(Task1-5) → executor(Task6-9) → 集成测试(Task10) → 文档(Task11)
```

## 验证命令清单

### UniAutosPython3验证

```bash
cd /home/tzing/openlibing/UniAutosPython3

# 1. 本地测试生成HTML
python src/Framework/Dev/bin/UniAutosScript.py --config test.json

# 2. 查看HTML文件体积
ls -lh cases_log/*.html

# 3. 检查HTML头部是否有内嵌CSS和外网CDN jquery
head -n 100 cases_log/tc_*.html | grep -E "<style>|apps.bdimg.com"
```

### executor验证

```bash
cd /home/tzing/openlibing/openlibing-tep-executor

# 1. 测试testXmlPaths为空
python tepexecor_frame/main.py --task_project_id test --env_param ... --config cli/test.json
cat tepexecor_frame/config/cases_log/metadata_test.xml

# 2. 测试testXmlPaths配置
cat cli/test_with_testXmlPaths.json
{
  "testXmlPaths": ["Testcases/02_MindIE_LLM1/"],
  ...
}
python tepexecor_frame/main.py ... --config cli/test_with_testXmlPaths.json
cat tepexecor_frame/config/cases_log/metadata_test.xml
```

## 完成标准

- [ ] UniAutosPython3 PR已合并,新版本已发布
- [ ] executor PR已合并,关联Issue #18
- [ ] HTML在外网环境可正常显示
- [ ] testXmlPaths功能按预期过滤testset xml
- [ ] 向后兼容验证通过(旧配置文件仍可运行)
- [ ] 文档已同步更新

## 实现状态

### UniAutosPython3 (已完成)

提交: `a5f6a753493860c01f83043ca519974fd3e3e5bb`

已完成任务:
- [x] Task 1: _read_static_file方法已实现
- [x] Task 2: formatHtmlHead和formatHtmlBodyScript方法已实现
- [x] Task 3: Appender.py已修改
- [ ] Task 4: 本地测试验证
- [ ] Task 5: 提交PR并发布