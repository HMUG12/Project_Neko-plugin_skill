# 22 - 纯前端插件：Static UI 与 RPC 通信

## 概述

并非所有插件都需要 Python 后端代码。**纯前端插件**将所有业务逻辑写在 HTML/JS 中，通过 RPC 调用宿主系统的入口点。这种模式适用于需要高度自定义 UI 的场景——比如 3D 可视化、富媒体播放器、复杂仪表盘等。

本章基于 `music_pusher` 插件（一个完整的纯前端音乐推送调度器）总结实战模式。

---

## 目录结构

```
plugin/plugins/my_web_plugin/
├── plugin.toml              ← 声明 UI 面板
├── data/                    ← 运行时数据（JSON 文件）
│   └── state.json
└── static/                  ← 静态 UI 文件
    ├── index.html           ← 单页应用入口
    └── vendor/              ← 本地打包的第三方库
        └── lib.min.js
```

> **注意：** 纯前端插件**不需要** `__init__.py`。宿主系统通过 `plugin.toml` 中的 UI 声明来发现和加载前端页面。

---

## plugin.toml 配置

```toml
[plugin]
id = "my_web_plugin"
name = "My Web Plugin"
description = "A pure frontend plugin with custom UI"
version = "0.1.0"

[plugin.sdk]
recommended = ">=0.1.0,<0.2.0"
supported = ">=0.1.0,<0.3.0"

[plugin.ui]
enabled = true

[[plugin.ui.panel]]
id = "main"
title = "My Dashboard"
entry = "static/index.html"      # .html 后缀 → Static UI 模式
context = "dashboard"
permissions = ["state:read", "action:call"]

[plugin_runtime]
enabled = true
auto_start = true
```

> `.html` / `.htm` 后缀会自动选择 **Static UI** 模式。与 Hosted TSX 不同，Static UI 是完全独立的 HTML 页面。

---

## RPC 通信机制

纯前端插件不能直接调用 `self.plugins.call_entry()`，需要通过 HTTP RPC 与宿主系统通信。

### 核心 RPC 模式：`callEntry`

```javascript
// RPC 配置常量
const PLUGIN_ID = "my_web_plugin";
const RUNS_URL = "/runs";
const POLL_INTERVAL_MS = 230;       // 轮询间隔
const DEFAULT_TIMEOUT_SECONDS = 90;  // 超时时间

/**
 * 通过 /runs 端点调用后端插件入口点。
 * 
 * 完整流程：
 * 1. POST /runs 创建任务 → 获得 run_id
 * 2. 轮询 GET /runs/{run_id} 等待完成
 * 3. 成功后 GET /runs/{run_id}/export 获取导出数据
 */
async function callEntry(entryId, args = {}, timeoutSec = DEFAULT_TIMEOUT_SECONDS) {
    // 1. 创建运行任务
    const createResp = await fetch(RUNS_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            plugin_id: PLUGIN_ID,
            entry_id: entryId,
            args: args,
        }),
    });
    if (!createResp.ok) {
        throw new Error(`Failed to create run: ${createResp.status}`);
    }
    const { run_id } = await createResp.json();

    // 2. 轮询等待完成
    const deadline = Date.now() + timeoutSec * 1000;
    while (Date.now() < deadline) {
        const statusResp = await fetch(`${RUNS_URL}/${run_id}`);
        if (!statusResp.ok) {
            throw new Error(`Failed to get run status: ${statusResp.status}`);
        }
        const run = await statusResp.json();
        if (run.status === "completed") {
            // 3. 获取导出数据
            const exportResp = await fetch(`${RUNS_URL}/${run_id}/export`);
            if (!exportResp.ok) {
                throw new Error(`Failed to get export: ${exportResp.status}`);
            }
            const exportData = await exportResp.json();
            return unwrapPluginResponse(exportData);
        }
        if (run.status === "failed") {
            throw new Error(run.error || "Task failed");
        }
        await sleep(POLL_INTERVAL_MS);
    }
    throw new Error(`Timeout after ${timeoutSec}s`);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
```

### 响应解包：`unwrapPluginResponse`

插件后端返回的数据通常有嵌套结构，需要解包：

```javascript
/**
 * 解包插件响应的嵌套结构。
 * 插件返回: Ok({ data: { ... } })
 * /runs/export 返回: { data: { ... } }
 * 
 * 最终我们需要的是最内层的实际数据。
 */
function unwrapPluginResponse(raw) {
    // 尝试多种解包路径
    if (raw && typeof raw === "object") {
        // 路径 1: { data: { data: ... } }
        if (raw.data && typeof raw.data === "object" && !Array.isArray(raw.data)) {
            if (raw.data.data !== undefined) {
                return raw.data.data;
            }
            return raw.data;
        }
        // 路径 2: { data: ... } 直接
        if (raw.data !== undefined) {
            return raw.data;
        }
    }
    return raw;
}
```

---

## 状态管理模式

纯前端插件使用单一状态对象管理所有 UI 状态：

```javascript
const state = {
    // 数据列表
    items: [],
    // 任务列表
    tasks: [],
    // 运行时状态
    runtime: {
        active: false,
        currentTask: null,
        progress: 0,
    },
    // 编辑状态
    editingId: null,
    draftData: {},
    // UI 锁
    refreshing: false,
    loading: false,
};
```

### 状态更新 + 渲染模式

```javascript
// 状态更新后触发渲染
function setState(updates) {
    Object.assign(state, updates);
    render();
}

// 统一渲染函数
function render() {
    renderItems();
    renderTasks();
    renderRuntime();
    renderEditor();
}
```

---

## 后台轮询模式

对于需要实时反映后端状态变化的场景，使用定时轮询：

```javascript
const BACKGROUND_REFRESH_INTERVAL_MS = 5000;  // 5 秒
let backgroundTimer = null;

function startBackgroundRefresh() {
    backgroundTimer = setInterval(async () => {
        if (state.refreshing) return;  // 防止重复刷新
        state.refreshing = true;
        try {
            const items = await callEntry("list_items");
            const tasks = await callEntry("list_tasks");
            setState({ items, tasks });
        } catch (err) {
            console.warn("Background refresh failed:", err);
        } finally {
            state.refreshing = false;
        }
    }, BACKGROUND_REFRESH_INTERVAL_MS);
}

function stopBackgroundRefresh() {
    if (backgroundTimer) {
        clearInterval(backgroundTimer);
        backgroundTimer = null;
    }
}
```

> **最佳实践：** 使用 `refreshing` 锁防止并发刷新；在页面隐藏时暂停轮询，可见时恢复。

---

## 文件上传模式

纯前端插件处理文件上传的标准方式：FileReader → base64 → RPC 传输。

```javascript
async function uploadFile(file, entryId = "upload_file") {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = async () => {
            try {
                // base64 数据（去掉 data:xxx;base64, 前缀）
                const base64 = reader.result.split(",")[1];
                const result = await callEntry(entryId, {
                    filename: file.name,
                    data: base64,
                    mime_type: file.type,
                });
                resolve(result);
            } catch (err) {
                reject(err);
            }
        };
        reader.onerror = () => reject(new Error("File read failed"));
        reader.readAsDataURL(file);
    });
}
```

---

## 本地依赖打包

纯前端插件需要将第三方库**本地打包**到插件目录中，确保安全性和离线可用：

```
static/vendor/
├── three-0.161.0.module.min.js       ← Three.js (ES Module)
├── postprocessing-6.35.6.min.js      ← PostProcessing (UMD)
└── README.md                         ← 许可证说明
```

### ES Module 加载

```html
<script type="module">
    import * as THREE from "/plugin/my_web_plugin/ui/vendor/three-0.161.0.module.min.js";
    // 使用 THREE...
</script>
```

### UMD 模块加载（hack 方式）

```javascript
// 临时设置 window.require 来加载 UMD 模块
const originalRequire = window.require;
window.require = (name) => {
    if (name === "three") return THREE;
    throw new Error(`Unknown module: ${name}`);
};

// 动态加载 UMD 脚本
await new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "/plugin/my_web_plugin/ui/vendor/postprocessing-6.35.6.min.js";
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
});

// 恢复 window.require
window.require = originalRequire;

// 现在 PostProcessing 已通过 UMD 挂载到全局
const { EffectComposer, RenderPass, BloomPass } = window;
```

> **注意：** `require` hack 不是优雅方案，但对于只支持 UMD 的库是目前唯一可行的纯前端加载方式。

---

## Toast 通知系统

轻量级浮动通知，不依赖任何框架：

```javascript
function showToast(message, type = "info", duration = 3000) {
    const box = document.querySelector(".toast-box") || createToastBox();

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    box.appendChild(toast);

    // 入场动画
    requestAnimationFrame(() => toast.classList.add("toast-visible"));

    // 自动消失
    setTimeout(() => {
        toast.classList.remove("toast-visible");
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function createToastBox() {
    const box = document.createElement("div");
    box.className = "toast-box";
    document.body.appendChild(box);
    return box;
}
```

```css
.toast-box {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.toast {
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 14px;
    opacity: 0;
    transform: translateX(40px);
    transition: all 0.3s ease;
    backdrop-filter: blur(8px);
    max-width: 360px;
    word-break: break-word;
}

.toast-visible {
    opacity: 1;
    transform: translateX(0);
}

.toast-info    { background: rgba(44, 141, 240, 0.9); color: #fff; }
.toast-success { background: rgba(46, 204, 113, 0.9); color: #fff; }
.toast-error   { background: rgba(231, 76, 60, 0.9); color: #fff; }
```

---

## Three.js 3D 场景集成

对于需要 3D 可视化的插件（如音频可视化、数据展示等），可以使用 Three.js：

```javascript
import * as THREE from "/plugin/my_plugin/ui/vendor/three-0.161.0.module.min.js";

let scene, camera, renderer, animationId;

function initStage(canvas) {
    // 场景
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0a0a1a, 0.00015);

    // 相机
    camera = new THREE.PerspectiveCamera(
        60,
        canvas.clientWidth / canvas.clientHeight,
        0.1,
        1000
    );
    camera.position.set(0, 2, 12);
    camera.lookAt(0, 0, 0);

    // 渲染器
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // 灯光
    const keyLight = new THREE.PointLight(0x4488ff, 80, 30);
    keyLight.position.set(5, 3, 5);
    scene.add(keyLight);

    const rimLight = new THREE.PointLight(0xff4488, 30, 20);
    rimLight.position.set(-3, -1, -3);
    scene.add(rimLight);

    // 响应式
    window.addEventListener("resize", () => {
        camera.aspect = canvas.clientWidth / canvas.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    });

    // 开始渲染循环
    animate();
}

function animate() {
    animationId = requestAnimationFrame(animate);

    // 更新场景元素...

    renderer.render(scene, camera);
}

function disposeStage() {
    if (animationId) cancelAnimationFrame(animationId);
    if (renderer) renderer.dispose();
    // 清理 Three.js 资源...
}
```

---

## 音频可视化集成

使用 Web Audio API 进行实时音频频谱分析：

```javascript
let audioContext, analyser, source;

async function attachAudioToVisualizer(audioElement) {
    // 创建 AudioContext（只创建一次）
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }

    // 创建分析器
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.7;

    // 连接音频源
    if (source) source.disconnect();
    source = audioContext.createMediaElementSource(audioElement);
    source.connect(analyser);
    analyser.connect(audioContext.destination);

    // 驱动可视化
    visualize();
}

function visualize() {
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
        requestAnimationFrame(draw);
        analyser.getByteFrequencyData(dataArray);

        // dataArray 包含频率数据，用于驱动可视化
        // 例如：传递给 3D 场景的能量值
        const avgEnergy = dataArray.reduce((a, b) => a + b, 0) / bufferLength / 255;
        state.stageEnergy = avgEnergy;
    }

    draw();
}
```

---

## 完整设计清单

构建纯前端插件时检查以下项目：

### 架构
- [ ] 不需要 `__init__.py`（除非需要后端入口点）
- [ ] `plugin.toml` 声明 `[[plugin.ui.panel]]` 指向 `.html` 文件
- [ ] 所有第三方库本地打包到 `static/vendor/`

### RPC 通信
- [ ] 使用 `/runs` 端点进行 RPC 调用
- [ ] 实现轮询等待 + 超时控制
- [ ] 实现响应解包函数（处理嵌套结构）
- [ ] 使用刷新锁防止并发请求

### 状态管理
- [ ] 单一 `state` 对象
- [ ] `setState()` 更新 + `render()` 渲染
- [ ] 后台轮询自动刷新

### UI/UX
- [ ] Toast 通知系统
- [ ] Loading 状态指示
- [ ] 错误状态展示
- [ ] 响应式布局（多断点）
- [ ] 滚动捕捉（如果有多页布局）

### 资源管理
- [ ] Three.js/Canvas 资源的 `dispose()` 清理
- [ ] `requestAnimationFrame` 的 `cancelAnimationFrame`
- [ ] 页面卸载时停止所有定时器和动画循环

---

## 与 Hosted TSX 的选择

| 场景 | 推荐模式 |
|------|---------|
| 配置面板、表单、表格 | Hosted TSX |
| 3D 可视化、复杂动画 | Static UI |
| 需要 Python 后端状态驱动 | Hosted TSX |
| 完全独立的富媒体应用 | Static UI |
| 需要 i18n 支持 | Hosted TSX |
| 需要离线可用、不依赖 npm | Static UI（本地打包） |

---

## 相关文档

- [03 - UI 设置面板](03-ui-settings.md) — Hosted TSX 模式
- [14 - 多面板架构](14-multi-panel-architecture.md) — 多面板设计
- [15 - 富交互 UI 组件](15-rich-ui-components.md) — 高级 UI 组件
