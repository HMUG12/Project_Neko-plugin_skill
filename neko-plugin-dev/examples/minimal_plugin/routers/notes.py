"""Router 子包示例：必须继承 PluginRouter。

注意：@llm_tool 只扫插件主类，不要写在 Router 里（旧版示例犯过这个错）。
也不要在 Router 上调用主类的方法（旧版 web.py 的 self._reload_config()）。
"""
from typing import Annotated

from plugin.sdk.plugin import PluginRouter, plugin_entry, Ok, Err, SdkError

MAX_NOTES = 50


class NotesRouter(PluginRouter):
    def __init__(self):
        super().__init__(prefix="notes", name="notes")
        self._notes: list[str] = []

    @plugin_entry(id="add_note", name="添加笔记", description="添加一条笔记")
    async def add_note(self, text: Annotated[str, "笔记内容"] = "", **_):
        clean = str(text).strip()[:200]
        if not clean:
            return Err(SdkError("text 不能为空"))
        if len(self._notes) >= MAX_NOTES:
            return Err(SdkError("笔记数量已达上限"))
        self._notes.append(clean)
        return Ok({"count": len(self._notes)})

    @plugin_entry(id="list_notes", name="列出笔记", description="列出已添加的笔记")
    async def list_notes(self, **_):
        return Ok({"notes": list(self._notes)})
