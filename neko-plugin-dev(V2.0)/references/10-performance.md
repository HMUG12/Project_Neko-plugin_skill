# 性能优化模式

> 基于 `file_manager` 的磁盘 I/O 优化、内存优化和批量处理最佳实践。

---

## 1. asyncio.to_thread — 磁盘 I/O 不阻塞事件循环

```python
import asyncio

async def _scan_directory(self, root_path: str) -> int:
    """在线程池中执行磁盘遍历，不阻塞 asyncio 事件循环。"""
    # ❌ 错误 — 直接 await 同步 I/O
    entries = os.walk(root_path)  # 阻塞事件循环

    # ✅ 正确 — 用 asyncio.to_thread 把同步 I/O 丢到线程池
    entries = await asyncio.to_thread(self._walk_disk, root_path)

    # 然后回到主线程处理结果
    written = await self._flush_batch(entries)
    return written
```

**分离同步函数**：把纯同步的磁盘 I/O 逻辑提取到独立方法，方便 `asyncio.to_thread` 调用：

```python
def _walk_disk(self, root_path: str) -> list[tuple]:
    """纯同步函数，在 asyncio.to_thread 中执行。"""
    result = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # 过滤保护路径
        dirnames[:] = [d for d in dirnames if not self._is_protected(os.path.join(dirpath, d))]
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            if self._is_protected(fpath):
                continue
            st = os.stat(fpath)
            _, ext = os.path.splitext(fname)
            result.append((fpath, fname, ext, st.st_size, st.st_mtime, 0, dirpath))
    return result
```

**适用场景**：
- `os.walk()` — 遍历目录树
- `os.stat()` — 获取文件元数据
- `shutil.copy2()` / `shutil.copytree()` — 大文件复制
- `open().read()` — 大文件读取

---

## 2. 批量处理 + 分批提交

不要逐条提交数据库，也不要一次性提交全部：

```python
BATCH_SIZE = 500  # 每批 500 条

async def _flush_batch(self, batch: list[tuple]) -> int:
    session = unwrap(await self.db.session())
    try:
        for row in batch:
            await session.execute(
                "INSERT OR REPLACE INTO files (...) VALUES (?,?,?,?,?,?,?)",
                row,
            )
        await session.commit()  # 整批提交一次
    finally:
        await session.close()
    return len(batch)

# 在循环中分批处理
for i in range(0, total, BATCH_SIZE):
    batch = entries[i:i + BATCH_SIZE]
    written += await self._flush_batch(batch)
    # 每批之间可以更新进度
    self._update_progress("scanning", i + BATCH_SIZE, total)
```

**BATCH_SIZE 选择**：
- 500-1000：适合批量插入
- 太大：单次事务过长，可能超时
- 太小：事务开销过大

---

## 3. 增量索引 vs 全量索引

| | 全量索引 | 增量索引 |
|------|---------|---------|
| 触发时机 | 首次启动、手动触发 | 定时器（每小时） |
| 策略 | 完整遍历所有目录 | 对比磁盘与数据库 mtime |
| 数据量 | 全部写入 | 只写入变化部分 |
| 内存 | 存储完整元数据 | 只存储路径和 mtime |

```python
# 增量索引的内存优化：只存路径->mtime 映射
disk_mtimes: dict[str, float] = {}  # 不存完整元数据，只存 mtime
for entry in entries:
    disk_mtimes[entry[0]] = entry[4]  # entry[0]=path, entry[4]=mtime

# 对比差异
db_mtimes: dict[str, float] = {row["path"]: row["modified_time"] for row in rows}
deleted = set(db_mtimes.keys()) - set(disk_mtimes.keys())  # 磁盘上消失的
new = set(disk_mtimes.keys()) - set(db_mtimes.keys())      # 新增的
changed = {p for p in common if abs(disk_mtimes[p] - db_mtimes[p]) > 0.001}  # 修改的
```

---

## 4. 线程安全

```python
import threading

class MyPlugin:
    def __init__(self):
        self._index_lock = threading.Lock()
        self._is_indexing = False
        self._scan_progress = {}

    def _update_progress(self, phase, scanned, total, message):
        with self._index_lock:  # 线程安全更新
            self._scan_progress = {"scanned": scanned, "total": total, "phase": phase}

    async def _do_index(self):
        with self._index_lock:  # 防止重复触发
            if self._is_indexing:
                return {"skipped": True}
            self._is_indexing = True

        try:
            # ... 索引逻辑 ...
        finally:
            with self._index_lock:  # 确保锁一定释放
                self._is_indexing = False
```

**关键点**：
- `finally` 块中释放锁 — 确保异常时也能释放
- 进度更新也用锁 — 避免 UI 读取到不一致状态
- 定时器检查冻结状态 — `if self._frozen: return {"skipped": True}`

---

## 5. 数据库索引

在大表上创建索引，加速查询：

```python
async def _ensure_tables(self):
    session = unwrap(await self.db.session())
    try:
        # 建表
        await session.execute("CREATE TABLE IF NOT EXISTS files (...)")

        # 创建索引 — 加速搜索
        await session.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files(name)")
        await session.execute("CREATE INDEX IF NOT EXISTS idx_files_ext ON files(extension)")
        await session.execute("CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent_path)")
        await session.execute("CREATE INDEX IF NOT EXISTS idx_files_mtime ON files(modified_time)")
        await session.execute("CREATE INDEX IF NOT EXISTS idx_ops_action ON operation_logs(action)")
        await session.execute("CREATE INDEX IF NOT EXISTS idx_ops_timestamp ON operation_logs(timestamp)")
        await session.commit()
    finally:
        await session.close()
```

**哪些字段需要索引**：
- 搜索条件中使用的字段（`name`, `extension`, `parent_path`）
- 排序字段（`modified_time`, `timestamp`）
- 过滤字段（`is_dangerous`）

---

## 6. 编码检测 — 多编码回退

```python
# 先检测二进制
with open(file_path, "rb") as f:
    head = f.read(8192)
if b"\x00" in head:
    return {"is_binary": True, "content": None}

# 多编码尝试
for enc in ("utf-8", "gbk", "gb2312", "shift_jis", "big5", "euc-kr", "latin-1"):
    try:
        with open(file_path, "r", encoding=enc, errors="surrogateescape") as f:
            content = f.read()
        break
    except (UnicodeDecodeError, UnicodeError):
        continue
else:
    # latin-1 兜底：永远不会失败
    with open(file_path, "r", encoding="latin-1", errors="replace") as f:
        content = f.read()
```

**编码顺序**：从最常见到最不常见，`latin-1` 作为永不失败的兜底。

---

## 7. 启动优化

```python
@lifecycle(id="startup")
async def on_startup(self, **_):
    # 1. 同步等待：读配置 + 建表（必须快速，< 1 秒）
    cfg = await self.config.dump()
    self._load_settings(cfg)
    await self._ensure_tables()

    # 2. 后台任务：耗时操作
    asyncio.create_task(self._maybe_full_index())  # 不阻塞启动

    return Ok({"status": "ready"})

async def _maybe_full_index(self):
    """后台检查数据库是否为空，为空则触发全量索引。"""
    if not self.scan_paths:
        return  # 没配置扫描路径，跳过
    session = unwrap(await self.db.session())
    try:
        cursor = await session.execute("SELECT COUNT(*) AS cnt FROM files")
        if cursor.fetchone()["cnt"] == 0:
            await self._do_full_index()
    finally:
        await session.close()
```

---

## 8. 定时器中的 asyncio 处理

定时器方法运行在独立线程中，需要自己创建事件循环：

```python
@timer_interval(id="my_timer", seconds=3600, name="定时任务", auto_start=True)
def _on_timer(self, **_):
    """定时器在独立线程中执行，需要自己创建事件循环。"""
    if self._frozen:
        return Ok({"skipped": True})

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(self._async_task())
    finally:
        loop.close()

    return Ok({"status": "done"})
```

---

## 性能检查清单

- [ ] 磁盘 I/O 用了 `asyncio.to_thread` 吗？
- [ ] 批量处理用了 `BATCH_SIZE` 分批提交吗？
- [ ] 大表有索引吗（搜索字段、排序字段）？
- [ ] 启动耗时 < 10 秒吗（耗时操作放后台）？
- [ ] 增量更新比全量更新更高效吗？
- [ ] 多线程共享状态用了 `threading.Lock` 吗？
- [ ] 编码检测有多层回退吗？
- [ ] 定时器中有 `asyncio.new_event_loop()` 吗？

## 相关文档

- [02-python-plugin.md](02-python-plugin.md) — `asyncio.to_thread`、批量处理、定时器签名
- [11-undo-and-logging.md](11-undo-and-logging.md) — 操作后数据库同步（索引更新）
- [07-gotchas.md](07-gotchas.md) — #5 启动超时、#8 根目录路径匹配