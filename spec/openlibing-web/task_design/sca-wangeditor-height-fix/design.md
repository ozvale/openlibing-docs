# Design: SCA wangEditor 编辑器高度设置修复

## 技术方案

### 根因分析

wangEditor v4（4.7.15）编辑区高度机制：

- `.w-e-text` 的 min-height 由 `editor.config.height` 在 `create()` 阶段初始化（默认 300px）
- `create()` 之后再修改 `.w-e-text-container` 容器 DOM 高度，`.w-e-text` 的 min-height 不会同步更新
- 内容超出容器可视高度时，被容器 `overflow:hidden` 静默裁切，无滚动条且无法回滚

原实现（create 后 DOM 操作）：

```js
editor.create();
// ...
let dom = document.getElementById(editor.textElemId);
if (this.height) {
  dom.parentElement.style.height = this.height + "px";
} else {
  dom.parentElement.style.height = "auto";
}
```

该写法只改了外层容器高度，内部 `.w-e-text` min-height 仍为 300px，高度约束失效。

### 修改内容

| 文件                                                             | 修改内容                                                      |
| ---------------------------------------------------------------- | ------------------------------------------------------------- |
| apps/web-openlibing/src/views/sca/component/wangEditor/index.vue | 高度设置迁移至 create 前 `editor.config.height` 配置（+8/-6） |

修复实现：

```js
// 高度必须在 create 之前通过 config.height 设置：
// create 后再改容器高度，.w-e-text 的 min-height 仍是默认 300px，
// 内容超出可视高度时会被 overflow:hidden 的容器裁切且无法滚动
if (this.height) {
  editor.config.height = this.height;
}

editor.create();

// ...
if (this.minHeight) {
  const dom = document.getElementById(editor.textElemId);
  dom.parentElement.style.minHeight = this.minHeight + "px";
}
```

要点：

- `height` 通过 `editor.config.height` 在 create 前设置，由 wangEditor 内部完成容器与文本区高度初始化
- 移除 create 后对 `dom.parentElement.style.height` 的分支设置（`height`/`auto`）
- `minHeight` 行为保持不变，仍通过容器 style.minHeight 设置，但 `dom` 查询移入对应 if 块内（原 else 分支删除后避免空引用）
- 与 `src/components/WangEditor.vue` 的实现方式对齐

### 影响范围

- 仅修改 SCA 模块 wangEditor 封装组件内部高度设置逻辑，不改变组件对外 props/事件接口
- 不涉及数据模型、后端接口变更
- 无安全影响

## 参考

- 业务 Issue：openlibing/openlibing-web#303
- 业务 PR：https://gitcode.com/openlibing/openlibing-web/merge_requests/801
- commit：6bb7b506 fix(sca): set wangEditor height via config before create
