# Tasks: Add `ignore_err` Parameter and Dict Return Type to SSH Command Execution

## Implementation Tasks

### Task 1: Update `_direct_exec_cmd()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [ ] Add `ignore_err=False` parameter to method signature
- [ ] Unify error handling logic:
  - Read stdout first, then stderr
  - Get exit_code via `stdout.channel.recv_exit_status()`
  - Use `exit_code != 0` as error condition
- [ ] Add success calculation:
  ```python
  if exit_code == 0:
      success = True
  elif ignore_err:
      success = True
  else:
      success = False
  ```
- [ ] Add logging: info for execution, warning when exit_code != 0
- [ ] Remove `self.client.close()` on error
- [ ] **Remove RuntimeError raise** - never throw exception
- [ ] Apply `.strip()` to both stdout and stderr content
- [ ] Change return type to dictionary:
  ```python
  return {
      'success': success,
      'stdout': stdout_content,
      'stderr': stderr_content
  }
  ```

---

### Task 2: Update `_jump_exec_command()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [ ] Add `ignore_err=False` parameter to method signature
- [ ] Unify error handling logic (same as Task 1):
  - Read stdout first, then stderr
  - Apply `.strip()` to both stdout and stderr content
- [ ] Add success calculation (same as Task 1)
- [ ] Add warning log when `exit_code != 0`
- [ ] Update logging format to match `_direct_exec_cmd()`
- [ ] **Remove RuntimeError raise** - never throw exception
- [ ] Change return type to dictionary

---

### Task 3: Update `ssh_cmd()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [ ] Add `ignore_err=False` parameter to method signature
- [ ] Pass `ignore_err` to `_direct_exec_cmd()` call
- [ ] Pass `ignore_err` to `_jump_exec_command()` call
- [ ] Return the dictionary directly (no additional processing needed)
- [ ] Update docstring to document new parameter and return type

---

### Task 4: Update `_direct_exec_cmd_interactive()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [ ] Add `ignore_err=False` parameter to method signature
- [ ] Add `matched_prompt = False` initialization at start
- [ ] Update prompt matching logic:
  ```python
  matched_prompt = False
  ...
  if prompt_regex.search(output):
      matched_prompt = True
      break
  ```
- [ ] Add success calculation:
  ```python
  if matched_prompt:
      success = True
  elif ignore_err:
      success = True
  else:
      success = False
  ```
- [ ] Add warning log when prompt not matched
- [ ] Add info logging for match status
- [ ] **Remove RuntimeError raise** - never throw exception
- [ ] Change return type to dictionary:
  ```python
  return {
      'success': success,
      'stdout': output,
      'stderr': ""
  }
  ```

---

### Task 5: Update `_jump_exec_cmd_interactive()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [ ] Add `ignore_err=False` parameter to method signature
- [ ] Add `matched_prompt = False` initialization at start
- [ ] Update prompt matching logic (same as Task 4)
- [ ] Add success calculation (same as Task 4)
- [ ] Add warning log when prompt not matched
- [ ] **Remove RuntimeError raise** - never throw exception
- [ ] Change return type to dictionary

---

### Task 6: Update `ssh_cmd_interactive()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [ ] Add `ignore_err=False` parameter to method signature
- [ ] Pass `ignore_err` to `_direct_exec_cmd_interactive()` call
- [ ] Pass `ignore_err` to `_jump_exec_cmd_interactive()` call
- [ ] Return the dictionary directly
- [ ] Update docstring to document the new parameter and return type

---

### Task 7: Update `Device.sendcmd()` method
**File**: `pytest_testkit/lib/common/environment/device.py`

- [ ] Add `ignore_err=False` parameter to method signature
- [ ] Update docstring to document the new parameter and return type
- [ ] Pass `ignore_err` to `ssh_cmd()` call
- [ ] Return the dictionary directly from `ssh_cmd()`

---

### Task 8: Update `Device.sendcmd_interactive()` method
**File**: `pytest_testkit/lib/common/environment/device.py`

- [ ] Add `ignore_err=False` parameter to method signature
- [ ] Update docstring to document the new parameter and return type
- [ ] Pass `ignore_err` to `ssh_cmd_interactive()` call
- [ ] Return the dictionary directly from `ssh_cmd_interactive()`

---

## Verification Checklist

After completing all tasks:

- [ ] Run linting: `ruff check pytest_testkit/`
- [ ] Verify **no exceptions are thrown** when command fails
- [ ] Verify non-interactive commands return dictionary:
  - `success=True` when `exit_code == 0`
  - `success=True` when `exit_code != 0` AND `ignore_err=True`
  - `success=False` when `exit_code != 0` AND `ignore_err=False`
  - `stdout`: stdout content (stripped)
  - `stderr`: stderr content (stripped)
- [ ] Verify interactive commands return dictionary:
  - `success=True` when `matched_prompt == True`
  - `success=True` when `matched_prompt == False` AND `ignore_err=True`
  - `success=False` when `matched_prompt == False` AND `ignore_err=False`
  - `stdout`: collected output
  - `stderr`: `""` (empty string)
- [ ] Verify `matched_prompt` tracking:
  - Starts as `False`
  - Set to `True` when `prompt_regex.search(output)` succeeds
- [ ] Verify warning log is output when command fails
- [ ] Verify callers can check `result['success']` instead of catching exceptions