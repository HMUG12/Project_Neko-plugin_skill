/**
 * 网页助手设置面板 —— 反 AI 味写法（41-ui-design-quality.md）：
 *   · 单一主操作、无嵌套卡片、对比度达标、文案具体、无 emoji 装饰 / 光晕。
 *   · 用已验证组件（03-ui-settings.md），无其他组件。
 */
import {
  Page, Card, Section, Stack, Grid, Text,
  Input, StatCard, ActionButton, Field, Tip,
} from "@neko/plugin-ui"
import type { HostedAction, PluginSurfaceProps } from "@neko/plugin-ui"
import { useLocalState } from "@neko/plugin-ui"

type State = {
  config: { has_key: boolean }
  status: { ready: boolean }
}

export default function SettingsPanel(props: PluginSurfaceProps<State>) {
  const { state, actions } = props

  // 1. 缓存 actions —— 避免首次渲染按钮消失（03 关键模式 1）
  const [cachedActions, setCachedActions] = useLocalState(
    "ca",
    () => [] as HostedAction[]
  )
  if (actions.length > 0 && actions.length !== cachedActions.length) {
    setCachedActions(actions)
  }
  const effectiveActions = cachedActions.length > 0 ? cachedActions : actions

  // 2. 本地状态：每个配置项一个（key 唯一，03 关键模式 3）
  const [apiKey, setApiKey] = useLocalState("ak", () => "")
  const [apiUrl, setApiUrl] = useLocalState("au", () => "")
  const [city, setCity] = useLocalState("ct", () => "")
  const [limit, setLimit] = useLocalState("lm", () => "5")

  const refreshAction = effectiveActions.find(
    (a: HostedAction) => a.id === "refresh_status"
  )

  async function handleRefresh() {
    if (!refreshAction) return
    try {
      await refreshAction.call({})
    } catch (e) {
      /* 忽略 */
    }
  }

  // 3. 渲染
  return (
    <Page title="网页助手">
      <Grid>
        <StatCard title="状态" value={state.status?.ready ? "就绪" : "未就绪"} />
        <StatCard
          title="API Key"
          value={state.config?.has_key ? "已配置" : "未配置"}
        />
      </Grid>

      <Card title="抓取配置">
        <Stack>
          <Field label="Firecrawl API Key">
            <Input
              type="password"
              value={apiKey}
              onChange={(v: string) => setApiKey(v)}
              placeholder="粘贴你的 Key"
            />
          </Field>
          <Field label="API 地址（可选，自建或代理时填）">
            <Input
              value={apiUrl}
              onChange={(v: string) => setApiUrl(v)}
              placeholder="留空使用官方"
            />
          </Field>
          <Field label="默认城市">
            <Input
              value={city}
              onChange={(v: string) => setCity(v)}
              placeholder="如 北京"
            />
          </Field>
          <Field label={`搜索返回条数：${limit}`}>
            <Input
              type="number"
              value={Number(limit)}
              onChange={(v: number) => setLimit(String(v))}
              min={1}
              max={20}
            />
          </Field>
        </Stack>
        <Tip>
          Key 仅保存在插件配置中，不会写入代码或提交到仓库（见 43 安全加固）。
        </Tip>
      </Card>

      <Section>
        <Stack>
          {refreshAction ? (
            <ActionButton action={refreshAction} values={{}}>
              刷新状态
            </ActionButton>
          ) : (
            <ActionButton
              action={
                { id: "refresh_status", call: async () => {} } as HostedAction
              }
              values={{}}
            >
              刷新状态（加载中…）
            </ActionButton>
          )}
        </Stack>
      </Section>
    </Page>
  )
}
