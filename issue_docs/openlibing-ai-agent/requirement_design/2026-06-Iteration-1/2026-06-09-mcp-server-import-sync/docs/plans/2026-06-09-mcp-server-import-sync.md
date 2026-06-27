# MCP Server 导入与同步实现计划

> **给 Claude：** 必须使用 superpowers:executing-plans 逐任务执行本计划。

**目标：** 实现 MCP Server 导入（预览 + 确认）和定时同步更新功能，参照现有 Skill 导入/同步模式，但使用 MCP 特有的解析逻辑。

**架构：** 克隆仓库到临时目录，扫描根目录下所有子目录作为 MCP Server 候选项，逐目录解析 mcp-rpm.yaml / mcp_config.json / README.md。同步使用独立的 cron 配置、独立的锁，按来源仓库分组以实现每个仓库只克隆一次。

**技术栈：** FastAPI, SQLAlchemy (async), GitPython, PyYAML (新增依赖), APScheduler, aiosmtplib

---

### 任务 1：添加 PyYAML 依赖

**文件：**
- 修改：`pyproject.toml`

**步骤 1：在依赖列表中添加 pyyaml**

在 `pyproject.toml` 的 `dependencies` 列表中添加 `"pyyaml>=6.0"`。

**步骤 2：安装依赖**

运行：`pip install pyyaml>=6.0`

**步骤 3：提交**

```bash
git add pyproject.toml
git commit -m "chore(deps): add pyyaml for mcp-rpm.yaml parsing"
```

---

### 任务 2：创建 MCP Server 配置解析工具

**文件：**
- 新建：`app/utils/mcp_parser.py`
- 测试：`tests/test_mcp_parser.py`

**步骤 1：编写 mcp_parser 的失败测试**

创建 `tests/test_mcp_parser.py`：

```python
import json
import tempfile
from pathlib import Path

import pytest

from app.utils.mcp_parser import (
    parse_mcp_server_dir,
    parse_mcp_config_json,
    parse_mcp_rpm_yaml,
    find_readme_content,
)


class TestParseMcpRpmYaml:
    @staticmethod
    def test_parse_valid_yaml(tmp_path):
        yaml_file = tmp_path / "mcp-rpm.yaml"
        yaml_file.write_text("name: My MCP Server\ndescription: A test server\n", encoding="utf-8")
        result = parse_mcp_rpm_yaml(yaml_file)
        assert result is not None
        assert result["name"] == "My MCP Server"
        assert result["description"] == "A test server"

    @staticmethod
    def test_parse_missing_yaml(tmp_path):
        result = parse_mcp_rpm_yaml(tmp_path / "nonexistent.yaml")
        assert result is None

    @staticmethod
    def test_parse_yaml_missing_name(tmp_path):
        yaml_file = tmp_path / "mcp-rpm.yaml"
        yaml_file.write_text("description: No name field\n", encoding="utf-8")
        result = parse_mcp_rpm_yaml(yaml_file)
        assert result is not None
        assert result["name"] is None
        assert result["description"] == "No name field"

    @staticmethod
    def test_parse_invalid_yaml(tmp_path):
        yaml_file = tmp_path / "mcp-rpm.yaml"
        yaml_file.write_text("{{invalid yaml}}\n", encoding="utf-8")
        result = parse_mcp_rpm_yaml(yaml_file)
        assert result is None


class TestParseMcpConfigJson:
    @staticmethod
    def test_parse_local_config(tmp_path):
        json_file = tmp_path / "mcp_config.json"
        config = {
            "mcpServers": {
                "my-server": {
                    "command": "python",
                    "args": ["server.py"],
                    "env": {"PORT": "8080"},
                }
            }
        }
        json_file.write_text(json.dumps(config), encoding="utf-8")
        result = parse_mcp_config_json(json_file, "my-server")
        assert result is not None
        assert result["local_server_config"] is not None
        assert result["remote_server_config"] is None
        local = json.loads(result["local_server_config"])
        assert "my-server" in local["mcpServers"]

    @staticmethod
    def test_parse_remote_config(tmp_path):
        json_file = tmp_path / "mcp_config.json"
        config = {
            "mcpServers": {
                "my-server": {
                    "url": "http://example.com/mcp",
                    "headers": {"Authorization": "Bearer token"},
                }
            }
        }
        json_file.write_text(json.dumps(config), encoding="utf-8")
        result = parse_mcp_config_json(json_file, "my-server")
        assert result is not None
        assert result["local_server_config"] is None
        assert result["remote_server_config"] is not None

    @staticmethod
    def test_parse_mixed_config(tmp_path):
        json_file = tmp_path / "mcp_config.json"
        config = {
            "mcpServers": {
                "my-server": {
                    "command": "python",
                    "args": ["server.py"],
                },
                "my-server-remote": {
                    "url": "http://example.com/mcp",
                },
            }
        }
        json_file.write_text(json.dumps(config), encoding="utf-8")
        result = parse_mcp_config_json(json_file, "my-server")
        assert result is not None
        assert result["local_server_config"] is not None
        assert result["remote_server_config"] is not None
        local = json.loads(result["local_server_config"])
        remote = json.loads(result["remote_server_config"])
        assert "my-server" in local["mcpServers"]
        assert "my-server-remote" in remote["mcpServers"]

    @staticmethod
    def test_parse_key_correction(tmp_path):
        json_file = tmp_path / "mcp_config.json"
        config = {
            "mcpServers": {
                "wrong-key": {
                    "command": "python",
                    "args": ["server.py"],
                }
            }
        }
        json_file.write_text(json.dumps(config), encoding="utf-8")
        result = parse_mcp_config_json(json_file, "correct-name")
        assert result is not None
        local = json.loads(result["local_server_config"])
        assert "correct-name" in local["mcpServers"]
        assert "wrong-key" not in local["mcpServers"]

    @staticmethod
    def test_parse_missing_json(tmp_path):
        result = parse_mcp_config_json(tmp_path / "nonexistent.json", "my-server")
        assert result is None

    @staticmethod
    def test_parse_invalid_json(tmp_path):
        json_file = tmp_path / "mcp_config.json"
        json_file.write_text("{invalid json}", encoding="utf-8")
        result = parse_mcp_config_json(json_file, "my-server")
        assert result is None


class TestFindReadmeContent:
    @staticmethod
    def test_find_readme_md(tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# My Server\n\nDescription here", encoding="utf-8")
        result = find_readme_content(tmp_path)
        assert result is not None
        assert "My Server" in result

    @staticmethod
    def test_find_readme_in_src(tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        readme = src_dir / "README.md"
        readme.write_text("# Src Readme", encoding="utf-8")
        result = find_readme_content(tmp_path)
        assert result is not None
        assert "Src Readme" in result

    @staticmethod
    def test_no_readme(tmp_path):
        result = find_readme_content(tmp_path)
        assert result is None

    @staticmethod
    def test_readme_case_insensitive(tmp_path):
        readme = tmp_path / "readme.md"
        readme.write_text("# lowercase readme", encoding="utf-8")
        result = find_readme_content(tmp_path)
        assert result is not None


class TestParseMcpServerDir:
    @staticmethod
    def test_full_parse(tmp_path):
        server_dir = tmp_path / "my-server"
        server_dir.mkdir()

        rpm_yaml = server_dir / "mcp-rpm.yaml"
        rpm_yaml.write_text("name: My Display Name\ndescription: Test description\n", encoding="utf-8")

        config_json = server_dir / "mcp_config.json"
        config = {
            "mcpServers": {
                "my-server": {
                    "command": "python",
                    "args": ["server.py"],
                }
            }
        }
        config_json.write_text(json.dumps(config), encoding="utf-8")

        readme = server_dir / "README.md"
        readme.write_text("# My Server", encoding="utf-8")

        result = parse_mcp_server_dir(server_dir)
        assert result is not None
        assert result["name"] == "my-server"
        assert result["display_name"] == "My Display Name"
        assert result["description"] == "Test description"
        assert result["local_server_config"] is not None
        assert result["remote_server_config"] is None
        assert result["readme_md"] is not None

    @staticmethod
    def test_minimal_parse(tmp_path):
        server_dir = tmp_path / "minimal-server"
        server_dir.mkdir()

        result = parse_mcp_server_dir(server_dir)
        assert result is not None
        assert result["name"] == "minimal-server"
        assert result["display_name"] == "minimal-server"
        assert result["description"] == ""
        assert result["local_server_config"] is None
        assert result["remote_server_config"] is None
        assert result["readme_md"] is None

    @staticmethod
    def test_config_from_other_json(tmp_path):
        server_dir = tmp_path / "json-server"
        server_dir.mkdir()

        other_json = server_dir / "config.json"
        config = {
            "mcpServers": {
                "json-server": {
                    "url": "http://example.com",
                }
            }
        }
        other_json.write_text(json.dumps(config), encoding="utf-8")

        result = parse_mcp_server_dir(server_dir)
        assert result is not None
        assert result["remote_server_config"] is not None
        assert result["local_server_config"] is None

    @staticmethod
    def test_config_from_readme_json(tmp_path):
        server_dir = tmp_path / "readme-server"
        server_dir.mkdir()

        readme = server_dir / "README.md"
        readme.write_text(
            '# My Server\n\n```json\n{"mcpServers": {"readme-server": {"command": "node", "args": ["index.js"]}}}\n```\n',
            encoding="utf-8",
        )

        result = parse_mcp_server_dir(server_dir)
        assert result is not None
        assert result["local_server_config"] is not None
```

**步骤 2：运行测试确认失败**

运行：`python -m pytest tests/test_mcp_parser.py -v`
预期：失败（模块未找到）

**步骤 3：实现 mcp_parser.py**

创建 `app/utils/mcp_parser.py`，实现以下函数：
- `parse_mcp_rpm_yaml(yaml_path) -> dict | None` — 解析 name + description
- `parse_mcp_config_json(json_path, server_name) -> dict | None` — 解析配置并校正 key
- `find_readme_content(server_dir) -> str | None` — 先外层目录再 src 目录查找 README
- `parse_mcp_server_dir(server_dir) -> dict` — 编排单个 MCP Server 目录的所有解析逻辑
- `_find_mcp_config(server_dir) -> dict | None` — 搜索 mcp_config.json（外层 → 内层）
- `_find_config_in_other_json(server_dir) -> dict | None` — 在其他 json 文件中搜索 mcpServers
- `_find_config_in_readme(server_dir) -> dict | None` — 在 README 中搜索 mcpServers 的 json 块

配置解析核心逻辑：
1. 搜索 mcp_config.json（外层目录优先，然后内层目录）
2. 未找到 → 搜索其他 .json 文件中含 "mcpServers" 的
3. 未找到 → 搜索 README.md/readme.md/README_EN.md 中含 mcpServers 的 json 块
4. 对所有 mcpServers 的 key：校正为 server_name，按 command（local）和 url（remote）分类

**步骤 4：运行测试确认通过**

运行：`python -m pytest tests/test_mcp_parser.py -v`
预期：通过

**步骤 5：提交**

```bash
git add app/utils/mcp_parser.py tests/test_mcp_parser.py
git commit -m "feat(mcp-parser): add MCP Server config parsing utility"
```

---

### 任务 3：添加 MCP Server 导入数据模型

**文件：**
- 修改：`app/schemas/import_.py`

**步骤 1：在 import_.py 中添加 MCP Server 导入相关 schema**

在已有 schema 之后添加：

```python
class MCPServerPreviewRequest(BaseModel):
    repo_url: str = Field(..., alias="repoUrl")
    branch: str = "main"
    root_dir: str = Field(..., alias="rootDir")

    model_config = ConfigDict(populate_by_name=True)


class MCPServerPreviewItem(BaseModel):
    name: str
    display_name: str | None = Field(default=None, alias="displayName")
    description: str = ""
    config_type: str = Field(default="none", alias="configType")  # local/remote/both/none
    source_url: str = Field(..., alias="sourceUrl")
    relative_path: str = ""

    model_config = ConfigDict(populate_by_name=True)


class MCPServerPreviewResponse(BaseModel):
    mcp_servers: list[MCPServerPreviewItem] = Field(default_factory=list, alias="mcpServers")
    conflicts: list[str] = []
    parse_errors: list[ParseError] = Field(default_factory=list, alias="parseErrors")
    repo_info: RepoInfo = Field(..., alias="repoInfo")

    model_config = ConfigDict(populate_by_name=True)


class MCPServerImportRequest(BaseModel):
    repo_url: str = Field(..., alias="repoUrl")
    branch: str = "main"
    root_dir: str = Field(..., alias="rootDir")
    mcp_servers: list[str] = Field(default_factory=list, alias="mcpServers")
    category: str = "其他"
    team: str = "未知团队"

    model_config = ConfigDict(populate_by_name=True)
```

**步骤 2：提交**

```bash
git add app/schemas/import_.py
git commit -m "feat(schemas): add MCP Server import preview and confirm schemas"
```

---

### 任务 4：实现 MCP Server 导入服务

**文件：**
- 修改：`app/services/import_service.py`
- 测试：`tests/test_mcp_import.py`

**步骤 1：编写 MCP Server 导入的失败测试**

创建 `tests/test_mcp_import.py`：

```python
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.import_ import MCPServerPreviewResponse
from app.services.import_service import preview_mcp_servers, import_mcp_servers


class TestPreviewMCPServers:
    @staticmethod
    @pytest.mark.asyncio
    async def test_preview_with_mcp_servers(tmp_path):
        servers_dir = tmp_path / "servers"
        server_a = servers_dir / "server-a"
        server_a.mkdir(parents=True)

        rpm_yaml = server_a / "mcp-rpm.yaml"
        rpm_yaml.write_text("name: Server A\ndescription: A test server\n", encoding="utf-8")

        config_json = server_a / "mcp_config.json"
        config = {"mcpServers": {"server-a": {"command": "python", "args": ["a.py"]}}}
        config_json.write_text(json.dumps(config), encoding="utf-8")

        with patch("app.services.import_service._clone_repo", return_value=tmp_path):
            with patch("app.services.import_service.parse_repo_url") as mock_parse:
                from app.utils.platform import RepoInfo
                mock_parse.return_value = RepoInfo(platform="gitcode", owner="test", repo="mcp-servers")
                with patch("app.services.import_service.build_clone_url", return_value="https://gitcode.com/test/mcp-servers.git"):
                    with patch("app.services.import_service.build_source_url", return_value="https://gitcode.com/test/mcp-servers/blob/main/servers/server-a"):
                        result = await preview_mcp_servers(
                            "https://gitcode.com/test/mcp-servers", "main", "servers"
                        )
                        assert isinstance(result, MCPServerPreviewResponse)
                        assert len(result.mcp_servers) >= 1

    @staticmethod
    @pytest.mark.asyncio
    async def test_preview_empty_root_dir(tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch("app.services.import_service._clone_repo", return_value=tmp_path):
            with patch("app.services.import_service.parse_repo_url") as mock_parse:
                from app.utils.platform import RepoInfo
                mock_parse.return_value = RepoInfo(platform="gitcode", owner="test", repo="mcp-servers")
                with patch("app.services.import_service.build_clone_url", return_value="https://gitcode.com/test/mcp-servers.git"):
                    result = await preview_mcp_servers(
                        "https://gitcode.com/test/mcp-servers", "main", "empty"
                    )
                    assert len(result.mcp_servers) == 0


class TestImportMCPServers:
    @staticmethod
    @pytest.mark.asyncio
    async def test_import_selected_servers(tmp_path):
        servers_dir = tmp_path / "servers"
        server_a = servers_dir / "server-a"
        server_a.mkdir(parents=True)

        rpm_yaml = server_a / "mcp-rpm.yaml"
        rpm_yaml.write_text("name: Server A\ndescription: A test server\n", encoding="utf-8")

        config_json = server_a / "mcp_config.json"
        config = {"mcpServers": {"server-a": {"command": "python", "args": ["a.py"]}}}
        config_json.write_text(json.dumps(config), encoding="utf-8")

        mock_repo = AsyncMock()
        mock_repo.get_by_name = AsyncMock(return_value=None)

        with patch("app.services.import_service._clone_repo", return_value=tmp_path):
            with patch("app.services.import_service.parse_repo_url") as mock_parse:
                from app.utils.platform import RepoInfo
                mock_parse.return_value = RepoInfo(platform="gitcode", owner="test", repo="mcp-servers")
                with patch("app.services.import_service.build_clone_url", return_value="https://gitcode.com/test/mcp-servers.git"):
                    with patch("app.services.import_service.build_source_url", return_value="https://gitcode.com/test/mcp-servers/blob/main/servers/server-a"):
                        result = await import_mcp_servers(
                            "https://gitcode.com/test/mcp-servers", "main", "servers",
                            ["server-a"], "开发效率", "测试团队", mock_repo
                        )
                        assert "server-a" in result.imported
```

**步骤 2：运行测试确认失败**

运行：`python -m pytest tests/test_mcp_import.py -v`
预期：失败（函数未找到）

**步骤 3：在 import_service.py 中实现 preview_mcp_servers 和 import_mcp_servers**

在 `app/services/import_service.py` 中添加：

- `preview_mcp_servers(repo_url, branch, root_dir)` — 克隆仓库，扫描根目录子目录，用 mcp_parser 解析每个目录，返回预览结果
- `import_mcp_servers(repo_url, branch, root_dir, mcp_server_names, category, team, mcp_repo)` — 预览后对选中的服务器执行新增或更新

关键实现细节：
- 使用已有的 `_clone_repo` 克隆仓库
- 列出 root_dir 路径下的所有子目录
- 对每个子目录调用 mcp_parser 的 `parse_mcp_server_dir`
- 使用 `build_source_url` 构建指向目录的 source_url
- 判断 `config_type`："local" / "remote" / "both" / "none"
- 导入时：对每个选中的服务器调用 `mcp_repo.create_server` 或 `mcp_repo.update_server`

**步骤 4：运行测试确认通过**

运行：`python -m pytest tests/test_mcp_import.py -v`
预期：通过

**步骤 5：提交**

```bash
git add app/services/import_service.py tests/test_mcp_import.py
git commit -m "feat(import): add MCP Server preview and import service"
```

---

### 任务 5：添加 MCP Server 导入 API 端点

**文件：**
- 新建：`app/routers/mcp_import.py`
- 修改：`app/main.py`（注册新路由）

**步骤 1：新建 mcp_import.py，参照 import_.py 的 Skill 导入模式**

创建 `app/routers/mcp_import.py`，路由前缀 `/api/admin/import-mcp-servers`，与 Skill 导入的 `import_.py`（前缀 `/api/admin/import-skills`）对称：

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories.mcp_server_repo import MCPServerRepository
from app.schemas.import_ import (
    MCPServerPreviewRequest,
    MCPServerPreviewResponse,
    MCPServerImportRequest,
    ImportResponse,
)
from app.services.import_service import preview_mcp_servers, import_mcp_servers

router = APIRouter(prefix="/api/admin/import-mcp-servers", tags=["mcp-import"])


def _get_mcp_repo(session: AsyncSession = Depends(get_session)) -> MCPServerRepository:
    return MCPServerRepository(session)


@router.post("/preview", response_model=MCPServerPreviewResponse)
async def preview_import_mcp_servers(
    body: MCPServerPreviewRequest,
    repo: MCPServerRepository = Depends(_get_mcp_repo),
):
    try:
        result = await preview_mcp_servers(body.repo_url, body.branch, body.root_dir)

        existing_names = set()
        for server in result.mcp_servers:
            existing = await repo.get_by_name(server.name)
            if existing:
                existing_names.add(server.name)

        result.conflicts = list(existing_names)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {e}") from e


@router.post("", response_model=ImportResponse)
async def confirm_import_mcp_servers(
    body: MCPServerImportRequest,
    repo: MCPServerRepository = Depends(_get_mcp_repo),
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await import_mcp_servers(
            body.repo_url, body.branch, body.root_dir,
            body.mcp_servers, body.category, body.team, repo
        )
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {e}") from e
```

**步骤 2：在 main.py 中注册新路由**

在 `app/main.py` 的路由注册部分添加：

```python
from app.routers.mcp_import import router as mcp_import_router
app.include_router(mcp_import_router)
```

**步骤 3：运行现有测试确认无回归**

运行：`python -m pytest tests/ -v`
预期：全部通过

**步骤 4：提交**

```bash
git add app/routers/mcp_import.py app/main.py
git commit -m "feat(mcp-import): add MCP Server import preview and confirm endpoints"
```

---

### 任务 6：实现 MCP Server 同步服务

**文件：**
- 修改：`app/services/sync_service.py`
- 测试：`tests/test_mcp_sync_service.py`

**步骤 1：编写 MCPServerSyncService 的失败测试**

创建 `tests/test_mcp_sync_service.py`：

```python
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.mcp_server import MCPServer
from app.models.sync import SyncLock, SyncTask
from app.services.email_service import EmailService
from app.services.sync_service import MCPServerSyncService
from app.utils.remote_fetcher import RemoteFetcher


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_fetcher():
    return AsyncMock(spec=RemoteFetcher)


@pytest.fixture
def mock_email():
    return AsyncMock(spec=EmailService)


@pytest.fixture
def mock_mcp_repo():
    repo = AsyncMock()
    repo.list_servers = AsyncMock(return_value={"data": [], "total": 0})
    repo.update_server = AsyncMock()
    return repo


@pytest.fixture
def mcp_sync_service(mock_session, mock_fetcher, mock_email, mock_mcp_repo):
    return MCPServerSyncService(
        session=mock_session,
        remote_fetcher=mock_fetcher,
        email_service=mock_email,
        mcp_server_repo=mock_mcp_repo,
        lock_timeout_hours=2,
    )


class TestMCPServerAcquireSyncLock:
    @staticmethod
    @pytest.mark.asyncio
    async def test_acquire_lock_success(mcp_sync_service, mock_session):
        task = await mcp_sync_service.acquire_sync_lock("test-instance")
        assert task is not None
        assert task.task_type == "mcp_server_sync"
        assert task.status == "running"


class TestMCPServerSyncAll:
    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_all_lock_busy(mcp_sync_service, mock_session):
        from sqlalchemy.exc import IntegrityError

        call_count = 0

        async def mock_commit():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise IntegrityError("", "", "")

        mock_session.commit = mock_commit
        recent_lock = SyncLock(
            lock_name="mcp_server_sync",
            locked_date=datetime.now(UTC).strftime("%Y-%m-%d"),
            locked_by="other-instance",
            locked_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = recent_lock
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await mcp_sync_service.sync_all()
        assert result["status"] == "skipped"
        assert result["reason"] == "lock_busy"

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_all_empty(mock_session, mock_fetcher, mock_email, mock_mcp_repo):
        lock_row = SyncLock(
            lock_name="mcp_server_sync",
            locked_date=datetime.now(UTC).strftime("%Y-%m-%d"),
            locked_by="test-instance",
            locked_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = lock_row
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_mcp_repo.list_servers = AsyncMock(return_value={"data": [], "total": 0})
        mock_email.send_sync_report = AsyncMock(return_value=True)

        svc = MCPServerSyncService(
            session=mock_session,
            remote_fetcher=mock_fetcher,
            email_service=mock_email,
            mcp_server_repo=mock_mcp_repo,
            lock_timeout_hours=2,
        )
        result = await svc.sync_all()
        assert result["stats"]["total"] == 0


class TestMCPServerSyncServer:
    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_server_no_source_url(mcp_sync_service):
        server = MagicMock(spec=MCPServer)
        server.name = "test"
        server.source_url = None
        result = await mcp_sync_service.sync_server(server, Path("/tmp/fake"))
        assert result["status"] == "skipped"

    @staticmethod
    @pytest.mark.asyncio
    async def test_sync_server_updated(mcp_sync_service, mock_mcp_repo, tmp_path):
        server_dir = tmp_path / "test-server"
        server_dir.mkdir()

        rpm_yaml = server_dir / "mcp-rpm.yaml"
        rpm_yaml.write_text("name: Updated Name\ndescription: Updated desc\n", encoding="utf-8")

        config_json = server_dir / "mcp_config.json"
        config = {"mcpServers": {"test-server": {"command": "python", "args": ["new.py"]}}}
        config_json.write_text(json.dumps(config), encoding="utf-8")

        server = MagicMock(spec=MCPServer)
        server.name = "test-server"
        server.source_url = "https://gitcode.com/test/mcp-servers/tree/main/servers/test-server"
        server.display_name = "Old Name"
        server.description = "Old desc"
        server.local_server_config = "{}"
        server.remote_server_config = None
        server.readme_md = None

        result = await mcp_sync_service.sync_server(server, tmp_path)
        assert result["status"] == "updated"
```

**步骤 2：运行测试确认失败**

运行：`python -m pytest tests/test_mcp_sync_service.py -v`
预期：失败（类未找到）

**步骤 3：在 sync_service.py 中实现 MCPServerSyncService**

在 `app/services/sync_service.py` 中添加 `MCPServerSyncService` 类：

- 使用锁名 `mcp_server_sync`（与 skill_sync 独立）
- `sync_all()`：获取锁 → 获取所有 MCP Server → 按仓库分组 → 克隆每个仓库 → 同步每个服务器 → 释放锁 → 发送邮件
- `sync_server(server, repo_path)`：从克隆的仓库中解析服务器目录，与数据库值比较，有变化则更新
- `sync_mcp_server(server, repo_path)`：用 mcp_parser 重新解析，比较字段，有变化则调用 mcp_repo.update_server

关键实现细节：
- 解析 source_url 提取 (platform, owner, repo, branch, dir_path)
- 按 (platform, owner, repo, branch) 分组
- 每组：克隆仓库一次，遍历该仓库下的所有服务器
- 对每个服务器：在克隆的仓库中找到其目录，调用 parse_mcp_server_dir，与当前数据库值比较
- 更新字段：display_name、description、local_server_config、remote_server_config、readme_md

**步骤 4：运行测试确认通过**

运行：`python -m pytest tests/test_mcp_sync_service.py -v`
预期：通过

**步骤 5：提交**

```bash
git add app/services/sync_service.py tests/test_mcp_sync_service.py
git commit -m "feat(sync): add MCPServerSyncService with independent lock and cron"
```

---

### 任务 7：添加 MCP Server 同步邮件报告

**文件：**
- 修改：`app/services/email_service.py`

**步骤 1：添加 build_mcp_sync_report 函数**

添加 `build_mcp_sync_report(result_summary: dict) -> str`，遵循与 `build_sync_report` 相同的 HTML 模板模式，但标题为"MCP Server 同步报告"。

**步骤 2：在 EmailService 中添加 send_mcp_sync_report 方法**

```python
async def send_mcp_sync_report(self, result_summary: dict[str, Any]) -> bool:
    # 与 send_sync_report 相同模式，但使用 MCP Server 主题
```

**步骤 3：提交**

```bash
git add app/services/email_service.py
git commit -m "feat(email): add MCP Server sync report email template"
```

---

### 任务 8：添加 MCP Server 同步 cron 配置

**文件：**
- 修改：`app/config.py`

**步骤 1：添加 MCP Server 同步 cron 设置**

在 Settings 类中添加：

```python
mcp_sync_cron_hour: int = 18
mcp_sync_cron_minute: int = 0
mcp_sync_lock_timeout_hours: int = 2
```

同时在 `__init__` 中添加 Apollo 配置加载。

**步骤 2：提交**

```bash
git add app/config.py
git commit -m "feat(config): add MCP Server sync cron settings"
```

---

### 任务 9：在 main.py 中注册 MCP Server 同步调度器

**文件：**
- 修改：`app/main.py`

**步骤 1：在 APScheduler 中添加 MCP Server 同步任务**

在 `lifespan()` 中，在已有的 skill_sync 任务之后添加：

```python
from app.services.sync_service import MCPServerSyncService

async def _run_mcp_sync() -> None:
    async with async_session_factory() as session:
        fetcher = RemoteFetcher(...)
        email_svc = EmailService(...)
        mcp_repo = MCPServerRepository(session)
        sync_svc = MCPServerSyncService(
            session=session,
            remote_fetcher=fetcher,
            email_service=email_svc,
            mcp_server_repo=mcp_repo,
            lock_timeout_hours=settings.mcp_sync_lock_timeout_hours,
        )
        result = await sync_svc.sync_all()
        logger.info("MCP Server scheduled sync completed: %s", result)

scheduler.add_job(
    _run_mcp_sync,
    CronTrigger(hour=settings.mcp_sync_cron_hour, minute=settings.mcp_sync_cron_minute),
    id="mcp_server_sync",
    replace_existing=True,
)
```

**步骤 2：运行全部测试确认无回归**

运行：`python -m pytest tests/ -v`
预期：全部通过

**步骤 3：提交**

```bash
git add app/main.py
git commit -m "feat(scheduler): register MCP Server sync cron job"
```

---

### 任务 10：添加 MCP Server 目录的 source_url 解析工具

**文件：**
- 修改：`app/utils/platform.py`

**步骤 1：添加 parse_mcp_source_url 函数**

MCP Server 的 source_url 指向目录（tree URL），而非文件（blob URL）。添加：

```python
def parse_mcp_source_url(source_url: str) -> dict | None:
    """解析指向目录的 MCP Server source URL。
    例如 https://gitcode.com/openeuler/mcp-servers/tree/master/servers/lto_dump_mcp
    """
    github_pattern = r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)"
    gitcode_pattern = r"https?://(?:www\.)?gitcode\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)"

    match = re.match(github_pattern, source_url)
    if match:
        return {"platform": "github", "owner": match.group(1), "repo": match.group(2), "branch": match.group(3), "dir_path": match.group(4)}

    match = re.match(gitcode_pattern, source_url)
    if match:
        return {"platform": "gitcode", "owner": match.group(1), "repo": match.group(2), "branch": match.group(3), "dir_path": match.group(4)}

    return None
```

**步骤 2：添加 parse_mcp_source_url 的测试**

添加到已有测试文件或创建内联测试。

**步骤 3：提交**

```bash
git add app/utils/platform.py
git commit -m "feat(platform): add parse_mcp_source_url for directory URLs"
```

---

### 任务 11：最终集成测试与清理

**文件：**
- 测试：`tests/test_mcp_import.py`、`tests/test_mcp_sync_service.py`

**步骤 1：运行完整测试套件**

运行：`python -m pytest tests/ -v`
预期：全部通过

**步骤 2：运行 ruff 代码检查**

运行：`ruff check app/ tests/`
预期：无错误

**步骤 3：修复所有代码检查问题**

**步骤 4：如有需要则最终提交**

```bash
git add -A
git commit -m "chore: fix lint issues and finalize MCP Server import/sync"
```
