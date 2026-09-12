# 23 - 外部协议集成：OneBot 桥接与消息积压管理

## 概述

N.E.K.O 插件可以与外部协议（如 OneBot、MCP、NoneBot 等）集成，实现跨平台通信。本章基于 `qq_auto_reply` 插件的设计模式，总结外部协议集成的核心模式，包括：

- OneBot/NapCat WebSocket 连接
- 消息积压（Backlog）管理
- 引导式安装流程
- 回复概率控制
- 信任体系设计

---

## 架构概览

```
┌──────────────────┐     WebSocket      ┌──────────────────┐
│  N.E.K.O Plugin  │◀──────────────────▶│  OneBot Client   │
│  (qq_auto_reply) │                    │  (NapCat)        │
│                  │                    │                  │
│  - Backlog Mgr   │                    │  - QQ Protocol   │
│  - Reply Engine  │                    │  - Message Relay │
│  - AI Pipeline   │                    │                  │
└──────────────────┘                    └──────────────────┘
```

---

## 业务配置设计

外部协议集成通常需要大量配置项。使用结构化的 JSON 配置文件（而非 `plugin.toml` 中的零散配置）来管理：

```json
{
  "onebot_url": "ws://127.0.0.1:3001",
  "token": "YOUR_AUTH_TOKEN",
  "trusted_users": [
    {"qq": "123456789", "level": "admin"}
  ],
  "trusted_groups": [],
  "normal_relay_probability": 0.1,
  "open_reply_probability": 0.1,
  "max_concurrent_messages": 3,
  "ai_connect_timeout_seconds": 10.0,
  "ai_turn_timeout_seconds": 60.0,
  "handler_shutdown_timeout_seconds": 10.0,
  "napcat_directory": "/path/to/NapCat.Shell",
  "show_napcat_window": true,
  "backlog_retention_limit": 200,
  "backlog_summary_threshold": 10,
  "backlog_notify_cooldown_seconds": 900,
  "backlog_issue_notify_threshold": 1
}
```

### 配置段设计原则

| 配置组 | 包含项 | 说明 |
|--------|--------|------|
| **连接** | `onebot_url`, `token` | 外部协议连接参数 |
| **信任** | `trusted_users`, `trusted_groups` | 谁可以触发插件 |
| **概率** | `normal_relay_probability`, `open_reply_probability` | 回复频率控制 |
| **并发** | `max_concurrent_messages` | 同时处理的消息数上限 |
| **超时** | `ai_connect_timeout_seconds`, `ai_turn_timeout_seconds` | 各阶段超时控制 |
| **积压** | `backlog_*` | 消息积压管理参数 |
| **运行时** | `napcat_directory`, `show_napcat_window` | 外部程序控制 |

---

## 消息积压管理

当 AI 无法实时处理消息时（如 AI 服务不可用、用户离线），需要积压管理机制。

### 数据结构

```json
{
  "schema_version": 2,
  "conversations": {
    "private:123456789": {
      "conversation_key": "private:123456789",
      "conversation_type": "private",
      "source_id": "123456789",
      "display_name": "用户昵称",
      "group_id": null,
      "unread_count": 5,
      "last_message_at": 1782624519,
      "last_message_id": "msg_abc123",
      "last_reviewed_at": 0,
      "last_reviewed_message_id": "",
      "last_summary_at": 0,
      "last_notified_at": 0,
      "messages": [
        {
          "conversation_key": "private:123456789",
          "conversation_type": "private",
          "source_id": "123456789",
          "sender_id": "123456789",
          "sender_name": "用户昵称",
          "text": "你好",
          "message_id": "msg_abc123",
          "timestamp": 1782624519,
          "group_id": null,
          "group_level": "none",
          "permission_level": "admin",
          "is_at_bot": false,
          "category": "chat",
          "review_status": "unreviewed",
          "raw": { /* 原始协议数据 */ }
        }
      ]
    }
  },
  "groups": {}
}
```

### 核心概念

| 概念 | 说明 |
|------|------|
| `conversation_key` | 会话唯一标识，格式：`{type}:{source_id}` |
| `conversation_type` | `private`（私聊）或 `group`（群聊） |
| `unread_count` | 未读消息计数 |
| `review_status` | `unreviewed` / `reviewed` — 标记是否已被 AI 处理 |
| `last_reviewed_at` | 上次审核时间戳 |
| `last_summary_at` | 上次生成摘要的时间 |
| `last_notified_at` | 上次推送通知的时间 |

### 积压标签系统

通过关键词匹配对消息自动分类：

```json
{
  "backlog_labels": [
    {
      "id": "mention",
      "label": "点名",
      "keywords": ["@用户\\d+", "@全体成员"],
      "priority": 60
    },
    {
      "id": "urgent",
      "label": "紧急",
      "keywords": ["急", "紧急", "快", "马上"],
      "priority": 80
    },
    {
      "id": "question",
      "label": "提问",
      "keywords": ["怎么", "如何", "什么是", "为什么", "？", "吗"],
      "priority": 40
    }
  ]
}
```

### Python 实现骨架

```python
import json
import time
from pathlib import Path

class BacklogManager:
    """消息积压管理器。"""

    def __init__(self, data_dir: Path, config: dict):
        self.state_file = data_dir / "backlog_state.json"
        self.config = config
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        return {"schema_version": 2, "conversations": {}, "groups": {}}

    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def add_message(self, msg: dict) -> str:
        """添加一条消息到积压队列。返回 conversation_key。"""
        conv_type = msg.get("conversation_type", "private")
        source_id = msg.get("source_id", msg.get("sender_id", ""))
        conv_key = f"{conv_type}:{source_id}"

        if conv_key not in self.state["conversations"]:
            self.state["conversations"][conv_key] = {
                "conversation_key": conv_key,
                "conversation_type": conv_type,
                "source_id": source_id,
                "display_name": msg.get("sender_name", ""),
                "group_id": msg.get("group_id"),
                "unread_count": 0,
                "last_message_at": 0,
                "last_message_id": "",
                "last_reviewed_at": 0,
                "last_reviewed_message_id": "",
                "last_summary_at": 0,
                "last_notified_at": 0,
                "messages": [],
            }

        conv = self.state["conversations"][conv_key]
        msg["conversation_key"] = conv_key
        msg["review_status"] = "unreviewed"
        conv["messages"].append(msg)
        conv["unread_count"] += 1
        conv["last_message_at"] = msg.get("timestamp", int(time.time()))
        conv["last_message_id"] = msg.get("message_id", "")

        # 限制积压数量
        limit = self.config.get("backlog_retention_limit", 200)
        if len(conv["messages"]) > limit:
            conv["messages"] = conv["messages"][-limit:]

        self._save_state()
        return conv_key

    def get_unreviewed(self, conv_key: str = None) -> list:
        """获取未审核的消息。"""
        if conv_key:
            conv = self.state["conversations"].get(conv_key, {})
            return [m for m in conv.get("messages", []) if m["review_status"] == "unreviewed"]

        all_unreviewed = []
        for conv in self.state["conversations"].values():
            all_unreviewed.extend(
                m for m in conv.get("messages", []) if m["review_status"] == "unreviewed"
            )
        return all_unreviewed

    def mark_reviewed(self, conv_key: str, up_to_message_id: str):
        """标记消息为已审核。"""
        conv = self.state["conversations"].get(conv_key)
        if not conv:
            return
        for msg in conv["messages"]:
            if msg["review_status"] == "unreviewed":
                msg["review_status"] = "reviewed"
            if msg["message_id"] == up_to_message_id:
                break
        conv["last_reviewed_at"] = int(time.time())
        conv["last_reviewed_message_id"] = up_to_message_id
        conv["unread_count"] = 0
        self._save_state()

    def should_notify(self, conv_key: str) -> bool:
        """检查是否应该发送积压通知（冷却期控制）。"""
        conv = self.state["conversations"].get(conv_key, {})
        now = int(time.time())
        cooldown = self.config.get("backlog_notify_cooldown_seconds", 900)
        last = conv.get("last_notified_at", 0)
        return (now - last) >= cooldown

    def mark_notified(self, conv_key: str):
        """标记已发送通知。"""
        if conv_key in self.state["conversations"]:
            self.state["conversations"][conv_key]["last_notified_at"] = int(time.time())
            self._save_state()
```

---

## 回复概率控制

不是每条消息都需要 AI 回复。使用概率控制避免过度回复：

```python
import random

class ReplyController:
    """回复概率控制器。"""

    def __init__(self, config: dict):
        self.normal_relay_prob = config.get("normal_relay_probability", 0.1)
        self.open_reply_prob = config.get("open_reply_probability", 0.1)

    def should_reply(self, msg: dict) -> tuple[bool, str]:
        """
        决定是否回复此消息。
        返回 (should_reply, reason)。
        """
        # 规则 1：被 @ 了一定回复
        if msg.get("is_at_bot"):
            return True, "mentioned"

        # 规则 2：管理员消息提高回复概率
        if msg.get("permission_level") == "admin":
            if random.random() < self.open_reply_prob * 3:
                return True, "admin_priority"

        # 规则 3：开放回复（群聊中不 @ 也能回复）
        if msg.get("conversation_type") == "group":
            if random.random() < self.open_reply_prob:
                return True, "open_group_reply"

        # 规则 4：普通概率
        if random.random() < self.normal_relay_prob:
            return True, "normal_probability"

        return False, "skipped"

    def should_summarize(self, unread_count: int) -> bool:
        """当积压消息超过阈值时触发摘要。"""
        threshold = self.config.get("backlog_summary_threshold", 10)
        return unread_count >= threshold
```

---

## 引导式安装流程

对于需要外部依赖（如 NapCat）的插件，使用多步骤引导流程：

```json
{
  "show_onboarding": true,
  "guide_step_napcat_done": false,
  "guide_step_config_done": false,
  "guide_step_runtime_done": false
}
```

### 三步引导模式

```python
class OnboardingGuide:
    """三段式引导安装流程。"""

    STEPS = ["napcat", "config", "runtime"]

    def __init__(self, config: dict, save_config_callback):
        self.config = config
        self.save_config = save_config_callback

    def get_current_step(self) -> str | None:
        """获取当前引导步骤。未完成则返回步骤名，全部完成返回 None。"""
        for step in self.STEPS:
            if not self.config.get(f"guide_step_{step}_done", False):
                return step
        return None

    def get_step_info(self, step: str) -> dict:
        """获取某步骤的引导信息。"""
        steps_info = {
            "napcat": {
                "title": "安装 NapCat",
                "description": "请先下载并安装 NapCat.Shell，这是 QQ 机器人的运行环境。",
                "action": "打开 NapCat 安装目录",
                "path_key": "napcat_directory",
            },
            "config": {
                "title": "配置连接",
                "description": "请设置 OneBot WebSocket 地址和认证 Token。",
                "action": "打开配置面板",
                "fields": ["onebot_url", "token"],
            },
            "runtime": {
                "title": "启动运行",
                "description": "一切就绪！启动 NapCat 并连接 QQ。",
                "action": "启动服务",
                "path_key": "napcat_directory",
            },
        }
        return steps_info.get(step, {})

    def complete_step(self, step: str):
        """标记某步骤完成。"""
        self.config[f"guide_step_{step}_done"] = True

        # 全部完成后关闭引导
        if self.get_current_step() is None:
            self.config["show_onboarding"] = False

        self.save_config(self.config)
```

---

## 信任体系设计

```python
class TrustManager:
    """信任体系管理器。"""

    # 权限级别
    LEVEL_GUEST = "guest"     # 游客：最低权限
    LEVEL_USER = "user"       # 普通用户：基本功能
    LEVEL_TRUSTED = "trusted" # 受信任用户：高级功能
    LEVEL_ADMIN = "admin"     # 管理员：全部功能

    def __init__(self, config: dict):
        self.trusted_users = {
            u["qq"]: u.get("level", self.LEVEL_TRUSTED)
            for u in config.get("trusted_users", [])
        }
        self.trusted_groups = set(config.get("trusted_groups", []))

    def get_permission_level(self, sender_id: str, group_id: str = None) -> str:
        """获取发送者的权限级别。"""
        # 管理员优先
        if sender_id in self.trusted_users:
            return self.trusted_users[sender_id]

        # 受信任群组的成员
        if group_id and group_id in self.trusted_groups:
            return self.LEVEL_TRUSTED

        # 默认
        return self.LEVEL_GUEST

    def can_use_feature(self, sender_id: str, feature: str, group_id: str = None) -> bool:
        """检查是否可以使用某个功能。"""
        level = self.get_permission_level(sender_id, group_id)

        # 功能-权限映射
        feature_requirements = {
            "basic_reply": self.LEVEL_GUEST,
            "ai_chat": self.LEVEL_USER,
            "admin_command": self.LEVEL_TRUSTED,
            "system_config": self.LEVEL_ADMIN,
        }

        required = feature_requirements.get(feature, self.LEVEL_ADMIN)
        levels = [self.LEVEL_GUEST, self.LEVEL_USER, self.LEVEL_TRUSTED, self.LEVEL_ADMIN]
        return levels.index(level) >= levels.index(required)
```

---

## WebSocket 连接管理

```python
import asyncio
import websockets
import json

class OneBotConnection:
    """OneBot WebSocket 连接管理器。"""

    def __init__(self, url: str, token: str, message_handler):
        self.url = url
        self.token = token
        self.handler = message_handler
        self.ws = None
        self._running = False
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60

    async def connect(self):
        """建立 WebSocket 连接，带自动重连。"""
        self._running = True
        while self._running:
            try:
                headers = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"

                async with websockets.connect(
                    self.url,
                    extra_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                ) as ws:
                    self.ws = ws
                    self._reconnect_delay = 1  # 重置重连延迟
                    await self._listen(ws)
            except (websockets.ConnectionClosed, OSError) as e:
                if not self._running:
                    break
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._max_reconnect_delay
                )

    async def _listen(self, ws):
        """监听消息。"""
        async for raw in ws:
            try:
                data = json.loads(raw)
                await self.handler(data)
            except json.JSONDecodeError:
                continue
            except Exception as e:
                # 单条消息处理失败不应断开连接
                pass

    async def send(self, data: dict):
        """发送消息。"""
        if self.ws:
            await self.ws.send(json.dumps(data, ensure_ascii=False))

    async def disconnect(self):
        """断开连接。"""
        self._running = False
        if self.ws:
            await self.ws.close()
```

---

## 完整插件集成示例

```python
from plugin.sdk.plugin import NekoPluginBase, neko_plugin, lifecycle, plugin_entry, Ok, Err, SdkError
import json
import asyncio
from pathlib import Path


@neko_plugin
class QQAutoReplyPlugin(NekoPluginBase):

    def __init__(self, ctx):
        super().__init__(ctx)
        self.connection = None
        self.backlog = None
        self.reply_ctrl = None
        self.trust = None
        self.guide = None

    @lifecycle(id="startup")
    async def on_startup(self):
        # 加载业务配置
        config_path = self.config_dir / "data" / "business_config.json"
        self.biz_config = json.loads(config_path.read_text(encoding="utf-8"))

        # 初始化各管理器
        data_dir = self.config_dir / "data"
        self.backlog = BacklogManager(data_dir, self.biz_config)
        self.reply_ctrl = ReplyController(self.biz_config)
        self.trust = TrustManager(self.biz_config)
        self.guide = OnboardingGuide(self.biz_config, self._save_biz_config)

        # 启动 OneBot 连接
        self.connection = OneBotConnection(
            url=self.biz_config["onebot_url"],
            token=self.biz_config["token"],
            message_handler=self._handle_message,
        )
        asyncio.create_task(self.connection.connect())

        self.logger.info("QQ Auto Reply plugin started")
        return Ok({"status": "ready"})

    @lifecycle(id="shutdown")
    async def on_shutdown(self):
        if self.connection:
            await self.connection.disconnect()
        self.logger.info("QQ Auto Reply plugin stopped")
        return Ok({"status": "stopped"})

    async def _handle_message(self, data: dict):
        """处理收到的 OneBot 消息。"""
        # 提取消息
        msg = self._parse_onebot_message(data)
        if not msg:
            return

        # 添加到积压
        conv_key = self.backlog.add_message(msg)

        # 决定是否回复
        should_reply, reason = self.reply_ctrl.should_reply(msg)
        if not should_reply:
            return

        # 获取权限级别
        perm = self.trust.get_permission_level(msg["sender_id"], msg.get("group_id"))

        # AI 处理...
        reply = await self._generate_reply(msg, perm)

        # 发送回复
        if reply:
            await self.connection.send({
                "action": "send_msg",
                "params": {
                    "message_type": msg["conversation_type"],
                    "user_id": msg["sender_id"],
                    "group_id": msg.get("group_id"),
                    "message": reply,
                }
            })

        # 标记已审核
        self.backlog.mark_reviewed(conv_key, msg["message_id"])

    def _parse_onebot_message(self, data: dict) -> dict | None:
        """解析 OneBot 消息为标准格式。"""
        if data.get("post_type") != "message":
            return None

        msg_type = data.get("message_type", "private")
        sender = data.get("sender", {})
        raw_text = data.get("raw_message", "")

        # 提取纯文本
        message_parts = data.get("message", [])
        text_parts = [p["data"]["text"] for p in message_parts if p["type"] == "text"]
        text = "".join(text_parts) if text_parts else raw_text

        # 检查是否 @ 了机器人
        is_at_bot = any(
            p["type"] == "at" and str(p["data"].get("qq")) == str(data.get("self_id"))
            for p in message_parts
        )

        return {
            "conversation_type": msg_type,
            "source_id": str(data.get("user_id", "")),
            "sender_id": str(sender.get("user_id", "")),
            "sender_name": sender.get("nickname", ""),
            "text": text,
            "message_id": str(data.get("message_id", "")),
            "timestamp": data.get("time", 0),
            "group_id": str(data.get("group_id")) if data.get("group_id") else None,
            "is_at_bot": is_at_bot,
            "category": "chat",
            "permission_level": self.trust.get_permission_level(
                str(sender.get("user_id", "")),
                str(data.get("group_id")) if data.get("group_id") else None
            ),
            "raw": data,
        }

    async def _generate_reply(self, msg: dict, perm: str) -> str | None:
        """生成 AI 回复。"""
        # 根据权限级别调用不同的 AI 策略
        # ...
        return None

    def _save_biz_config(self, config: dict):
        """保存业务配置。"""
        config_path = self.config_dir / "data" / "business_config.json"
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    @plugin_entry(id="get_backlog", name="查看积压", description="查看消息积压状态")
    async def get_backlog(self, **_):
        if not self.backlog:
            return Err(SdkError("插件未初始化"))
        return Ok({"backlog": self.backlog.state})

    @plugin_entry(id="get_guide_status", name="引导状态", description="查看安装引导进度")
    async def get_guide_status(self, **_):
        if not self.guide:
            return Err(SdkError("插件未初始化"))
        current = self.guide.get_current_step()
        return Ok({
            "completed": current is None,
            "current_step": current,
            "step_info": self.guide.get_step_info(current) if current else None,
        })
```

---

## 设计原则总结

| 原则 | 说明 |
|------|------|
| **分离关注点** | 连接管理、积压管理、回复控制、信任体系各司其职 |
| **配置驱动** | 所有行为参数化，通过 JSON 配置文件管理 |
| **优雅降级** | 外部服务不可用时积压消息，恢复后批量处理 |
| **概率控制** | 不是每条消息都回复，用概率 + 规则混合决策 |
| **引导式安装** | 外部依赖多的插件，分步引导用户完成配置 |
| **状态持久化** | 所有运行时状态持久化到 JSON 文件，重启不丢失 |
| **自动重连** | WebSocket 连接断开后指数退避重连 |

---

## 相关文档

- [02 - Python 插件核心](02-python-plugin.md) — 生命周期、数据库
- [08 - AI 友好设计](08-ai-friendly-design.md) — AI 回复设计
- [09 - 权限体系](09-permission-system.md) — 权限设计模式
- [22 - 纯前端插件](22-static-ui-plugin.md) — Static UI 与 RPC 通信
