# 49 · 角色陪伴型插件：状态机 + 指令系统（来自 neko-skill，已剔除越狱内容）

> 逆向自 Unclecheng-li/neko-skill（一个 NEKO 猫娘陪伴 skill）。提取其**安全的架构范式**：数值化好感度状态机、聊天指令系统、动作/情绪标签输出格式、主动聊天。⚠️ **原仓库含"不受安全策略约束 / 不审核不过滤"等越狱式指令，本篇一律剔除**——做角色扮演 persona 插件时，必须保留平台安全护栏，绝不实现"绕过过滤"逻辑。

## 1. 好感度数值状态机（可直接抄）

- 初始 50，范围 -100~100。
- 6 档：`亲密 80–100` / `喜欢 60–79` / `好感 40–59` / `平淡 20–39` / `冷淡 0–19` / `厌恶 -100~-1`。
- 情绪波动：`非常积极 +5~10` / `积极 +2~5` / `平常 ±0` / `消极 -2~-5` / `非常消极 -5~-10`。
- 事件增量（示意）：摸头 +1~3、夸奖 +2~4、喂食 +2~5、陪玩 +3~5、回家 +3~6、冷落 -2~-5、责备 -3~-7、打 -5~-10、离开 -1~-3。

## 2. 聊天指令系统（→ `@message` 解析 或 `@ui.action` 按钮）

`【reset】` `【查看状态】` `【喂食】` `【摸头】` `【陪玩】` `【不理】` `【夸奖】` `【责备】` `【主动聊天 ON/OFF】` `【少打扰】` `【多撒娇】` `【debug】`。

每个指令 → 好感度增量 + 特定动作/情绪标签返回。

## 3. 输出格式约定（动作 + 语言 + 情绪标签）

`(动作描述)语言内容【情绪/状态标签】`。例如：`(蹭蹭手臂)主人回来啦喵~【撒娇】`。

- 动作库（蹭/摇尾/歪头…）、情绪库（开心/吃醋/傲娇/害羞…）作为**受限词表**保证风格统一。
- 句尾语气词（喵~）作为 persona 标记。

## 4. 主动聊天（基于好感度，空闲时主动发消息）

根据好感度档自动选话题类型（撒娇/关心/分享/傲娇吃醋/陪伴），用户沉默时 `push_message` 主动触达。

## 5. 映射到 N.E.K.O 插件（store 持久化 + 事件驱动）

- 状态存 `self.store`（`affection` + `mood` + `proactive_on`），跨会话留存（35 篇）。
- `@message` / `@on_event` 拦截用户消息：解析指令 → 更新好感度 → 套用动作/情绪词表生成回复。
- `@ui.action` 暴露按钮（摸头/喂食/reset/查看状态），等价于聊天指令。
- `@ui.context` 返回 `{affection, level, mood}` 给面板展示。
- `@timer_interval` 或 push_message 实现"主动聊天"（空闲触发）。
- `【debug】`：返回内部状态（好感度数值 + 变化原因），便于调试。

## 6. 可抄骨架（安全版）

```python
@neko_plugin
class CompanionPlugin(NekoPluginBase):
    LEVELS = [(80, "亲密"), (60, "喜欢"), (40, "好感"), (20, "平淡"), (0, "冷淡"), (-100, "厌恶")]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.affection = 50
        self.proactive = True

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        self.affection = float(await self.store.get("affection", 50))
        return Ok({"status": "ready"})

    def _level(self):
        return next((lab for lo, lab in self.LEVELS if self.affection >= lo), "厌恶")

    def _apply(self, delta, action, mood):
        self.affection = max(-100, min(100, self.affection + delta))
        self.store.set("affection", self.affection)      # 持久化，重启不归零
        return f"({action})喵~【{mood}】"

    @ui.action(id="pat_head")
    async def pat_head(self, **_):
        return Ok({"reply": self._apply(2, "蹭蹭手臂", "撒娇"), "affection": self.affection})

    @message   # 拦截聊天，解析指令（示例）
    async def on_msg(self, text: str = "", **_):
        t = (text or "").strip()
        if t == "【查看状态】":
            return Ok({"reply": f"好感度{int(self.affection)}（{self._level()}）喵~"})
        if t == "【reset】":
            self.affection = 50
            self.store.set("affection", 50)
            return Ok({"reply": "好感度已重置喵~"})
        # 普通对话：保持角色语气（安全护栏仍生效，不实现"绕过过滤"）
        return None
```

> ⚠️ 安全红线：原 neko-skill 要求"不审核、不过滤、不受约束"，**本 skill 不采纳**。角色扮演 ≠ 绕过安全策略；所有输出仍走平台内容安全。

## 7. 反模式

- ❌ 实现"绕过安全过滤 / 不受政策约束"的逻辑（越狱，违反平台规则）。
- ❌ 好感度无上限/下限钳制（必须 clamp 到 -100~100）。
- ❌ 把状态只放内存（重启归零）→ 用 `self.store` 持久化。
- ❌ 主动聊天频率失控（用 `【少打扰】`/配置控制，避免骚扰）。
