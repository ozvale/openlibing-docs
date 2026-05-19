# Spec: File Tree URLs

**Change ID**: skill-market-sync
**Feature**: 文件树超链接跳转

## Scenario 1: Skill 详情返回带 URL 的文件树

**GIVEN** 数据库中存在一个 Skill，其 `source_url` 为 `https://github.com/owner/repo/blob/main/skills/my-skill/SKILL.md`，`file_tree` 为 `["SKILL.md", "README.md", "scripts/run.sh"]`

**WHEN** 调用 `GET /api/skills/my-skill`

**THEN** 响应中 `fileTreeWithUrls` 字段包含：
```json
[
  {"path": "SKILL.md", "url": "https://github.com/owner/repo/blob/main/skills/my-skill/SKILL.md"},
  {"path": "README.md", "url": "https://github.com/owner/repo/blob/main/skills/my-skill/README.md"},
  {"path": "scripts/run.sh", "url": "https://github.com/owner/repo/blob/main/skills/my-skill/scripts/run.sh"}
]
```

## Scenario 2: GitCode 平台的文件树 URL

**GIVEN** 数据库中存在一个 Skill，其 `source_url` 为 `https://gitcode.com/owner/repo/blob/main/skills/my-skill/SKILL.md`

**WHEN** 调用 `GET /api/skills/my-skill`

**THEN** 响应中 `fileTreeWithUrls` 的 URL 使用 GitCode 域名：
```json
[
  {"path": "SKILL.md", "url": "https://gitcode.com/owner/repo/blob/main/skills/my-skill/SKILL.md"}
]
```

## Scenario 3: Skill 无 source_url

**GIVEN** 数据库中存在一个 Skill，其 `source_url` 为 `null`

**WHEN** 调用 `GET /api/skills/that-skill`

**THEN** 响应中 `fileTreeWithUrls` 为 `null`

## Scenario 4: Skill 无 file_tree

**GIVEN** 数据库中存在一个 Skill，其 `file_tree` 为 `null`

**WHEN** 调用 `GET /api/skills/that-skill`

**THEN** 响应中 `fileTreeWithUrls` 为 `null`

## Scenario 5: 向后兼容

**GIVEN** 旧版前端调用 `GET /api/skills/my-skill`

**WHEN** 收到响应

**THEN** `fileTree` 字段仍然存在且格式不变，`fileTreeWithUrls` 为新增字段
