## Context

当前系统已有完善的 Skill 管理能力：
- `skill_parser.py` 可解析 SKILL.md 的 frontmatter 元数据
- `git_client.py` 可克隆 Git 仓库
- `SkillRepository.upsert_skill()` 可创建或更新 Skill

需要新增从 Git 仓库 URL 导入 Skill 的能力，支持 GitHub 和 GitCode 两个平台，采用预览+确认两步操作模式。

## Goals / Non-Goals

**Goals:**
- 支持通过 URL 导入 Skill，自动识别 GitHub/GitCode 平台
- 仅支持公开仓库导入
- 递归扫描仓库中所有 SKILL.md 文件
- 预览模式：先展示可导入的 Skill 列表和冲突信息
- 确认导入：批量写入数据库，冲突时报错

**Non-Goals:**
- 不支持增量同步（每次导入都是全新扫描）
- 不支持自动定时同步
- 不支持 GitLab、Gitee 等其他平台

## Decisions

### 1. API 设计：预览 + 确认两步

**选择**：两个独立 API
- `POST /api/admin/skills/import/preview` - 预览
- `POST /api/admin/skills/import` - 确认导入

**原因**：
- 用户可以在导入前查看将要导入的内容
- 可以发现冲突并决定如何处理
- 避免误操作导入不需要的 Skill

**备选方案**：单 API 直接导入
- 缺点：无法预览，用户体验差

### 2. 平台识别：URL 域名解析

**选择**：通过 URL 域名自动识别平台
- `github.com` → GitHub
- `gitcode.com` → GitCode

**原因**：
- 用户无需额外指定平台
- 实现简单，解析 URL 即可

### 3. 临时目录管理

**选择**：使用系统临时目录，导入完成后清理

**原因**：
- 避免占用项目空间
- 自动清理，不留垃圾文件

**实现**：
```python
import tempfile
with tempfile.TemporaryDirectory() as tmp_dir:
    # clone 仓库到 tmp_dir
    # 扫描 SKILL.md
    # 导入完成后自动清理
```

### 4. source_url 格式

**选择**：指向具体的 SKILL.md 文件

**格式**：
- GitHub: `https://github.com/{owner}/{repo}/blob/{branch}/{path}/SKILL.md`
- GitCode: `https://gitcode.com/{owner}/{repo}/blob/{branch}/{path}/SKILL.md`

**原因**：
- 用户可以直接跳转到源文件
- 便于追溯 Skill 来源

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 大仓库克隆耗时较长 | 设置超时时间，前端显示加载状态 |
| 临时目录磁盘占用 | 使用 tempfile 自动清理，设置仓库大小限制 |
| SKILL.md 格式不规范 | 使用现有 skill_parser 容错处理，解析失败则跳过 |
| 网络问题导致克隆失败 | 返回明确错误信息，建议用户检查网络 |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Import Flow                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   Router     │────▶│   Service    │────▶│  Repository  │        │
│  │ (import.py)  │     │(import_      │     │ (skill_repo) │        │
│  │              │     │ service.py)  │     │              │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│         │                    │                    │                │
│         │                    ▼                    │                │
│         │            ┌──────────────┐             │                │
│         │            │  git_client  │             │                │
│         │            │  (clone)     │             │                │
│         │            └──────────────┘             │                │
│         │                    │                    │                │
│         │                    ▼                    │                │
│         │            ┌──────────────┐             │                │
│         │            │skill_parser  │             │                │
│         │            │(parse .md)   │             │                │
│         │            └──────────────┘             │                │
│         │                                         │                │
│         ▼                                         ▼                │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                    Database (SQLite/MySQL)                │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```
