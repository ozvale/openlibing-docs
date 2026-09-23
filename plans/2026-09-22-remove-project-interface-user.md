# Remove Project Interface User Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task.

**Goal:** Permanently remove the obsolete project interface-user field from the
Argus database and all backend and frontend contracts.

**Architecture:** A timestamped Flyway migration removes the PostgreSQL column
and index. The DDD domain, persistence, trigger, and React layers then remove
the corresponding properties so no runtime API can expose or modify the field.

**Tech Stack:** Java 21, Spring Boot, MyBatis-Plus, Flyway, PostgreSQL, React
19, TypeScript, React Router, Node test runner.

---

### Task 1: Establish the backend removal contract

**Files:**

- Create: `openlibing-vulnerability-hunting/argus-app/src/test/java/com/argus/project/ProjectInterfaceUserRemovalContractTest.java`

**Step 1: Write the failing test**

Use reflection to assert that `ProjProjectEntity` (domain), the infrastructure
project PO, `ProjectRequest`, and `ProjectVO` do not declare `interfaceUserId`;
also assert `ProjectVO` does not declare `interfaceUserName`.

**Step 2: Run it to verify it fails**

Run:

```powershell
mvn test -pl argus-app -Dtest=ProjectInterfaceUserRemovalContractTest
```

Expected: a clear assertion failure for an existing interface-user field.

### Task 2: Remove backend model and API references

**Files:**

- Modify: `openlibing-vulnerability-hunting/argus-domain/src/main/java/com/argus/project/model/entity/ProjProjectEntity.java`
- Modify: `openlibing-vulnerability-hunting/argus-domain/src/main/java/com/argus/project/model/dto/ProjectRequest.java`
- Modify: `openlibing-vulnerability-hunting/argus-domain/src/main/java/com/argus/project/service/ProjectService.java`
- Modify: `openlibing-vulnerability-hunting/argus-infrastructure/src/main/java/com/argus/project/persistence/entity/ProjProjectEntity.java`
- Modify: `openlibing-vulnerability-hunting/argus-trigger/src/main/java/com/argus/project/trigger/dto/ProjectVO.java`
- Modify: `openlibing-vulnerability-hunting/argus-trigger/src/main/java/com/argus/project/trigger/http/ProjectController.java`
- Modify: `openlibing-vulnerability-hunting/argus-trigger/src/main/java/com/argus/project/trigger/http/ProjectScopeController.java`

**Step 1: Implement the smallest removal**

Delete the fields and their comments. Delete the conditional assignment from
`ProjectService.updateProject`. Delete interface-user name enrichment and update
the affected Javadocs without changing domain/component/group behavior.

**Step 2: Run the backend contract test**

Run the Task 1 command. Expected: pass.

### Task 3: Remove the database column

**Files:**

- Create: `openlibing-vulnerability-hunting/argus-app/src/main/resources/db/migration/V20260922.HHmm__drop_project_interface_user.sql`

**Step 1: Create the migration with the actual creation minute**

```sql
DROP INDEX IF EXISTS idx_proj_project_interface_user;
ALTER TABLE t_proj_project DROP COLUMN IF EXISTS interface_user_id;
```

Do not edit checksum-locked historical migrations.

**Step 2: Compile and validate migrations**

Run:

```powershell
mvn compile -pl argus-infrastructure,argus-trigger,argus-app -am -DskipTests
mvn flyway:validate
```

Expected: compile succeeds; record any environment-related Flyway limitation
without altering unrelated configuration.

### Task 4: Establish the frontend removal contract

**Files:**

- Create: `openlibing-vulnerability-hunting-web/tests/project-interface-user-removal.test.mjs`

**Step 1: Write the failing test**

Read the project API, dialog, table, and page source files and assert they do
not contain `interfaceUserId`, `interfaceUserName`, `代码仓接口人`, or the
interface-user table header.

**Step 2: Run it to verify it fails**

Run:

```powershell
npm test -- project-interface-user-removal.test.mjs
```

Expected: a source-contract assertion fails before implementation.

### Task 5: Remove frontend fields and UI

**Files:**

- Modify: `openlibing-vulnerability-hunting-web/app/lib/api/project.ts`
- Modify: `openlibing-vulnerability-hunting-web/app/components/project/project-dialog.tsx`
- Modify: `openlibing-vulnerability-hunting-web/app/components/project/project-table.tsx`
- Modify: `openlibing-vulnerability-hunting-web/app/pages/projects.tsx`

**Step 1: Implement the smallest removal**

Delete field declarations, initial form state, update payload mapping, dialog
section, table header/cell/skeleton, and page-description wording. Preserve the
project edit menu and all other project fields.

**Step 2: Run the frontend contract test**

Run the Task 4 command. Expected: pass.

### Task 6: Verify and commit

**Files:**

- Verify only the files listed above plus the two focused tests and one migration.

**Step 1: Run validation**

```powershell
npm test
npm run typecheck
npm run build
```

Run the focused backend test and relevant Maven compile/validation commands.

**Step 2: Review and commit**

Use `git diff --check` and inspect staged paths. Commit backend, frontend, and
documentation separately. Do not stage the existing local rate-limit edits,
untracked files, or user-owned dependency directories.
