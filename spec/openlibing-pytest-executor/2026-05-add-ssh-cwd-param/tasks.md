# Tasks: Add `cwd` Parameter to SSH Command Execution

## Implementation Tasks

### Task 1: Update `ssh_cmd()` method signature
**File**: `pytest_testkit/lib/base/ssh.py`

- [x] Add `cwd=None` parameter to `ssh_cmd()` method (line 121)
- [x] Pass `cwd` parameter to `_direct_exec_cmd()` call
- [x] Pass `cwd` parameter to `_jump_exec_command()` call

---

### Task 2: Update `_direct_exec_cmd()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [x] Add `cwd=None` parameter to method signature (line 284)
- [x] Add command transformation logic before `bash -l -c` wrapping:
  ```python
  if cwd:
      cmd = f"cd {shlex.quote(cwd)} && {cmd}"
  ```

---

### Task 3: Update `_jump_exec_command()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [x] Add `cwd=None` parameter to method signature (line 95)
- [x] Add command transformation logic before `bash -l -c` wrapping:
  ```python
  if cwd:
      cmd = f"cd {shlex.quote(cwd)} && {cmd}"
  ```

---

### Task 4: Update `ssh_cmd_interactive()` method signature
**File**: `pytest_testkit/lib/base/ssh.py`

- [x] Add `cwd=None` parameter to `ssh_cmd_interactive()` method (line 131)
- [x] Pass `cwd` parameter to `_direct_exec_cmd_interactive()` call
- [x] Pass `cwd` parameter to `_jump_exec_cmd_interactive()` call

---

### Task 5: Update `_direct_exec_cmd_interactive()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [x] Add `cwd=None` parameter to method signature (line 151)
- [x] Modify `channel.send()` to include `cd` prefix when `cwd` is set:
  ```python
  if cwd:
      self.channel.send(f"cd {shlex.quote(cwd)} && {cmd}\n")
  else:
      self.channel.send(cmd + '\n')
  ```

---

### Task 6: Update `_jump_exec_cmd_interactive()` method
**File**: `pytest_testkit/lib/base/ssh.py`

- [x] Add `cwd=None` parameter to method signature (line 196)
- [x] Modify `target_channel.send()` to include `cd` prefix when `cwd` is set:
  ```python
  if cwd:
      self.target_channel.send(f"cd {shlex.quote(cwd)} && {cmd}\n")
  else:
      self.target_channel.send(cmd + '\n')
  ```

---

### Task 7: Update `Device.sendcmd()` method
**File**: `pytest_testkit/lib/common/environment/device.py`

- [x] Add `cwd=None` parameter to `sendcmd()` method (line 220)
- [x] Update docstring to document the new parameter
- [x] Pass `cwd` parameter to `ssh_cmd()` call

---

### Task 8: Update `Device.sendcmd_interactive()` method
**File**: `pytest_testkit/lib/common/environment/device.py`

- [x] Add `cwd=None` parameter to `sendcmd_interactive()` method (line 252)
- [x] Update docstring to document the new parameter
- [x] Pass `cwd` parameter to `ssh_cmd_interactive()` call

---

## Verification Checklist

After completing all tasks:

- [ ] Run linting: `ruff check pytest_testkit/`
- [ ] Run type checking (if configured)
- [ ] Verify backward compatibility: existing calls without `cwd` should work unchanged
- [ ] Test with paths containing spaces and special characters