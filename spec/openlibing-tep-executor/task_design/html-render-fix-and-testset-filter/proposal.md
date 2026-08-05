# HTML渲染修复与XML路径过滤功能增加

## 需求背景

Issue链接: https://gitcode.com/openlibing/openlibing-tep-executor/issues/18

当前测试结果HTML文件依赖内网CSS和JavaScript资源:
- CSS: `http://taas.inhuawei.com/uniautos-log/logstatic/MainStyle.css`
- JS: `jquery-1.6.1.js`, `Main.js`, `echarts-all.js`
- 资源路径: `http://taas.inhuawei.com/uniautos-log/logstatic/`

**问题**: 在外网环境访问HTML时,CSS/JS资源无法加载,导致HTML无法正常显示,严重影响测试结果的查看和分享。

此外,当前`get_testcase_metadata`方法在收集元数据时,只支持过滤testcase的file_path,不支持过滤testset xml文件本身的路径,导致无法按路径范围精确收集指定目录下的testset元数据。

## 功能描述

### 功能1: HTML渲染修复

移除HTML对内网CSS/JS资源的依赖,改为内嵌方式:
- 将CSS/JS内容直接嵌入HTML头部
- HTML文件无需外部依赖,在任何网络环境均可正常显示
- 保持原有HTML功能和样式完全一致

**静态资源说明**:
- TestCase日志: 需嵌入 `MainStyle.css`(2KB) + `jquery-1.6.1.js`(235KB) + `Main.js`(19KB) ≈ 256KB
- Main日志: 额外需嵌入 `echarts-all.js`(972KB),总计约1.2MB

### 功能2: XML路径过滤

支持指定xml路径,在`get_testcase_metadata`收集云数据时过滤testset xml文件:
- 新增配置参数 `testsetPaths`,用于指定testset xml文件的路径范围
- 只处理路径匹配的testset xml文件,提高元数据收集的精确性和效率
- 与现有`testPaths`参数区分:testsetPaths过滤testset文件,testPaths过滤testcase file_path

**不做什么**:
- 不修改HTML内容生成逻辑,只修改HTML头部CSS/JS引用方式
- 不改变testcase file_path过滤逻辑(`_is_file_path_in_test_paths`保持不变)
- 不移除echarts图表功能,Main日志类型仍支持加载echarts(仅改为内嵌方式)

## 验收标准

### 功能1验收标准
- [ ] HTML在外网环境可正常显示,样式和交互功能完整
- [ ] TestCase日志HTML内嵌CSS+jquery+Main.js,文件体积增加约256KB
- [ ] Main日志HTML内嵌CSS+jquery+Main.js+echarts,文件体积增加约1.2MB
- [ ] 原有HTML功能不受影响:表格展开/折叠、日志级别筛选、时间戳排序等
- [ ] 主流浏览器兼容性验证:Chrome/Firefox/Edge正常显示

### 功能2验收标准
- [ ] 配置JSON支持新增`testsetPaths`字段,类型为字符串数组
- [ ] `testsetPaths`为空或未配置时,默认处理所有testset xml文件(保持原有行为)
- [ ] `testsetPaths`配置后,只处理路径前缀匹配的testset xml文件
- [ ] 元数据XML中只包含路径过滤后的testcase信息
- [ ] 多config场景下,各config可独立配置`testsetPaths`,互不影响
- [ ] 错误路径配置时,记录警告日志但不影响流程,metadata.xml仍可生成(内容为空或部分testcase)

### 综合验收标准
- [ ] 两个功能互不干扰,可独立启用或同时启用
- [ ] 不影响原有测试执行流程和结果上报流程
- [ ] 向后兼容:旧配置文件(不含testsetPaths)仍可正常运行

## 影响范围

### 跨仓影响

**涉及仓库**:
- **openlibing-tep-executor** (主仓): executor.py新增testsetPaths处理逻辑
- **UniAutosPython3** (框架仓): LogFormat.py修改HTML头部生成逻辑

**接口契约变化**:
- 配置JSON新增可选字段`testsetPaths`,向后兼容
- HTML头部结构变化(内嵌CSS/JS),不影响HTML内容解析

### 模块影响

**openlibing-tep-executor**:
- `tepexecor_frame/executor.py`: `_get_all_testset_files`方法增加路径过滤参数
- `tepexecor_frame/executor.py`: `accept_para`方法解析`testsetPaths`配置
- `tepexecor_frame/executor.py`: `get_testcase_metadata`方法传递testsetPaths参数

**UniAutosPython3**:
- `src/Framework/Dev/lib/UniAutos/Log/LogFormat.py`: `formatHtmlHead`方法改为内嵌CSS/JS
- `src/Framework/Dev/lib/UniAutos/Log/html/`: 静态资源文件作为内嵌内容读取源

### 数据影响

- 元数据XML内容变化:根据testsetPaths过滤后生成,可能减少testcase数量
- HTML文件体积增加:TestCase日志约256KB,Main日志约1.2MB

### 部署影响

- UniAutos框架升级后,需同步更新openlibing-tep-executor依赖
- 旧HTML文件仍可访问(外网显示问题依然存在),新HTML文件外网可正常显示
- 无配置迁移需求:testsetPaths为可选字段,旧配置无需修改

## 参考方案

### HTML混合方案参考

**外网CDN jquery**:
```html
<script type="text/javascript" src="https://apps.bdimg.com/libs/jquery/2.1.4/jquery.min.js"></script>
```

**内嵌CSS示例**:
```html
<style type="text/css">
/* MainStyle.css内容 */
body { font-family: Arial, sans-serif; }
...
</style>
```

**内嵌Main.js示例**:
```html
<script type="text/javascript">
// Main.js内容
$(document).ready(function() {
...
});
</script>
```

### XML路径过滤方案参考

配置示例:
```json
{
  "testsetPaths": ["Testcases/02_MindIE_LLM1/", "Testcases/03_MindIE_LLM2/"],
  "testPaths": ["scripts/Testcases/02_MindIE_LLM1/"],
  ...
}
```

过滤逻辑:
```python
def _is_testset_path_match(testset_file: str, testset_paths: list) -> bool:
    if not testset_paths:
        return True
    normalized_path = testset_file.replace("\\", "/")
    for path in testset_paths:
        if normalized_path.startswith(path):
            return True
    return False
```