# 背景

目前页面支持配置的代码仓类型有： gitcode gitee github 现在gitcode代码仓域名进行了新增：gitcode.com 和 atomgit.com 都属于gitcode的代码仓
所以现在需要进行相关代码的适配，当用户输入的代码仓url中包含gitcode.com 或 atomgit.com时，都需要解析为gitcode的代码仓类型。

# 要求

1. 请对整仓代码进行扫描适配，确保在解析代码仓类型时能够正确识别gitcode的代码仓。
2. 请先给出适配方案和具体的代码修改点，在当前文件夹下生成设计文档design-xxx.md,要求设计文档基于代码仓分离，一个代码仓生成一个详细的设计文档
3. 本次涉及的改造仓有：openlibing-coderepo、openlibing-codecheck、openlibing-cicd
4. 最后请基于：openlibing-ai-engineering\personal-skills\common\design\FE-design下的md格式要求重新生成 一个简化版的 设计文档，不确定的点需要指出，里面包含三大仓的修改点和注意点

# 补充

以下代码就是需要适配的一个点，请你全局扫描整仓代码，找到所有相关的代码修改点。

```
  public static String parsePlatformFromUrl(String url) {
    if (StringUtils.isBlank(url)) {
      return "";
    }
    String lowerUrl = url.toLowerCase(Locale.ROOT);
    if (lowerUrl.contains("gitcode.com")) {
      return ProjectConstant.RepoPlatform.PLATFORM_GITCODE;
    }
    if (lowerUrl.contains("gitee.com")) {
      return ProjectConstant.RepoPlatform.PLATFORM_GITEE;
    }
    if (lowerUrl.contains("github.com")) {
      return ProjectConstant.RepoPlatform.PLATFORM_GITHUB;
    }
    return "";
  }
```
