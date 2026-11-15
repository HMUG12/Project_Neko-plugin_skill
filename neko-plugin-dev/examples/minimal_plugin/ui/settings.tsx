/**
 * 最小设置面板：绑定真实保存 action，无静默兜底、无死代码。
 * 组件与 props 以官方 hosted-ui-api.md / 03-ui-settings.md 为准。
 */
import {
  Page, Card, Section, Stack, Grid, Text,
  Input, StatCard, ActionButton, Field,
} from "@neko/plugin-ui"
import type { HostedAction, PluginSurfaceProps } from "@neko/plugin-ui"
import { useLocalState } from "@neko/plugin-ui"

type State = {
  config: { greeting: string }
  status: { ticks: number; frozen: boolean }
}

export default function SettingsPanel(props: PluginSurfaceProps<State>) {
  const { state, actions } = props

  // 缓存 actions，避免首次渲染按钮消失（03 关键模式 1）
  const [cachedActions, setCachedActions] = useLocalState(
    "mp_actions",
    () => [] as HostedAction[]
  )
  if (actions.length > 0 && actions.length !== cachedActions.length) {
    setCachedActions(actions)
  }
  const effectiveActions = cachedActions.length > 0 ? cachedActions : actions

  const [greeting, setGreeting] = useLocalState(
    "mp_greeting",
    () => state.config?.greeting ?? ""
  )
  const [error, setError] = useLocalState("mp_error", () => "")

  const saveAction = effectiveActions.find(
    (a: HostedAction) => a.id === "save_settings"
  )

  return (
    <Page title="最小插件设置">
      <Grid>
        <StatCard title="计数" value={String(state.status?.ticks ?? 0)} />
        <StatCard title="状态" value={state.status?.frozen ? "已冻结" : "运行中"} />
      </Grid>

      <Card title="基本设置">
        <Stack>
          <Field label="问候语">
            <Input
              value={greeting}
              onChange={(v: string) => setGreeting(v)}
              placeholder="输入一句问候"
            />
          </Field>
        </Stack>
      </Card>

      <Section>
        <Stack>
          {saveAction ? (
            <ActionButton
              action={saveAction}
              values={{ config: { greeting } }}
              onResult={(r: unknown) => {
                const ok = Boolean((r as { ok?: boolean } | null)?.ok)
                setError(ok ? "" : "保存失败，请检查插件日志后重试")
              }}
            >
              保存设置
            </ActionButton>
          ) : (
            <Text>保存动作尚未就绪，请刷新面板或重载插件</Text>
          )}
          {error ? <Text>{error}</Text> : null}
        </Stack>
      </Section>
    </Page>
  )
}
