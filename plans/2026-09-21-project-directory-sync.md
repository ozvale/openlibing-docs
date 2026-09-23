# Project Directory Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the ambiguous, multi-source project pull operation with an OpenLibing-only project-directory synchronization flow and consistent synchronization terminology.

**Architecture:** The management controller exposes a no-selector directory-sync route that invokes the existing complete OpenLibing source snapshot flow. The service no longer builds a provider map or accepts manual project selections; it uses the OpenLibing provider directly, preserving batch records and the existing raw-snapshot archive reconciliation. The React management UI invokes the renamed route and renders a compact confirmation dialog rather than source cards or a candidate picker.

**Tech Stack:** Java 21, Spring Boot, JUnit 5/Mockito, React 19, TypeScript, React Query, Vite, Node test runner.

---

### Task 1: Establish the OpenLibing-only backend contract

**Files:**

- Modify: `openlibing-vulnerability-hunting/argus-trigger/src/main/java/com/argus/project/trigger/http/ProjectController.java:291-313`
- Delete: `openlibing-vulnerability-hunting/argus-domain/src/main/java/com/argus/project/model/dto/ProjectPullRequest.java`
- Modify: `openlibing-vulnerability-hunting/argus-domain/src/main/java/com/argus/project/model/dto/ProjectPullResult.java`
- Modify: `openlibing-vulnerability-hunting/argus-domain/src/main/java/com/argus/project/service/ProjectPullService.java:41-180`
- Delete: `openlibing-vulnerability-hunting/argus-infrastructure/src/main/java/com/argus/project/pull/ManualProjectPullSourceProvider.java`
- Modify: `openlibing-vulnerability-hunting/argus-domain/src/main/java/com/argus/project/repository/IProjectPullSourceProvider.java`

**Step 1: Write the failing service test**

Create or extend `argus-domain/src/test/java/com/argus/project/service/ProjectPullServiceSummaryTest.java` to call `syncDirectory(operatorUserId)`. Assert that it creates or reuses the `SOURCE_PULL` batch and schedules the OpenLibing source key with an empty selected-project list. Assert no source key or project IDs are supplied by the caller.

**Step 2: Run the focused test to verify it fails**

Run: `mvn test -pl argus-domain -Dtest=ProjectPullServiceSummaryTest`

Expected: FAIL because `syncDirectory` does not exist.

**Step 3: Implement the minimal service change**

Replace `pullProjects(sourceKey, projectIds, operatorUserId)` with `syncDirectory(operatorUserId)`. Resolve the sole `openlibing` provider internally, retain `SOURCE_PULL` persistence and the after-commit batch runner, and change user-facing result messages from “源码同步” to “项目目录同步”. Remove manual-only validation and the provider map; inject or resolve the OpenLibing provider directly. Rename the result type only if all call sites can move together without widening the API surface.

**Step 4: Replace the controller route**

Expose `POST /projects/sync-directory` without a request DTO. Preserve rate limiting/audit logging with an API identifier and audit wording aligned to project-directory synchronization. Remove `/pull`, `ProjectPullRequest`, selected-ID validation, and the manual external-scope helper that is used only by this operation.

**Step 5: Remove the manual provider contract**

Delete `ManualProjectPullSourceProvider` and its tests. Simplify `IProjectPullSourceProvider` only if its selected-ID method has no remaining OpenLibing caller; otherwise retain the minimum interface necessary for the one provider, without a public manual branch.

**Step 6: Run focused backend tests**

Run: `mvn test -pl argus-domain -Dtest=ProjectPullServiceSummaryTest`

Expected: PASS.

### Task 2: Prove controller and lifecycle compatibility

**Files:**

- Modify: `openlibing-vulnerability-hunting/argus-app/src/test/java/com/argus/project/ProjectControllerExternalScopeTest.java`
- Modify: `openlibing-vulnerability-hunting/argus-app/src/test/java/com/argus/project/ProjectModulePhase1Test.java` if it asserts the previous route
- Modify: `openlibing-vulnerability-hunting/argus-app/src/test/java/com/argus/project/ProjectArchiveReconciliationServiceTest.java` only if the source entrypoint contract is covered there

**Step 1: Write failing controller assertions**

Assert that a management user can invoke `POST /projects/sync-directory` with no `sourceKey`, project list, or external-project scope. Assert the former manual `/projects/pull` path is no longer mapped.

**Step 2: Run the focused controller test**

Run: `mvn test -pl argus-app -Dtest=ProjectControllerExternalScopeTest,ProjectModulePhase1Test`

Expected: FAIL before route migration, then PASS after Task 1.

**Step 3: Verify archive flow stays source-complete**

Run: `mvn test -pl argus-app -Dtest=ProjectArchiveReconciliationServiceTest,ProjectPullServiceSummaryTest`

Expected: PASS; only the entrypoint changes, while complete raw OpenLibing snapshot reconciliation remains unchanged.

### Task 3: Replace the frontend API and remove manual state

**Files:**

- Modify: `openlibing-vulnerability-hunting-web/app/lib/api/project.ts`
- Modify: `openlibing-vulnerability-hunting-web/app/pages/projects.tsx:114-118,489-497`
- Modify: `openlibing-vulnerability-hunting-web/app/components/project/project-pull-dialog.tsx`

**Step 1: Write a failing frontend contract test**

Create `openlibing-vulnerability-hunting-web/tests/project-directory-sync.test.mjs`. Assert the API client targets `/projects/sync-directory`, does not declare `manual`, `sourceKey`, `projectIds`, or `pullCandidates`, and the dialog contains no source-option array or multi-select control.

**Step 2: Run the test to verify it fails**

Run: `npm test -- project-directory-sync.test.mjs`

Expected: FAIL because the pull API and manual UI are still present.

**Step 3: Implement the smallest frontend contract change**

Replace `ProjectPullRequest` and `pullProjects` with a zero-argument directory-sync API function and result type. Remove candidate pagination/filtering from `projectManageApi` and the page query. Update the mutation and `ProjectPullDialog` props so submit has no payload.

**Step 4: Collapse the dialog**

Render only the confirmed-copy header, a clear OpenLibing full-synchronization explanation, an archive lifecycle notice, Cancel, and `开始同步`. Remove source cards, selection state/effects, project picker, candidate error/loading props, and all manual terminology.

**Step 5: Run the focused test**

Run: `npm test -- project-directory-sync.test.mjs`

Expected: PASS.

### Task 4: Apply the unified synchronization vocabulary

**Files:**

- Modify: `openlibing-vulnerability-hunting-web/app/components/project/project-toolbar.tsx`
- Modify: `openlibing-vulnerability-hunting-web/app/components/project/project-table.tsx`
- Modify: `openlibing-vulnerability-hunting-web/app/components/project/project-sync-records-dialog.tsx`
- Modify: `openlibing-vulnerability-hunting-web/app/pages/projects.tsx`
- Test: `openlibing-vulnerability-hunting-web/tests/project-directory-sync.test.mjs`

**Step 1: Extend the failing text assertions**

Assert the primary action says `同步项目目录`; the dialog says `同步项目目录` and `开始同步`; the table headings are `代码仓 / 编码`, `组织 / 父组件`, `最近同步`; the default state says `未同步`; and `VALIDATION_FAILED` maps to `同步校验未通过`.

**Step 2: Implement text and record-label changes**

Rename the records dialog to `项目目录同步记录` and describe directory-level batch results. Update empty-state wording and success/refresh messages. Keep historical records intact; add a pure sync-type label helper that maps the old manual source/type to `历史手工同步`, while current OpenLibing batches display `项目目录同步`.

**Step 3: Run the frontend contract test**

Run: `npm test -- project-directory-sync.test.mjs`

Expected: PASS.

### Task 5: Validate build and behavior boundaries

**Files:**

- Modify only files identified by failing tests in Tasks 1–4.

**Step 1: Run frontend verification**

Run: `npm test`

Expected: all Node tests pass.

Run: `npm run typecheck`

Expected: TypeScript completes with no errors.

Run: `npm run build`

Expected: production build completes successfully.

**Step 2: Run backend verification**

Run: `mvn test -pl argus-domain -Dtest=ProjectPullServiceSummaryTest`

Run: `mvn test -pl argus-app -Dtest=ProjectControllerExternalScopeTest,ProjectModulePhase1Test,ProjectArchiveReconciliationServiceTest`

Run: `mvn compile -pl argus-infrastructure,argus-trigger -am -DskipTests`

Expected: all targeted tests and compile pass. If the known unrelated full-suite report tests still fail, record them separately rather than attributing them to this change.

**Step 3: Inspect scope**

Run `git status --short` and `git diff --check` in each repository. Confirm only intended source/test files are staged; do not stage pre-existing untracked user files.

### Task 6: Commit and hand off

**Files:**

- Modify: `openlibing-docs/spec/openlibing-vulnerability-hunting/task_design/project-directory-sync/tasks.md`

**Step 1: Record completed task state**

Update checkboxes in the task-design document without changing the already committed design decision.

**Step 2: Commit each delivery repository**

Create one backend commit, one frontend commit, and one docs commit. Each commit must use the required conventional subject and `Co-authored-by` / `Generated-by` trailers.

**Step 3: Hand off for user self-test**

Report commit hashes, test evidence, the retained historical-manual-record behavior, and the intentional retirement of `/projects/pull`. Ask for explicit self-test confirmation before creating any PR.
