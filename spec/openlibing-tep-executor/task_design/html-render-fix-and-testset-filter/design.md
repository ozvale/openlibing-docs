# HTML渲染修复与XML路径过滤功能增加 — 技术设计

## 方案概述

本需求包含两个独立功能:
1. **HTML渲染修复**: 将UniAutos框架生成的HTML头部CSS/JS引用改为内嵌方式,移除内网资源依赖
2. **XML路径过滤**: 在executor中新增testXmlPaths配置,过滤testset xml文件路径范围

两个功能跨仓实现:openlibing-tep-executor(业务仓) + UniAutosPython3(框架仓)

## 架构决策

### 决策1: HTML混合方案(外网CDN + 内嵌)

**问题**: HTML文件体积增加显著(TestCase日志+256KB, Main日志+1.2MB),需在外网正常显示

**方案选项**:
1. **全部内嵌**: 所有CSS/JS内嵌到HTML头部(体积过大)
2. **全部外网CDN**: 所有资源使用外网CDN(依赖外部服务稳定性)
3. **混合方案**: jquery使用外网CDN,CSS/Main.js内嵌,echarts内嵌(推荐)

**决策**: 采用方案3"混合方案"
- TestCase日志: 内嵌CSS(2KB) + Main.js(19KB) + 外网CDN jquery ≈ 21KB
- Main日志: 内嵌CSS(2KB) + Main.js(19KB) + 外网CDN jquery + 内嵌echarts(972KB) ≈ 993KB
- jquery CDN: `https://apps.bdimg.com/libs/jquery/2.1.4/jquery.min.js` (百度CDN,国内访问快)

**决策依据**:
- jquery使用外网CDN,体积约84KB(压缩版),但不需内嵌,HTML体积大幅减小
- CSS和Main.js体积小(21KB),内嵌不影响传输,且无外部依赖风险
- echarts体积大(972KB),但Main日志较少使用,内嵌仍可接受
- 百度CDN在国内访问稳定,外网环境可正常加载

**实现方式**:
- LogFormat.py新增静态方法`_read_static_file(filename)`读取CSS/Main.js
- `formatHtmlHead`方法: jquery改为外网CDN引用,CSS内嵌到`<head>`
- 新增`formatHtmlBodyScript`方法: Main.js/echarts内嵌到`</body>`前
- 保持原有逻辑: Main日志加载echarts(TestCase日志不加载)

### 决策2: XML路径过滤配置参数设计

**问题**: 如何传递testset xml路径过滤参数

**方案选项**:
1. **复用testPaths**: 同一参数既过滤testset xml又过滤testcase file_path
2. **新增testXmlPaths**: 独立参数专门过滤testset xml路径
3. **统一为paths**: 单一参数过滤所有路径相关场景

**决策**: 采用方案2"新增testXmlPaths"
- 原因: testset xml路径和testcase file_path语义不同,独立配置更清晰
- 向后兼容: testXmlPaths为可选字段,未配置时默认处理所有testset xml

**实现方式**:
- executor.py新增`self.test_xml_paths = []`成员变量
- `accept_para`方法解析配置JSON中的`testXmlPaths`字段
- `_get_all_testset_files`方法新增路径过滤逻辑(类似`_is_file_path_in_test_paths`)

### 决策3: 跨仓协作方式

**问题**: UniAutosPython3框架仓修改如何同步到openlibing-tep-executor

**方案选项**:
1. **框架独立发布**: UniAutosPython3独立版本发布,executor更新依赖版本
2. **统一PR提交**: 两个仓的修改通过同一个Issue关联,分别提交PR
3. **先框架后业务**: 先完成UniAutosPython3修改并发布,再修改executor

**决策**: 采用方案3"先框架后业务"
- 原因: UniAutosPython3是独立框架仓,需先发布新版本
- executor再依赖新版本框架,确保HTML生成逻辑已更新
- Issue关联: 两个仓的PR都关联Issue #18,跨仓引用使用`openlibing/openlibing-tep-executor#18`

## 涉及文件

### UniAutosPython3仓库

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/Framework/Dev/lib/UniAutos/Log/LogFormat.py` | 修改 | 新增_read_static_file、formatHtmlBodyScript方法,修改formatHtmlHead方法 |
| `src/Framework/Dev/lib/UniAutos/Log/Appender.py` | 修改 | 调用formatHtmlBodyScript生成bodyScript |
| `src/Framework/Dev/lib/UniAutos/Log/html/MainStyle.css` | 读取 | 作为内嵌内容源(不修改文件本身) |
| `src/Framework/Dev/lib/UniAutos/Log/html/Main.js` | 读取 | 作为内嵌内容源(不修改文件本身) |
| `src/Framework/Dev/lib/UniAutos/Log/html/echarts-all.js` | 读取 | 作为内嵌内容源(仅Main日志加载) |

### openlibing-tep-executor仓库

| 文件 | 操作 | 说明 |
|------|------|------|
| `tepexecor_frame/executor.py` | 修改 | 新增test_xml_paths成员、accept_para解析、_get_all_testset_files过滤 |
| `tepexecor_frame/cte/utils.py` | 不修改 | get_metadata_info_from_testset保持不变 |

## 关键设计细节

### LogFormat.py修改方案

**当前实现**:
```python
def formatHtmlHead(logType):
    cssList = ['MainStyle.css']
    scriptList = ['jquery-1.6.1.js', 'Main.js', 'echarts-all.js']
    scriptPath = 'http://taas.inhuawei.com/uniautos-log/logstatic/'
    # 生成<link>和<script src>标签
```

**修改后实现**:

1. **新增`_read_static_file`方法**:
```python
def _read_static_file(filename):
    """读取html目录下的静态资源文件

    Args:
        filename (string): 静态资源文件名

    Returns:
        string: 文件内容,若文件不存在则返回空字符串
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_dir = os.path.join(base_dir, "html")
    filepath = os.path.join(html_dir, filename)

    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logging.getLogger(__name__).error(
                "Static file not found: %s, HTML may lose styles/functions", filepath)
            return ""
    except Exception as e:
        logging.getLogger(__name__).error(
            "Failed to read static file %s: %s, HTML may lose styles/functions",
            filepath, str(e))
        return ""
```

2. **修改`formatHtmlHead`方法**:
```python
def formatHtmlHead(logType):
    """根据日志类型，生成不同的Html头(支持外网渲染)

    Returns:
        string: Html头信息（仅包含CSS和jquery CDN）
    """
    # jquery使用外网CDN(百度CDN)
    jquery_cdn_url = "https://apps.bdimg.com/libs/jquery/2.1.4/jquery.min.js"

    # 内嵌CSS
    css_content = _read_static_file("MainStyle.css")

    # 生成内嵌<style>标签
    cssHtml = ""
    if css_content:
        cssHtml = "<style type=\"text/css\">\n" + css_content + "\n</style>"

    # <head>只包含jquery CDN，不包含内嵌script
    headScriptHtml = "<script type=\"text/javascript\" src=\"" + jquery_cdn_url + "\"></script>"

    return logFormatDic["htmlHead"].format(css=cssHtml, headScript=headScriptHtml)
```

3. **新增`formatHtmlBodyScript`方法**:
```python
def formatHtmlBodyScript(logType):
    """根据日志类型，生成</body>前的script部分

    Returns:
        string: </body>前的script内容
    """
    # 内嵌Main.js（确保jquery已加载）
    main_js_content = _read_static_file("Main.js")

    # 生成内嵌<script>标签
    bodyScriptHtml = ""
    if main_js_content:
        bodyScriptHtml = "<script type=\"text/javascript\">\n" + main_js_content + "\n</script>"

    # Main日志类型额外内嵌echarts
    if logType is Enum.LogType.Main:
        echarts_content = _read_static_file("echarts-all.js")
        if echarts_content:
            bodyScriptHtml += "\n<script type=\"text/javascript\">\n" + echarts_content + "\n</script>"

    return bodyScriptHtml
```

4. **模板变更**:
```python
logFormatDic = {
    # {script} 改为 {headScript}
    'htmlHead': '<html><head>...{css}{headScript}<body>...',
    # 新增 {bodyScript}
    'htmlTail': '</table></div>{bodyScript}</body></html>'
}
```

### Appender.py修改方案

```python
def __init__(self, logType, fileName, baseConfig, log_id=None, test_set_info=None):
    htmlHead = LogFormat.formatHtmlHead(logType)
    bodyScript = LogFormat.formatHtmlBodyScript(logType)  # 新增
    htmlTail = LogFormat.logFormatDic['htmlTail'].format(bodyScript=bodyScript)  # 修改
    if fileName not in Appender._loggerDict:
        handler = ExtendFileHandler(baseConfig, fileName, htmlHead, htmlTail)
```

### executor.py修改方案

**新增成员变量**:
```python
class Executor:
    def __init__(self):
        ...
        self.test_xml_paths = []  # 新增:testset xml路径过滤参数
```

**accept_para解析testXmlPaths**:
```python
def accept_para(self):
    ...
    test_xml_paths_raw = config_json_data.get("testXmlPaths", [])
    # 多config场景:合并所有config的testXmlPaths
    if self.config_list:
        all_test_xml_paths = []
        for config_item in self.config_list:
            test_xml_paths_item = config_item.get("testXmlPaths", [])
            if isinstance(test_xml_paths_item, list):
                all_test_xml_paths.extend(test_xml_paths_item)
        if all_test_xml_paths:
            test_xml_paths_raw = list(dict.fromkeys(all_test_xml_paths))

    self.test_xml_paths = []
    for p in test_xml_paths_raw:
        normalized = p.replace("\\", "/")
        if not normalized.endswith("/"):
            normalized += "/"
        self.test_xml_paths.append(normalized)
```

**_get_all_testset_files增加过滤**:
```python
def _get_all_testset_files(self):
    ...
    # 获取所有testset xml文件
    _tmp_testset_files = utils.get_files(scripts_dir, r'testSet.*\.xml', ['.git'], root_dir=test_set_dir)
    tep_executor_logger.info(f"[TEST_SET] _tmp_testset_files before filter: {_tmp_testset_files}")

    # 新增:路径过滤
    if self.test_xml_paths:
        filtered_files = []
        for testset_file in _tmp_testset_files:
            normalized_path = testset_file.replace("\\", "/")
            for path in self.test_xml_paths:
                if normalized_path.startswith(path):
                    filtered_files.append(testset_file)
                    break
        _tmp_testset_files = filtered_files
        tep_executor_logger.info(f"[TEST_SET] _tmp_testset_files after filter: {_tmp_testset_files}")

    return _tmp_testset_files
```

## 风险 & 缓解

### 风险1: 外网CDN依赖风险

**风险描述**: jquery使用百度外网CDN,若CDN服务不可用可能导致交互功能失效

**缓解措施**:
- 百度CDN在国内访问稳定,历史可用性高
- 降级方案: 若CDN加载失败,HTML样式(CSS内嵌)仍可正常显示,仅交互功能受影响
- 后续可增加备用CDN源或本地降级加载机制

**体积优势**: TestCase日志仅增加21KB(内嵌CSS+Main.js), Main日志993KB(含内嵌echarts)

### 风险2: 静态资源文件路径依赖

**风险描述**: LogFormat.py依赖html目录下的静态资源文件,若目录结构变化可能导致内嵌失败

**缓解措施**:
- 在`_read_static_file`中增加文件存在性检查和异常处理
- 若静态资源文件缺失,记录错误日志并降级为空内容(HTML仍可生成,但样式丢失)
- UniAutosPython3发布时,明确标注html目录为必需资源

### 风险3: testXmlPaths配置错误导致元数据为空

**风险描述**: 用户配置错误的testXmlPaths,导致所有testset xml被过滤,metadata.xml为空

**缓解措施**:
- 在`_get_all_testset_files`中增加日志: 记录过滤前后的testset文件数量
- 若过滤后testset文件为空,记录警告日志但不抛异常(保持原有容错逻辑)
- 文档中明确说明testXmlPaths为可选字段,未配置时默认处理所有文件

### 风险4: 跨仓协作版本依赖问题

**风险描述**: executor依赖新版本UniAutosPython3,若版本未同步可能导致HTML生成逻辑不一致

**缓解措施**:
- UniAutosPython3先发布新版本,明确标注版本号(如v1.2.0)
- executor在requirements.txt或依赖配置中明确版本号
- 提供回退方案: 若框架版本未更新,executor仍可运行(testXmlPaths功能不影响)

## 跨仓影响

### UniAutosPython3 → openlibing-tep-executor

**接口变化**:
- 新增`formatHtmlBodyScript`方法,需在Appender.py中调用
- `formatHtmlHead`返回内容变化(仅CSS+jquery CDN)
- `logFormatDic['htmlTail']`模板新增`{bodyScript}`占位符

**数据变化**:
- executor生成的HTML文件体积增加
- OBS上传的日志压缩包体积增加

### openlibing-tep-executor → UniAutosPython3

**无反向依赖**: executor的testXmlPaths功能不影响UniAutosPython3框架

### 其他仓影响

**无影响**: 其他业务仓若使用UniAutosPython3框架,HTML生成逻辑同步变化,但无需额外修改

## 测试策略

### HTML渲染测试

**测试场景**:
1. 外网环境访问TestCase日志HTML,验证样式和交互功能
2. 外网环境访问Main日志HTML,验证图表功能(echarts)
3. 浏览器兼容性: Chrome/Firefox/Edge
4. HTML文件体积对比: 新旧HTML文件大小差异

**验证命令**:
```bash
# 生成测试日志
python tepexecor_frame/main.py --task_project_id test --env_param ... --config cli/test.json

# 对比HTML文件体积
ls -lh tepexecor_frame/config/cases_log/*.html

# 外网访问验证(需实际部署后验证)
curl -I https://obs.xxx/test_log.html
```

### XML路径过滤测试

**测试场景**:
1. testXmlPaths为空: 验证处理所有testset xml(默认行为)
2. testXmlPaths配置单个路径: 验证只处理匹配路径的testset xml
3. testXmlPaths配置多个路径: 验证多路径过滤
4. testXmlPaths配置错误路径: 验证日志警告和metadata.xml为空

**验证命令**:
```bash
# 配置testXmlPaths
cat cli/test_with_testXmlPaths.json
{
  "testXmlPaths": ["Testcases/02_MindIE_LLM1/"],
  ...
}

# 执行并查看日志
python tepexecor_frame/main.py --task_project_id test ... --config cli/test_with_testXmlPaths.json

# 查看metadata.xml内容
cat tepexecor_frame/config/cases_log/metadata_test.xml
```

### 集成测试

**测试场景**:
1. 同时启用两个功能: HTML内嵌 + testXmlPaths过滤
2. 向后兼容: 使用旧配置文件(不含testXmlPaths)执行,验证默认行为
3. 多config场景: 不同config配置不同testXmlPaths,验证合并过滤

## 部署方案

### UniAutosPython3部署

1. 修改LogFormat.py和Appender.py
2. 本地测试验证HTML生成
3. 提交PR到UniAutosPython3主干
4. 发布新版本(如v1.2.0)

### openlibing-tep-executor部署

1. 更新UniAutosPython3依赖版本号
2. 修改executor.py
3. 本地测试验证testXmlPaths功能
4. 提交PR到openlibing-tep-executor主干

### 回退方案

若UniAutosPython3新版本有问题,executor可临时回退到旧版本框架(testXmlPaths功能仍可用)

## 文档同步需求

### 需更新文档

1. **UniAutosPython3 README**: 说明HTML内嵌CSS/JS的变化
2. **openlibing-tep-executor README**: 说明testXmlPaths配置参数用法
3. **配置示例文档**: 提供含testXmlPaths的配置JSON示例
4. **迁移指南**: 说明旧配置无需修改,向后兼容

## 实现优先级

| 优先级 | 任务 | 原因 |
|--------|------|------|
| P0 | UniAutosPython3 LogFormat.py修改 | HTML渲染是主要痛点,优先解决 |
| P1 | UniAutosPython3版本发布 | executor依赖新版本框架 |
| P2 | executor testXmlPaths功能 | 次要功能,可在框架更新后实现 |
| P3 | 文档同步 | 交付后补充 |

## 设计偏差与取舍

1. **未采用JS压缩方案**: 当前直接内嵌原始JS文件,体积较大;后续可优化为压缩版本
2. **未提供testXmlPaths正则匹配**: 当前只支持路径前缀匹配,后续可扩展为正则表达式匹配
3. **已移除内网URL引用**: 原taas.inhuawei.com的URL常量已删除,不再依赖内网资源

## 实现状态

### UniAutosPython3 (已完成)

提交: `a5f6a753493860c01f83043ca519974fd3e3e5bb`

修改内容:
- LogFormat.py: 新增`_read_static_file`、`formatHtmlBodyScript`方法,修改`formatHtmlHead`方法
- Appender.py: 调用`formatHtmlBodyScript`生成bodyScript
- Main.js: 微调(8行变更)