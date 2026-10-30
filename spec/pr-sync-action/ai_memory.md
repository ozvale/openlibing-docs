# pr-sync-action — AI 协作经验记忆

## Windows / PowerShell 中文编码（高优先级，多次踩坑）

- 含中文的文件读写必须显式 UTF-8：`Get-Content` 默认按系统 ANSI(GBK) 解码 UTF-8 文件，
  读后再写回会产生双重编码乱码（2026-10 pre-commit.yml 乱码事故）；优先用工具链的
  read/edit/write 能力，PowerShell 读写显式加 `-Encoding UTF8`。
- ⚠️ PowerShell 5.1 的 `-Encoding UTF8` 写出的是 **UTF-8 with BOM**：`git commit -F` /
  `--body-file` 会把 BOM 当作正文首字符（javac 等编译器也会报"非法字符 \ufeff"）。
  无 BOM 写法：`[System.IO.File]::WriteAllText($path, $content, (New-Object
System.Text.UTF8Encoding($false)))`，或改用 PowerShell 7 的 `-Encoding utf8NoBOM`。
- `git commit -m "<中文>"` 经 PowerShell 传参存在乱码风险；含中文的提交信息用
  `git commit -F <无 BOM UTF-8 文件>`。已合入仓库的提交信息经核验均为英文，无乱码。
- GitCode 远端写操作（issue/PR 评论、body）含中文必须 `--body-file` + 显式 UTF-8 写盘，
  禁止 `--body` 直接传中文变量。

## GitCode Actions 触发器语义

- `pull_request_comment.comments` 数组为多值 OR，每个值按正则对评论全文做包含匹配
  （非精确相等）；YAML 双引号中正则的反斜杠需写成 `\\`，单引号原样保留。
- `pull_request_target` 的 `branches` 过滤的是目标分支；通配符 `*` 不匹配含 `/` 的
  分支名，需用 `**`（官方文档明确）。
- workflow 引用的分支名必须与目标仓默认分支对齐（main/master 混用时事件不触发）。

## GitCode 双域名口径（gitcode.com / atomgit.com）

- 平台 API 与 webhook payload 恒定返回 gitcode.com；atomgit.com 只是用户录入/网页
  访问的别名域名。需要适配的是「识别与匹配」（坐标口径 repoType+owner+repo，域名
  无关），而不是切换 API 出站域名。
- 已知坑：按 repo_url 全串精确匹配反查 token/配置的代码，在跨域名录入场景会失配
  （PrAccessTokenServiceImpl 曾中招）；新增此类查询必须走 RepoCoordinateResolver/
  RepoInfoCoordinateResolver 坐标兜底。
- GitCode webhook 载荷中 `project.name` / `project.namespace` 是展示名（display
  name），路径要用 `project.path`、`path_with_namespace` 或从 `git_http_url` 反解；
  `MergeRequestEventHandler` 有现成的正确实现可参考。

## 插件发布与安全基线

- pr-sync-action 仅支持 OIDC 免密认证（AppCode 回退已禁用）；新工作流必须声明
  `permissions: id-token: write`，否则插件跳过执行。
- 工作流 `branches` 与 runner 标签（`codearts-hosted` 托管池已验证可用）接入新仓时
  按目标仓实际情况对齐；组织共享 K8s 池的标签体系（default/arch=x86/cpu=N）与托管
  池是两套，切换前需实测 id-token 注入与出网能力。
