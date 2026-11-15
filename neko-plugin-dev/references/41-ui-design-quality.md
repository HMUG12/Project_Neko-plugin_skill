# 41 · 反"AI 味"的 Hosted UI 设计

> 融合来源：
> - **pbakaus/impeccable**（确定性设计规则、反 AI slop、版式与对齐纪律）
> - **Nutlope/hallmark**（57 项 slop 测试、宏观结构、留白与层级）
>
> 适用对象：NEKO 插件的 **Hosted UI（TSX + `@neko/plugin-ui`）**。这类 UI 由 AI 生成概率极高，最容易落入"千篇一律的 AI 默认审美"。本文把两个反 slop 体系的规则**映射到 NEKO 组件约束**，让你交付的插件界面看起来是"人做的"。

---

## 0 · 先记住 NEKO 的硬约束（否则设计都是空谈）

Hosted UI 是 TSX 沙箱，**有禁止项**（详见 `03-ui-settings.md` / `15-rich-ui-components.md`）：

- 不能 `import` 任意 npm 包；只能用 `@neko/plugin-ui` 提供的组件 + 内联 `style`。
- 禁止 class 组件、React Context / Portals / Suspense。
- 没有 `Slider`（用 `Input` 的 `type="number"` / `type="range"` 代替）。
- 用内联 `style` 对象做样式，**不是** CSS 类 / Tailwind。
- 通过 `useNeko()` 拿 `settings` / `reportStatus` / `setSettings`；用 `api.call` 调后端 entry。

> 所以"反 AI 味"不是让你堆特效，而是在**受限组件集 + 内联样式**下做出干净、克制、有层级的设计。

---

## 1 · AI 默认审美的典型信号（slop tells）

hallmark/impeccable 反复点名、NEKO 插件里最常见的"AI 味"：

- **字体**：默认 `Inter`（沙箱里多半也是无衬线系统字体）——不要靠字体"显高级"，靠层级。
- **配色**：满屏紫色/蓝色→青色渐变背景；或"柔和渐变 + 模糊光斑"。
- **卡片**：嵌套卡片套卡片（card-in-card）、统一 `border-radius: 16px` + 浅灰描边 + 柔和阴影的"套娃"。
- **文字**：浅灰正文（`#9ca3af` 之类）压在彩色背景上，对比度不达标。
- **图标块**：一排圆角方块图标，每个带不同粉彩底色（"彩虹药丸"）。
- **英雄区**：大标题 + 一句废话副标题 + 一个悬浮发光按钮。
- **模板句式**：副标题写 "Your all-in-one solution to…"、按钮写 "Get started" / "Learn more"。
- **装饰滥用**：无意义的网格点、光晕、噪点纹理、"抽象几何"背景。
- **假数据感**：所有卡片用同一套占位文案、同一张渐变缩略图。

> **来源核实**：hallmark 的 `skills/hallmark/references/slop-test.md` 是一份 **58 道关卡**的反 slop 检查表；impeccable 的 `reference/craft-floor.md` 是"质量地板 + 绝对禁令"。下面把两者的真实类别映射到 NEKO Hosted UI 的受限组件集。

---

## 2 · 反 slop 的 10 条可执行规则（映射到 NEKO）

1. **单一强调色 + 中性底**。全界面只用一个品牌色（如 `#2563eb` 或你产品的主色），其余用黑/白/灰。渐变只用于**一处**关键 CTA，绝不铺满背景。
2. **层级靠字号/字重/留白，不靠颜色堆叠**。主标题 22–28px、加粗；次要信息 13–14px、常规；说明 12px、弱化但不低于 `#6b7280`（保证对比度 ≥ 4.5:1）。
3. **留白即设计**。容器 `padding` 16–24px，卡片间距 12–16px，不要贴边。拥挤是 AI 味的近亲。
4. **对齐一致**。同一列信息左对齐；数字/价格右对齐；表头与列对齐。impeccable 强调"对齐是专业的近义词"。
5. **少用边框，多用分隔**。能用 1px 浅灰分隔线（`border-bottom`）就不用全包围卡片。嵌套卡片能免则免。
6. **阴影克制**。只在浮层（`Modal`/`DropdownMenu`）用阴影，普通卡片用 1px 浅边框或纯背景差（`#f9fafb` vs `#fff`）。
7. **文案具体、不废话**。按钮写"保存配置""运行抓取"，不写"Get started"；副标题写本插件真实用途一句话。
8. **真实数据形态**。列表项用真实字段（名称、时间、状态徽章），状态用 `StatusBadge` 的语义色（成功/警告/错误），别用彩虹色块。
9. **一个焦点**。一屏只引导用户做一件事；次要操作降为次级按钮或文本链接。
10. **动效克制**。悬停只做轻微 `opacity`/`background` 变化，不用弹跳、不大幅位移。沙箱本就不鼓励重动画。

---

## 2.5 · impeccable 的 craft-floor 绝对禁令（映射到 NEKO）

impeccable 把"不可违反的地板"单列成 `craft-floor.md`，NEKO 插件 UI 里对应：

| impeccable 禁令 | NEKO 映射（用 `@neko/plugin-ui` 内联 style 时） |
|---|---|
| 不要用 emoji 当装饰 | 状态/图标用 `StatusBadge` 语义色，不在文案里塞 🎨✨ 装点 |
| 不要渐变背景 / 渐变文字 | 背景用纯色（`#fff` / `#f9fafb`）；渐变只允许在**一处**主 CTA |
| 不要无目的 box-shadow | 阴影只给浮层（`Modal`/`DropdownMenu`）；普通卡片用 1px 浅边框或背景差 |
| 不要统一 `border-radius: 16px` 套娃 | 卡片圆角统一取 8–12px，嵌套卡片能免则免 |
| 不要"彩虹药丸"色块 | 全界面 ≤1 个品牌色，状态用 `StatusBadge` 而非彩色方块 |
| 对比度必须达标 | 灰字不低于 `#6b7280`（对比度 ≥ 4.5:1），浅灰压彩底直接否 |
| 间距用统一刻度 | 容器 `padding` 16/24、卡片间距 12/16，不要随手写 13px、17px |

impeccable 的"反 slop 反射（reflexes）"：每写完一块 UI，下意识检查——**对齐到网格了吗？层级靠字号而非颜色吗？这一笔装饰去掉会不会更好？** 三问过了再交付。

---

## 2.6 · hallmark 的 58 道 slop 关卡（按 NEKO 场景归类）

hallmark 的 `slop-test.md` 用 58 个二进制关卡判定"是否 AI slop"。对 NEKO 插件 UI 最相关的几类：

- **配色类**：默认紫/蓝渐变、柔和光斑背景、彩虹强调色 → 见 §2 规则 1。
- **形状类**：圆角套娃、无目的阴影、全包围卡片 → 见 §2 规则 5、6。
- **排版类**：全用系统无衬线还自认"高级"、正文灰压彩底、字号无层级 → 见 §2 规则 2、§3。
- **文案类**：英雄区废话副标题、"Get started" / "Learn more"、 "all-in-one solution" → 见 §2 规则 7、§1。
- **结构类**：发明非标准布局、设置堆主页、假数据占位 → 见 §3、§4。
- **装饰类**：网格点、光晕、噪点、抽象几何背景 → 一律删（§1 信号）。

**用法**：交付前把 `slop-test.md` 当勾选表逐条过——任何一道"是 AI slop"就改。核心精神：**克制即专业**。

---

## 3 · 宏观结构（hallmark 的 macrostructure）

一个插件 UI 通常就这几块，按顺序排，别发明新结构：

```
[标题栏] 插件名 + 一句真实用途（12–14px 灰字）
[主操作区] 1 个主 CTA + 必要输入（Input/Select）
[结果/状态区] StatusBadge + 列表/详情（JsonView 仅用于调试）
[设置入口] 跳 settings 面板，不在主页堆设置项
```

- **不要英雄区**。插件 UI 是工具，不是落地页，不需要大标题+光晕。
- **设置与主页分离**。设置项放 Hosted UI 的 settings 面板（见 `03-ui-settings.md`），主页只放"用"。
- **结果区默认空态友好**。"还没有数据，点击上方按钮开始" 比空白强。

---

## 4 · NEKO 组件的正确用法（避免"组件炫技"）

- `StatusBadge`：用语义色表达状态，是替代"彩虹药丸"的正道。
- `Modal` / `ConfirmDialog`：危险操作（删除/清空）必经确认，别直接执行。
- `JsonView`：给开发者/调试用，**不要**当用户主界面；用户要看可读列表，不是原始 JSON。
- `Table`：数据多于 5 行就用表，别用 div 列表硬凑。
- `Form` / `ActionForm`：把"提交→调 `api.call`→`reportStatus`"固化成模式，减少临时拼装。

---

## 5 · 自检清单（交付前过一遍）

- [ ] 全界面品牌色 ≤ 1 个？渐变 ≤ 1 处？
- [ ] 没有嵌套卡片（card-in-card）？
- [ ] 正文对比度 ≥ 4.5:1（灰字不低于 `#6b7280`）？
- [ ] 文案是具体动作/真实用途，没有 "Get started / all-in-one" 之类废话？
- [ ] 对齐一致、留白充足、没有贴边？
- [ ] 状态用 `StatusBadge` 语义色，而非彩色方块？
- [ ] 没有英雄区、光晕、网格点等纯装饰？
- [ ] 设置项在 settings 面板，不在主页堆砌？

> 交叉阅读：`03-ui-settings.md`（设置面板与组件清单）、`15-rich-ui-components.md`（富组件用法）、`40-engineering-discipline.md`（克制即纪律，YAGNI 同样适用于 UI）。
