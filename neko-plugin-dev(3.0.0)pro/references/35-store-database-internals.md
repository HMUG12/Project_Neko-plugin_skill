# 35 — PluginStore 与 PluginDatabase 内部机制

> **来源**：N.E.K.O-main `plugin/core/` 深度逆向分析  
> **适用**：理解 `self.store` 和 `self.db` 的内部工作原理，正确使用数据持久化

---

## 1. 两种持久化机制

N.E.K.O 提供两种不同的数据持久化机制：

| 特性 | PluginStore (`self.store`) | PluginDatabase (`self.db`) |
|------|---------------------------|---------------------------|
| 存储引擎 | JSON 文件 | SQLite |
| 数据结构 | 键值对 (dict) | 关系表 (SQL) |
| 适用场景 | 配置、状态、少量数据 | 大量结构化数据 |
| 查询能力 | 按 key 读取 | SQL 查询 |
| 事务支持 | 无 | 有 |
| 性能 | 小数据量优秀 | 大数据量优秀 |

---

## 2. PluginStore（键值存储）

### 启用

```toml
# plugin.toml
[plugin.store]
enabled = true
```

### 基本 API

```python
# 读取
value = await self.store.get("my_key")
all_data = await self.store.dump()  # 返回完整 dict

# 写入
await self.store.set("my_key", "value")
await self.store.set("nested", {"a": 1, "b": 2})

# 删除
await self.store.delete("my_key")

# 批量
await self.store.update({"key1": "val1", "key2": "val2"})
```

### 内部实现

```python
# 伪代码
class PluginStore:
    def __init__(self, plugin_id, data_dir):
        self._file = data_dir / f"{plugin_id}_store.json"
        self._data = self._load()  # 启动时加载到内存

    def _load(self) -> dict:
        if self._file.exists():
            return json.loads(self._file.read_text())
        return {}

    def _save(self):
        self._file.write_text(json.dumps(self._data, indent=2))

    async def set(self, key, value):
        self._data[key] = value
        self._save()  # 每次写入都持久化到磁盘

    async def get(self, key):
        return self._data.get(key)

    async def dump(self):
        return dict(self._data)
```

### 关键特性

1. **全量加载**：启动时将整个 JSON 文件加载到内存
2. **每次写入都持久化**：`set()` 立即写入磁盘
3. **不是并发安全的**：多线程同时 `set()` 可能丢失数据
4. **文件路径**：`data_path / "{plugin_id}_store.json"`

### 使用场景

```python
# ✅ 适合：少量配置、状态标记
await self.store.set("last_scan_time", time.time())
await self.store.set("user_preferences", {"theme": "dark"})

# ❌ 不适合：大量数据、频繁更新
# 应该用 self.db 代替
```

### 陷阱 35-1：大量数据用 store

```python
# ❌ 错误：每次 set 都写整个文件到磁盘
for item in large_list:  # 10000 条
    await self.store.set(f"item_{item['id']}", item)

# ✅ 正确：使用数据库
session = unwrap(await self.db.session())
for item in large_list:
    await session.execute("INSERT INTO items VALUES (?, ?)", ...)
await session.commit()
```

### 陷阱 35-2：并发写入 store

```python
# ❌ 错误：多线程并发 set 可能丢失数据
async def handler1():
    await self.store.set("counter", current + 1)

async def handler2():
    await self.store.set("counter", current + 1)  # 竞态！

# ✅ 正确：加锁保护
with self._lock:
    current = await self.store.get("counter") or 0
    await self.store.set("counter", current + 1)
```

---

## 3. PluginDatabase（SQLite 数据库）

### 启用

```toml
# plugin.toml
[plugin.database]
enabled = true
```

### 基本 API

```python
# 获取会话
session = unwrap(await self.db.session())

# 执行 SQL
await session.execute("CREATE TABLE IF NOT EXISTS ...")
await session.execute("INSERT INTO t VALUES (?, ?)", (val1, val2))
cursor = await session.execute("SELECT * FROM t WHERE ...")
rows = cursor.fetchall()  # 同步调用！

# 提交
await session.commit()

# 关闭
await session.close()
```

### 关键约束

| 操作 | 支持 | 不支持 |
|------|------|--------|
| `session.execute()` | ✅ | — |
| `session.executemany()` | ❌ | 必须逐行 execute |
| `cursor.fetchall()` | ✅ (同步) | ❌ 不能 await |
| `cursor.fetchone()` | ✅ (同步) | ❌ 不能 await |
| 事务 | ✅ commit/rollback | — |

### 完整 CRUD 模式

```python
# CREATE
async def _ensure_tables(self):
    session = unwrap(await self.db.session())
    try:
        await session.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await session.execute(
            "CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)"
        )
        await session.commit()
    finally:
        await session.close()

# INSERT
async def _insert(self, name: str):
    session = unwrap(await self.db.session())
    try:
        await session.execute(
            "INSERT INTO items (name) VALUES (?)", (name,)
        )
        await session.commit()
    finally:
        await session.close()

# SELECT
async def _query(self, keyword: str) -> list[dict]:
    session = unwrap(await self.db.session())
    try:
        cursor = await session.execute(
            "SELECT * FROM items WHERE name LIKE ?", (f"%{keyword}%",)
        )
        rows = cursor.fetchall()  # ← 同步调用
        return [dict(r) for r in rows]
    finally:
        await session.close()

# UPDATE
async def _update(self, item_id: int, name: str):
    session = unwrap(await self.db.session())
    try:
        await session.execute(
            "UPDATE items SET name = ? WHERE id = ?", (name, item_id)
        )
        await session.commit()
    finally:
        await session.close()

# DELETE
async def _delete(self, item_id: int):
    session = unwrap(await self.db.session())
    try:
        await session.execute(
            "DELETE FROM items WHERE id = ?", (item_id,)
        )
        await session.commit()
    finally:
        await session.close()
```

### 批量插入模式

```python
# ✅ 正确：分批 + 逐行 + 分批 commit
BATCH_SIZE = 500
for i in range(0, len(items), BATCH_SIZE):
    batch = items[i:i + BATCH_SIZE]
    for item in batch:
        await session.execute(
            "INSERT INTO items (name) VALUES (?)", (item["name"],)
        )
    await session.commit()  # 每批提交一次
```

---

## 4. PluginStatePersistence（状态持久化）

### 用途

存储插件的运行时状态，跨重启保留。

```python
# 保存状态
await self.state.set("last_active_time", time.time())
await self.state.set("processing_queue", queue_data)

# 恢复状态
last_time = await self.state.get("last_active_time")
queue_data = await self.state.get("processing_queue")
```

### 与 PluginStore 的区别

| | PluginStore | PluginStatePersistence |
|------|------------|----------------------|
| 用途 | 用户配置、偏好设置 | 运行时状态 |
| 内容 | 配置项、用户数据 | 队列、进度、缓存 |
| 用户可见 | 是（设置面板） | 否（内部状态） |
| 持久化 | JSON 文件 | JSON 文件 |

---

## 5. data_path（私有数据目录）

```python
# 获取插件私有目录下的子路径
cache_dir = self.data_path("cache")       # → Path(".../data/my_plugin/cache")
output_dir = self.data_path("output")     # → Path(".../data/my_plugin/output")
temp_file = self.data_path("tmp") / "temp.dat"

# 确保目录存在
cache_dir.mkdir(parents=True, exist_ok=True)

# 存储文件
file_path = self.data_path("songs") / f"{song_name}.mp3"
with open(file_path, "wb") as f:
    f.write(audio_data)
```

---

## 6. 数据持久化策略选择

```
需要持久化数据？

├── 少量配置/状态 (< 1KB)？
│   └── → PluginStore (self.store)
│
├── 大量结构化数据 (> 100 条)？
│   └── → PluginDatabase (self.db)
│
├── 二进制文件（音频、图片等）？
│   └── → data_path + 直接文件 I/O
│
├── 运行时状态（队列、缓存）？
│   └── → PluginStatePersistence (self.state)
│
└── 用户可见配置？
    └── → plugin.toml [settings] + self.config
```

---

## 相关文档

- [02-python-plugin](02-python-plugin.md) — 数据库基本模式
- [10-performance](10-performance.md) — 批量处理优化
- [07-gotchas](07-gotchas.md) — executemany 陷阱
- [25-concurrency-race-conditions](25-concurrency-race-conditions.md) — store 并发写入
