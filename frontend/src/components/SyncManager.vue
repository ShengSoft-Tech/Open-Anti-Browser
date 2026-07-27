<template>
  <div class="sync-page">
    <el-alert
      v-if="syncGate.disabled || arrangeGate.disabled"
      class="platform-banner"
      type="warning"
      :closable="false"
      show-icon
      :title="t('syncer.platformBannerTitle')"
    >
      <p v-if="syncGate.disabled">{{ syncGate.reason || t('platformLimits.windowsOnlyFallback') }}</p>
      <p v-if="arrangeGate.disabled && arrangeGate.reason !== syncGate.reason">{{ arrangeGate.reason || t('platformLimits.windowsOnlyFallback') }}</p>
      <p class="platform-banner-hint">{{ t('syncer.platformBannerHint') }}</p>
    </el-alert>

    <section class="page-panel soft sync-hero">
      <div class="sync-hero-main">
        <div>
          <div class="sync-eyebrow">Synchronizer</div>
          <h2>同步器</h2>
          <p class="panel-desc">用于多窗口联动操作</p>
        </div>

        <div class="hero-action-row">
          <el-tooltip :disabled="!syncGate.disabled" :content="syncGate.reason || t('platformLimits.windowsOnlyFallback')">
            <el-button type="primary" :disabled="selectedRunningIds.length < 2 || syncGate.disabled" :loading="submitting" @click="startSync">
              <el-icon><VideoPlay /></el-icon>
              启动同步
            </el-button>
          </el-tooltip>
          <el-tooltip :disabled="!syncGate.disabled" :content="syncGate.reason || t('platformLimits.windowsOnlyFallback')">
            <el-button plain :disabled="!session.running || selectedRunningIds.length < 2 || syncGate.disabled" :loading="submitting" @click="restartSync">
              <el-icon><RefreshRight /></el-icon>
              重启同步
            </el-button>
          </el-tooltip>
          <el-tooltip :disabled="!syncGate.disabled" :content="syncGate.reason || t('platformLimits.windowsOnlyFallback')">
            <el-button plain :disabled="!session.running || syncGate.disabled" :loading="submitting" @click="stopSync">
              <el-icon><CloseBold /></el-icon>
              停止同步
            </el-button>
          </el-tooltip>
          <el-popover
            v-model:visible="settingsVisible"
            placement="bottom-end"
            width="430"
            trigger="click"
            popper-class="sync-settings-popper"
          >
            <template #reference>
              <el-button circle plain>
                <el-icon><Setting /></el-icon>
              </el-button>
            </template>
            <div class="settings-popover">
              <div class="popover-head">
                <div>
                  <div class="popover-title">同步设置</div>
                  <div class="popover-subtitle">选择需要同步的操作范围</div>
                </div>
                <el-button text @click="settingsVisible = false">关闭</el-button>
              </div>

              <div class="settings-section">
                <div class="section-title">同步内容</div>
                <div class="toggle-grid">
                  <label class="toggle-item"><span>页面跳转</span><el-switch v-model="settings.options.sync_navigation" /></label>
                  <label class="toggle-item"><span>点击动作</span><el-switch v-model="settings.options.sync_click" /></label>
                  <label class="toggle-item"><span>文本输入</span><el-switch v-model="settings.options.sync_input" /></label>
                  <label class="toggle-item"><span>滚动动作</span><el-switch v-model="settings.options.sync_scroll" /></label>
                  <label class="toggle-item"><span>键盘动作</span><el-switch v-model="settings.options.sync_keyboard" /></label>
                  <label class="toggle-item"><span>鼠标轨迹</span><el-switch v-model="settings.options.sync_mouse_move" /></label>
                  <label class="toggle-item"><span>标签页与地址栏</span><el-switch v-model="settings.options.sync_browser_ui" /></label>
                </div>
              </div>

              <div class="settings-section">
                <div class="section-title">启动行为</div>
                <label class="toggle-item single">
                  <span>启动时同步主控网址</span>
                  <el-switch v-model="settings.options.sync_current_url_on_start" />
                </label>
              </div>

              <div class="settings-section">
                <div class="section-title">操作延迟</div>
                <div class="delay-card">
                  <label class="toggle-item single inline">
                    <span>点击延迟</span>
                    <el-switch v-model="settings.delayClickEnabled" />
                  </label>
                  <div class="delay-line">
                    <el-input-number v-model="settings.delayClickMin" :min="0" :max="5000" controls-position="right" />
                    <span>至</span>
                    <el-input-number v-model="settings.delayClickMax" :min="0" :max="5000" controls-position="right" />
                    <span>ms</span>
                  </div>
                </div>
                <div class="delay-card">
                  <label class="toggle-item single inline">
                    <span>输入延迟</span>
                    <el-switch v-model="settings.delayInputEnabled" />
                  </label>
                  <div class="delay-line">
                    <el-input-number v-model="settings.delayInputMin" :min="0" :max="5000" controls-position="right" />
                    <span>至</span>
                    <el-input-number v-model="settings.delayInputMax" :min="0" :max="5000" controls-position="right" />
                    <span>ms</span>
                  </div>
                </div>
              </div>

              <div class="settings-section">
                <div class="section-title">快捷键</div>
                <div class="hotkey-grid">
                  <div v-for="item in hotkeyItems" :key="item.key" class="hotkey-item">
                    <span>{{ item.label }}</span>
                    <el-input v-model="settings.hotkeys[item.key]" clearable />
                  </div>
                </div>
              </div>

              <div class="popover-actions">
                <el-button @click="settingsVisible = false">取消</el-button>
                <el-button type="primary" @click="saveSettings">保存</el-button>
              </div>
            </div>
          </el-popover>
        </div>
      </div>

      <div class="sync-metrics">
        <div class="metric-card">
          <span>已选窗口</span>
          <strong>{{ selectedRunningIds.length }}</strong>
        </div>
        <div class="metric-card">
          <span>运行窗口</span>
          <strong>{{ runningProfiles.length }}</strong>
        </div>
        <div class="metric-card">
          <span>当前主控</span>
          <strong>{{ masterName }}</strong>
        </div>
        <div class="metric-card accent">
          <span>状态</span>
          <strong>{{ syncStateLabel }}</strong>
        </div>
      </div>
    </section>

    <div class="sync-layout">
      <section class="page-panel sync-list-panel">
        <div class="panel-title-row sync-list-head">
          <div>
            <h3>运行中的浏览器</h3>
            <p class="panel-desc">选择两个及以上窗口后即可开始</p>
          </div>
          <div class="list-head-actions">
            <el-select v-model="groupFilter" class="group-filter" clearable placeholder="全部分组">
              <el-option label="全部分组" value="" />
              <el-option v-for="group in groups" :key="group || '_'" :label="group || '未分组'" :value="group" />
            </el-select>
            <el-button plain :disabled="!selectedRunningIds.length || arrangeGate.disabled" @click="showWindows()">
              <el-icon><FullScreen /></el-icon>
              显示窗口
            </el-button>
            <el-button plain :disabled="!selectedRunningIds.length || arrangeGate.disabled" @click="uniformSize">
              统一大小
            </el-button>
          </div>
        </div>

        <div class="sync-selected-bar">
          <span class="pill">已选 {{ selectedRunningIds.length }}</span>
          <span class="pill soft">主控 {{ masterName }}</span>
          <span class="pill soft">跟随 {{ followerCountPreview }}</span>
        </div>

        <div class="sync-table-wrap">
          <el-table v-if="filteredProfiles.length" class="sync-table" :data="filteredProfiles" row-key="id" stripe height="100%">
            <el-table-column width="52">
              <template #header>
                <el-checkbox
                  :model-value="allVisibleSelected"
                  :indeterminate="someVisibleSelected"
                  @change="handleSelectAll"
                />
              </template>
              <template #default="{ row }">
                <el-checkbox
                  :model-value="isSelected(row.id)"
                  @change="value => handleSelect(row.id, value)"
                  @click.stop
                />
              </template>
            </el-table-column>

            <el-table-column label="窗口" min-width="280">
              <template #default="{ row }">
                <div class="profile-card-row">
                  <div class="profile-avatar engine">
                    <img class="profile-avatar-icon" :src="row.engine === 'chrome' ? chromeIcon : firefoxIcon" :alt="row.engine" />
                  </div>
                  <div class="profile-info">
                    <div class="profile-name-line">
                      <span class="profile-name">{{ row.name || row.id.slice(0, 8) }}</span>
                      <el-tag v-if="effectiveMasterId === row.id" size="small" type="primary" effect="plain">主控</el-tag>
                    </div>
                    <div class="profile-meta">{{ row.group || '未分组' }} · 调试端口 {{ row.runtime?.remote_debugging_port || '—' }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="内核" width="100">
              <template #default="{ row }">
                <el-tag :type="row.engine === 'chrome' ? 'primary' : 'warning'" effect="plain" size="small">
                  {{ row.engine === 'chrome' ? 'Chrome' : 'Firefox' }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="连接信息" min-width="220">
              <template #default="{ row }">
                <div class="status-stack">
                  <span class="status-ip">{{ row.runtime?.resolved_ip || '未解析' }}</span>
                  <span class="status-url">{{ row.runtime?.startup_url || row.runtime?.last_url || '当前标签页待获取' }}</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="150" align="center" fixed="right">
              <template #default="{ row }">
                <div class="row-actions">
                  <el-tooltip content="设为主控">
                    <el-button circle text class="row-action" @click="setMaster(row.id)">
                      <el-icon><Monitor /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="显示窗口">
                    <el-button circle text class="row-action" :disabled="arrangeGate.disabled" @click="showWindows([row.id])">
                      <el-icon><FullScreen /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <div v-else class="empty-state sync-empty">
            <el-icon><Monitor /></el-icon>
            <h3>暂无可同步窗口</h3>
            <p>请先启动两个或以上浏览器窗口</p>
          </div>
        </div>
      </section>

      <aside class="page-panel soft sync-console">
        <div class="console-head">
          <div>
            <h3>操作台</h3>
            <p class="panel-desc">窗口 文本和标签页操作</p>
          </div>
          <el-switch v-model="compactPanel" active-text="精简" inactive-text="完整" />
        </div>

        <div class="console-status-list">
          <div class="status-card-line" :class="{ active: session.running }">
            <span class="status-dot" :class="session.running ? 'running' : ''"></span>
            <div class="status-copy">
              <span>同步状态：</span>
              <strong>{{ syncStateLabel }}</strong>
            </div>
          </div>
          <div class="status-card-line">
            <div class="status-copy">
              <span>已连接：</span>
              <strong>{{ session.connected_followers || 0 }} / {{ session.follower_count || 0 }}</strong>
            </div>
          </div>
          <div class="status-card-line wide">
            <div class="status-copy wide">
              <span>最近动作：</span>
              <strong>{{ lastEventText }}</strong>
            </div>
          </div>
        </div>

        <div class="console-primary-actions">
          <el-button type="primary" :disabled="selectedRunningIds.length < 2 || syncGate.disabled" :loading="submitting" @click="startSync">启动同步</el-button>
          <el-button plain :disabled="!session.running || selectedRunningIds.length < 2 || syncGate.disabled" :loading="submitting" @click="restartSync">重启同步</el-button>
          <el-button plain :disabled="!session.running || syncGate.disabled" :loading="submitting" @click="stopSync">停止同步</el-button>
        </div>

        <template v-if="compactPanel">
          <div class="compact-panel">
            <div class="quick-grid two">
              <el-button plain :disabled="!selectedRunningIds.length || arrangeGate.disabled" @click="showWindows()">显示窗口</el-button>
              <el-button plain :disabled="!selectedRunningIds.length || arrangeGate.disabled" @click="uniformSize">统一大小</el-button>
              <el-button plain :disabled="!selectedRunningIds.length || arrangeGate.disabled" @click="arrangeWindows">一键排列</el-button>
              <el-button plain :disabled="!selectedRunningIds.length || syncGate.disabled" @click="runTabAction('close_blank')">关闭空白页</el-button>
            </div>
          </div>
        </template>

        <template v-else>
          <el-segmented
            v-model="activePanel"
            class="console-tabs"
            :options="[
              { label: '窗口管理', value: 'windows' },
              { label: '文本管理', value: 'text' },
              { label: '标签页管理', value: 'tabs' },
            ]"
          />

          <div v-if="activePanel === 'windows'" class="panel-stack">
            <section class="console-card">
              <div class="card-title">快速操作</div>
              <div class="quick-grid two">
                <el-button plain :disabled="!selectedRunningIds.length || arrangeGate.disabled" @click="showWindows()">显示窗口</el-button>
                <el-button plain :disabled="!selectedRunningIds.length || arrangeGate.disabled" @click="uniformSize">统一大小</el-button>
              </div>
            </section>

            <section class="console-card">
              <div class="card-title">窗口排列</div>
              <el-form label-position="top" class="panel-form">
                <el-form-item label="显示器">
                  <el-select v-model="windowForm.monitorId" placeholder="请选择显示器">
                    <el-option v-for="monitor in monitors" :key="monitor.id" :label="monitorText(monitor)" :value="monitor.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="排列方式">
                  <el-radio-group v-model="windowForm.arrangeMode" class="arrange-radio">
                    <el-radio-button value="grid">宫格</el-radio-button>
                    <el-radio-button value="overlap">重叠</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-form>
              <el-tooltip :disabled="!arrangeGate.disabled" :content="arrangeGate.reason || t('platformLimits.windowsOnlyFallback')">
                <el-button class="wide-btn" type="primary" plain :disabled="!selectedRunningIds.length || arrangeGate.disabled" @click="arrangeWindows">一键排列</el-button>
              </el-tooltip>
            </section>
          </div>

          <div v-else-if="activePanel === 'text'" class="panel-stack">
            <section class="console-card">
              <div class="card-title">常用输入</div>
              <div class="quick-grid two">
                <el-button plain :disabled="!selectedRunningIds.length || syncGate.disabled" @click="runTextAction({ action: 'clear' })">清空内容</el-button>
                <el-button plain :disabled="!selectedRunningIds.length || !sameText.trim() || syncGate.disabled" @click="runTextAction({ action: 'same', text: sameText })">相同内容</el-button>
              </div>
            </section>

            <section class="console-card">
              <div class="card-title">随机数字</div>
              <div class="range-row">
                <el-input-number v-model="randomRange.start" :precision="3" :step="0.001" controls-position="right" />
                <span class="range-sep">至</span>
                <el-input-number v-model="randomRange.end" :precision="3" :step="0.001" controls-position="right" />
              </div>
              <el-button class="wide-btn" plain :disabled="!selectedRunningIds.length || syncGate.disabled" @click="runTextAction({ action: 'random', range_start: randomRange.start, range_end: randomRange.end, precision: 3 })">输入随机数字</el-button>
            </section>

            <section class="console-card">
              <div class="card-title">相同文本</div>
              <el-input v-model="sameText" type="textarea" :rows="3" placeholder="请输入要同步输入的内容" />
              <div class="card-actions right">
                <el-button type="primary" plain :disabled="!selectedRunningIds.length || !sameText.trim() || syncGate.disabled" @click="runTextAction({ action: 'same', text: sameText })">输入</el-button>
              </div>
            </section>

            <section class="console-card">
              <div class="card-title">指定文本组</div>
              <el-radio-group v-model="designatedMode" class="mode-radio">
                <el-radio-button value="sequential">顺序</el-radio-button>
                <el-radio-button value="random">随机</el-radio-button>
                <el-radio-button value="fixed">固定</el-radio-button>
              </el-radio-group>
              <el-input v-if="designatedMode === 'fixed'" v-model="fixedText" placeholder="请输入固定内容" />
              <div class="text-groups">
                <div v-for="group in designatedGroups" :key="group.id" class="text-group-card">
                  <div class="text-group-head">
                    <span>{{ group.title }}</span>
                    <el-button text :disabled="designatedGroups.length === 1" @click="removeGroup(group.id)">删除</el-button>
                  </div>
                  <el-input v-model="group.content" type="textarea" :rows="4" placeholder="每行一条内容" />
                </div>
              </div>
              <el-button class="wide-btn dashed" plain @click="addGroup">添加文本组</el-button>
              <div class="card-actions right">
                <el-button type="primary" plain :disabled="!selectedRunningIds.length || syncGate.disabled" @click="runTextAction({ action: 'designated', groups: designatedGroups, designated_mode: designatedMode, fixed_text: fixedText })">执行输入</el-button>
              </div>
            </section>
          </div>

          <div v-else class="panel-stack">
            <section class="console-card">
              <div class="card-title">标签页整理</div>
              <div class="quick-grid two">
                <el-button plain :disabled="!selectedRunningIds.length || syncGate.disabled" @click="runTabAction('unify_tabs')">统一标签页</el-button>
                <el-button plain :disabled="!selectedRunningIds.length || syncGate.disabled" @click="runTabAction('close_others')">关闭其他</el-button>
                <el-button plain :disabled="!selectedRunningIds.length || syncGate.disabled" @click="runTabAction('close_current')">关闭当前</el-button>
                <el-button plain :disabled="!selectedRunningIds.length || syncGate.disabled" @click="runTabAction('close_blank')">关闭空白页</el-button>
              </div>
            </section>

            <section class="console-card">
              <div class="card-title">批量打开网址</div>
              <el-input v-model="urlInput" type="textarea" :rows="4" placeholder="每行一个网址" />
              <label class="toggle-item single block-gap">
                <span>首个网址在当前标签页打开</span>
                <el-switch v-model="firstInCurrentTab" />
              </label>
              <el-button class="wide-btn" plain :disabled="!selectedRunningIds.length || !parsedUrls.length || syncGate.disabled" @click="openUrls">批量打开</el-button>
            </section>
          </div>
        </template>

        <el-alert v-if="session.last_error" class="console-error" type="error" show-icon :closable="false">{{ session.last_error }}</el-alert>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onActivated, onDeactivated, onUnmounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { CloseBold, FullScreen, Monitor, RefreshRight, Setting, VideoPlay } from '@element-plus/icons-vue'
import { useProfileStore } from '../stores/profile.js'
import { getWindowFeatureGate } from '../lib/capabilitiesGating.js'
import chromeIcon from '../assets/chrome.svg'
import firefoxIcon from '../assets/firefox.png'

const { t } = useI18n()
const store = useProfileStore()
const groupFilter = ref('')
const selectedIds = ref([])
const masterId = ref('')
const activePanel = ref('windows')
const settingsVisible = ref(false)
const compactPanel = ref(false)
const submitting = ref(false)
const urlInput = ref('')
const sameText = ref('')
const firstInCurrentTab = ref(true)
const designatedMode = ref('sequential')
const fixedText = ref('')
const designatedGroups = ref([{ id: crypto.randomUUID(), title: '文本组1', content: '' }])
const randomRange = reactive({ start: 0.001, end: 0.009 })
const windowForm = reactive({ monitorId: '', arrangeMode: 'grid' })

let pollTimer = null
let pollRound = 0
let hotkeysBound = false
const componentActive = ref(false)

const SETTINGS_KEY = 'oab.sync.settings.v6'
const UI_KEY = 'oab.sync.ui.v6'

const settings = reactive(loadSettings())
const hotkeyItems = [
  { key: 'start_sync', label: '启动同步' },
  { key: 'stop_sync', label: '停止同步' },
  { key: 'restart_sync', label: '重启同步' },
  { key: 'toggle_panel', label: '切换操作台' },
  { key: 'arrange_windows', label: '一键排列' },
  { key: 'random_input', label: '随机数字输入' },
  { key: 'same_text', label: '相同文本输入' },
  { key: 'unify_tabs', label: '统一标签页' },
  { key: 'close_others', label: '关闭其他标签页' },
  { key: 'close_current', label: '关闭当前标签页' },
  { key: 'close_blank', label: '关闭空白标签页' },
]

const session = computed(() => store.synchronizer || { running: false, follower_count: 0, connected_followers: 0, last_event: null, last_error: '' })
const runningProfiles = computed(() => (store.profiles || []).filter(item => item.status === 'running' && item.runtime?.remote_debugging_port))
const groups = computed(() => Array.from(new Set(runningProfiles.value.map(item => item.group || '').values())).filter(Boolean).sort((a, b) => a.localeCompare(b)))
const filteredProfiles = computed(() => runningProfiles.value.filter(item => !groupFilter.value || (item.group || '') === groupFilter.value))
const visibleIds = computed(() => filteredProfiles.value.map(item => item.id))
const selectedRunningIds = computed(() => selectedIds.value.filter(id => runningProfiles.value.some(item => item.id === id)))
const allVisibleSelected = computed(() => visibleIds.value.length > 0 && visibleIds.value.every(id => selectedIds.value.includes(id)))
const someVisibleSelected = computed(() => {
  if (!visibleIds.value.length) return false
  const count = visibleIds.value.filter(id => selectedIds.value.includes(id)).length
  return count > 0 && count < visibleIds.value.length
})
const effectiveMasterId = computed(() => {
  if (masterId.value && selectedRunningIds.value.includes(masterId.value)) return masterId.value
  if (session.value.master_profile_id && selectedRunningIds.value.includes(session.value.master_profile_id)) return session.value.master_profile_id
  return selectedRunningIds.value[0] || masterId.value || session.value.master_profile_id || ''
})
const monitors = computed(() => store.syncMonitors || [])
const parsedUrls = computed(() => urlInput.value.split(/\r?\n/).map(item => item.trim()).filter(Boolean))
const masterName = computed(() => runningProfiles.value.find(item => item.id === effectiveMasterId.value)?.name || '—')
const followerCountPreview = computed(() => Math.max(0, selectedRunningIds.value.length - (effectiveMasterId.value ? 1 : 0)))
const syncStateLabel = computed(() => session.value.running ? '同步中' : '未启动')
const lastEventText = computed(() => {
  const event = session.value.last_event
  if (!event?.type) return '暂无'
  const labels = {
    navigate: '页面跳转',
    manual_navigate: '打开网址',
    sync_current_url: '同步网址',
    browser_close_current: '关闭标签页',
    click: '点击',
    input: '输入',
    change: '表单变化',
    wheel: '滚动',
    scroll: '滚动',
    keydown: '键盘',
    mouse_move: '鼠标轨迹',
  }
  const label = labels[event.type] || event.type
  return event.summary ? `${label} · ${event.summary}` : label
})
// D-00 单一事实源:同步类与排列类操作各读各的能力字段,互不回退。
const syncGate = computed(() => getWindowFeatureGate(store.capabilities, 'sync'))
const arrangeGate = computed(() => getWindowFeatureGate(store.capabilities, 'arrange'))

watch(() => session.value.master_profile_id, value => {
  if (value) masterId.value = value
})
watch([compactPanel, activePanel, () => windowForm.monitorId, () => windowForm.arrangeMode, firstInCurrentTab, groupFilter], saveUiState)
watch(() => session.value.running, () => {
  if (componentActive.value) {
    startPolling()
  }
})
watch(() => runningProfiles.value.map(item => item.id).join('|'), pruneSelection)

onActivated(async () => {
  componentActive.value = true
  loadUiState()
  bindHotkeys()
  pruneSelection()
  try {
    if (!store.synchronizer || typeof store.synchronizer.running === 'undefined') {
      await store.refreshSynchronizer()
    }
    if (!monitors.value.length) {
      await store.refreshSyncMonitors()
    }
    if (!store.profiles?.length) {
      await store.refreshProfiles()
    }
  } catch {
    // ignore activation refresh errors
  }
  pruneSelection()
  startPolling()
})

onDeactivated(() => {
  componentActive.value = false
  stopPolling()
  unbindHotkeys()
})

onUnmounted(() => {
  stopPolling()
  unbindHotkeys()
})

function loadSettings() {
  const defaults = {
    options: {
      sync_navigation: true,
      sync_click: true,
      sync_input: true,
      sync_scroll: true,
      sync_keyboard: true,
      sync_mouse_move: false,
      sync_current_url_on_start: true,
      sync_browser_ui: true,
    },
    delayClickEnabled: false,
    delayClickMin: 100,
    delayClickMax: 300,
    delayInputEnabled: false,
    delayInputMin: 300,
    delayInputMax: 300,
    hotkeys: {
      start_sync: 'Ctrl+Alt+S',
      stop_sync: 'Ctrl+Alt+D',
      restart_sync: 'Ctrl+Alt+R',
      toggle_panel: 'Ctrl+Alt+E',
      arrange_windows: 'Ctrl+Alt+Z',
      random_input: 'Ctrl+Alt+F',
      same_text: 'Ctrl+Alt+G',
      unify_tabs: 'Ctrl+Alt+X',
      close_others: 'Ctrl+Alt+B',
      close_current: 'Ctrl+Alt+H',
      close_blank: 'Ctrl+Alt+N',
    },
  }
  try {
    const raw = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')
    return {
      ...defaults,
      ...raw,
      options: { ...defaults.options, ...(raw.options || {}) },
      hotkeys: { ...defaults.hotkeys, ...(raw.hotkeys || {}) },
    }
  } catch {
    return defaults
  }
}

function loadUiState() {
  try {
    const raw = JSON.parse(localStorage.getItem(UI_KEY) || '{}')
    compactPanel.value = !!raw.compactPanel
    activePanel.value = raw.activePanel || 'windows'
    windowForm.monitorId = raw.monitorId || ''
    windowForm.arrangeMode = raw.arrangeMode || 'grid'
    firstInCurrentTab.value = raw.firstInCurrentTab ?? true
    groupFilter.value = raw.groupFilter || ''
  } catch {
    // ignore
  }
}

function saveUiState() {
  localStorage.setItem(UI_KEY, JSON.stringify({
    compactPanel: compactPanel.value,
    activePanel: activePanel.value,
    monitorId: windowForm.monitorId,
    arrangeMode: windowForm.arrangeMode,
    firstInCurrentTab: firstInCurrentTab.value,
    groupFilter: groupFilter.value,
  }))
}

function saveSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
  settingsVisible.value = false
  ElMessage.success('同步设置已保存')
}

async function refreshAll(forceProfiles = false) {
  const tasks = [store.refreshSynchronizer()]
  const hasRuntimeActivity = session.value.running || runningProfiles.value.length > 0 || selectedRunningIds.value.length > 0
  const shouldRefreshProfiles = forceProfiles || pollRound % (hasRuntimeActivity ? 5 : 12) === 0
  const shouldRefreshMonitors = forceProfiles || !monitors.value.length
  if (shouldRefreshProfiles) tasks.push(store.refreshProfiles())
  if (shouldRefreshMonitors) tasks.push(store.refreshSyncMonitors())
  await Promise.all(tasks)
  pruneSelection()
}

function startPolling() {
  stopPolling()
  pollRound = 0
  const interval = session.value.running
    ? 2200
    : (runningProfiles.value.length ? 4200 : 9000)
  pollTimer = window.setInterval(async () => {
    if (!componentActive.value || document.hidden) return
    pollRound += 1
    try {
      await refreshAll(false)
    } catch {
      // ignore polling errors
    }
  }, interval)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function bindHotkeys() {
  if (hotkeysBound) return
  window.addEventListener('keydown', onHotkey, true)
  hotkeysBound = true
}

function unbindHotkeys() {
  if (!hotkeysBound) return
  window.removeEventListener('keydown', onHotkey, true)
  hotkeysBound = false
}

function pruneSelection() {
  const available = new Set(runningProfiles.value.map(item => item.id))
  const nextSelected = selectedIds.value.filter(id => available.has(id))
  if (nextSelected.length !== selectedIds.value.length) selectedIds.value = nextSelected
  if (masterId.value && !nextSelected.includes(masterId.value)) {
    masterId.value = nextSelected[0] || ''
  }
}

function isSelected(profileId) {
  return selectedIds.value.includes(profileId)
}

function handleSelect(profileId, checked) {
  const next = new Set(selectedIds.value)
  if (checked) next.add(profileId)
  else next.delete(profileId)
  selectedIds.value = Array.from(next).filter(id => runningProfiles.value.some(item => item.id === id))
  if (checked && !masterId.value) masterId.value = profileId
  if (masterId.value && !selectedIds.value.includes(masterId.value)) masterId.value = selectedIds.value[0] || ''
}

function handleSelectAll(checked) {
  const next = new Set(selectedIds.value)
  if (checked) visibleIds.value.forEach(id => next.add(id))
  else visibleIds.value.forEach(id => next.delete(id))
  selectedIds.value = Array.from(next).filter(id => runningProfiles.value.some(item => item.id === id))
  if (!masterId.value && selectedIds.value.length) masterId.value = selectedIds.value[0]
  if (masterId.value && !selectedIds.value.includes(masterId.value)) masterId.value = selectedIds.value[0] || ''
}

function setMaster(id) {
  masterId.value = id
  if (!selectedIds.value.includes(id)) {
    selectedIds.value = [...selectedIds.value, id]
  }
}

function syncPayload() {
  if (selectedRunningIds.value.length < 2) throw new Error('请至少选择 2 个已启动窗口')
  const master = effectiveMasterId.value || selectedRunningIds.value[0]
  const followers = selectedRunningIds.value.filter(id => id !== master)
  if (!followers.length) throw new Error('请至少选择 2 个已启动窗口')
  return {
    master_profile_id: master,
    follower_profile_ids: followers,
    options: {
      ...settings.options,
      delay_click_enabled: settings.delayClickEnabled,
      delay_click_min_ms: settings.delayClickMin,
      delay_click_max_ms: settings.delayClickMax,
      delay_input_enabled: settings.delayInputEnabled,
      delay_input_min_ms: settings.delayInputMin,
      delay_input_max_ms: settings.delayInputMax,
    },
  }
}

async function startSync() {
  submitting.value = true
  try {
    await store.startSynchronizer(syncPayload())
    startPolling()
    ElMessage.success('同步已启动')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    submitting.value = false
  }
}

async function stopSync() {
  submitting.value = true
  try {
    await store.stopSynchronizer()
    startPolling()
    ElMessage.success('同步已停止')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    submitting.value = false
  }
}

async function restartSync() {
  submitting.value = true
  try {
    if (session.value.running) await store.stopSynchronizer()
    await store.startSynchronizer(syncPayload())
    startPolling()
    ElMessage.success('同步已重启')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    submitting.value = false
  }
}

async function showWindows(ids = selectedRunningIds.value) {
  if (!ids.length) return ElMessage.warning('请先选择窗口')
  try {
    await store.showSyncWindows(ids)
    ElMessage.success('操作已执行')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function uniformSize() {
  if (!selectedRunningIds.value.length) return ElMessage.warning('请先选择窗口')
  try {
    await store.uniformSyncWindows(selectedRunningIds.value)
    ElMessage.success('操作已执行')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function arrangeWindows() {
  if (!selectedRunningIds.value.length) return ElMessage.warning('请先选择窗口')
  try {
    await store.arrangeSyncWindows({
      profile_ids: selectedRunningIds.value,
      monitor_id: windowForm.monitorId,
      arrange_mode: windowForm.arrangeMode,
    })
    ElMessage.success('操作已执行')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function runTextAction(payload) {
  if (!selectedRunningIds.value.length) return ElMessage.warning('请先选择窗口')
  try {
    await store.runSyncTextAction({ profile_ids: selectedRunningIds.value, ...payload })
    ElMessage.success('操作已执行')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function runTabAction(action) {
  if (!selectedRunningIds.value.length) return ElMessage.warning('请先选择窗口')
  try {
    await store.runSyncTabAction({
      profile_ids: selectedRunningIds.value,
      action,
      master_profile_id: effectiveMasterId.value,
    })
    ElMessage.success('操作已执行')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function openUrls() {
  if (!selectedRunningIds.value.length) return ElMessage.warning('请先选择窗口')
  try {
    await store.runSyncTabAction({
      profile_ids: selectedRunningIds.value,
      action: 'open_urls',
      urls: parsedUrls.value,
      first_in_current: firstInCurrentTab.value,
    })
    ElMessage.success('操作已执行')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function addGroup() {
  designatedGroups.value.push({
    id: crypto.randomUUID(),
    title: `文本组${designatedGroups.value.length + 1}`,
    content: '',
  })
}

function removeGroup(id) {
  if (designatedGroups.value.length === 1) return
  designatedGroups.value = designatedGroups.value.filter(item => item.id !== id)
}

function monitorText(monitor) {
  const work = monitor?.work_area || {}
  return `${monitor.name}${monitor.primary ? ' · 主屏' : ''}${work.width ? ` ${work.width}×${work.height}` : ''}`
}

function normalizeShortcut(value) {
  return String(value || '').toLowerCase().replace(/\s+/g, '').replace('control', 'ctrl')
}

function matchShortcut(event, shortcut) {
  const normalized = normalizeShortcut(shortcut)
  if (!normalized) return false
  const parts = normalized.split('+').filter(Boolean)
  const last = parts[parts.length - 1]
  if (!!event.ctrlKey !== parts.includes('ctrl')) return false
  if (!!event.altKey !== parts.includes('alt')) return false
  if (!!event.shiftKey !== parts.includes('shift')) return false
  if (!!event.metaKey !== (parts.includes('meta') || parts.includes('cmd') || parts.includes('win'))) return false
  return String(event.key || '').toLowerCase() === last
}

function onHotkey(event) {
  if (!componentActive.value) return
  const target = event.target
  const tagName = String(target?.tagName || '').toLowerCase()
  const isTypingTarget = !!target?.isContentEditable || ['input', 'textarea', 'select'].includes(tagName)
  if (isTypingTarget) return
  for (const item of hotkeyItems) {
    if (!matchShortcut(event, settings.hotkeys[item.key])) continue
    event.preventDefault()
    if (item.key === 'start_sync') return startSync()
    if (item.key === 'stop_sync') return stopSync()
    if (item.key === 'restart_sync') return restartSync()
    if (item.key === 'toggle_panel') {
      compactPanel.value = !compactPanel.value
      return
    }
    if (item.key === 'arrange_windows') return arrangeWindows()
    if (item.key === 'random_input') return runTextAction({ action: 'random', range_start: randomRange.start, range_end: randomRange.end, precision: 3 })
    if (item.key === 'same_text') return runTextAction({ action: 'same', text: sameText.value })
    if (item.key === 'unify_tabs') return runTabAction('unify_tabs')
    if (item.key === 'close_others') return runTabAction('close_others')
    if (item.key === 'close_current') return runTabAction('close_current')
    if (item.key === 'close_blank') return runTabAction('close_blank')
  }
}
</script>

<style scoped>
.sync-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sync-page :deep(.page-panel),
.sync-page :deep(.page-panel.soft) {
  background: var(--oab-panel-solid-bg) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  box-shadow: none !important;
  transition: none !important;
}

.sync-page :deep(.el-button),
.sync-page :deep(.el-input__wrapper),
.sync-page :deep(.el-select__wrapper),
.sync-page :deep(.el-textarea__inner),
.sync-page :deep(.el-input-number__decrease),
.sync-page :deep(.el-input-number__increase),
.sync-page :deep(.el-segmented),
.sync-page :deep(.el-radio-button__inner),
.sync-page :deep(.el-table),
.sync-page :deep(.el-table__inner-wrapper),
.sync-page :deep(.el-table .el-table__row),
.sync-page :deep(.el-tag) {
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  box-shadow: none !important;
  transition: none !important;
}

.sync-page :deep(.el-button:hover),
.sync-page :deep(.el-button:active),
.sync-page :deep(.el-input-group__append:active),
.sync-page :deep(.el-radio-button__inner:hover) {
  transform: none !important;
  box-shadow: none !important;
}

.sync-hero {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sync-hero-main,
.sync-list-head,
.console-head,
.popover-head,
.text-group-head,
.card-actions,
.toggle-item,
.status-card-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.sync-eyebrow {
  color: var(--oab-accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.sync-hero h2,
.console-head h3 {
  margin: 0;
  color: var(--oab-text);
  letter-spacing: -0.35px;
}

.sync-hero h2 {
  font-size: 28px;
}

.console-head h3 {
  font-size: 18px;
}

.hero-action-row,
.list-head-actions,
.console-primary-actions,
.sync-selected-bar,
.row-actions,
.popover-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.hero-action-row {
  justify-content: flex-end;
}

.sync-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  min-height: 78px;
  padding: 14px 16px;
  border-radius: var(--oab-radius-lg);
  border: 1px solid var(--oab-border);
  background: var(--oab-card-bg);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.metric-card span,
.status-card-line span,
.popover-subtitle {
  color: var(--oab-muted);
  font-size: 12px;
  line-height: 1.5;
}

.metric-card strong,
.status-card-line strong {
  color: var(--oab-text);
  font-size: 13px;
  font-weight: 650;
  line-height: 1.4;
  word-break: break-word;
}

.metric-card strong {
  font-size: 17px;
  font-weight: 700;
}

.metric-card.accent {
  border-color: rgba(0, 122, 255, 0.18);
  background: var(--oab-accent-soft);
}

.sync-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 410px;
  gap: 16px;
  align-items: start;
}

.sync-list-panel,
.sync-console {
  min-height: 680px;
}

.sync-console {
  position: sticky;
  top: 12px;
}

.group-filter {
  width: 170px;
}

.sync-selected-bar {
  margin: -4px 0 14px;
}

.pill {
  min-height: 30px;
  padding: 6px 11px;
  border-radius: 999px;
  background: var(--oab-accent-soft);
  color: var(--oab-accent);
  font-size: 12px;
  font-weight: 600;
}

.pill.soft {
  background: var(--oab-card-bg);
  color: var(--oab-text-secondary);
  border: 1px solid var(--oab-border);
}

.sync-table-wrap {
  height: calc(100vh - 365px);
  min-height: 520px;
  border-radius: var(--oab-radius-lg);
  border: 1px solid var(--oab-border);
  background: var(--oab-card-bg);
  overflow: hidden;
}

.sync-table {
  width: 100%;
}

.profile-info {
  min-width: 0;
}

.profile-name-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.status-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
}

.status-ip {
  color: var(--oab-text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.status-url {
  max-width: 320px;
  color: var(--oab-muted);
  font-size: 12px;
  line-height: 1.45;
  word-break: break-all;
}

.row-actions {
  justify-content: center;
}

.row-action {
  color: var(--oab-accent);
}

.sync-empty {
  min-height: 100%;
}

.console-status-list,
.panel-stack,
.settings-popover,
.settings-section,
.compact-panel,
.text-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.console-status-list {
  margin: 14px 0;
}

.status-card-line {
  justify-content: flex-start;
  padding: 12px 14px;
  border-radius: var(--oab-radius-md);
  border: 1px solid var(--oab-border);
  background: var(--oab-card-bg);
}

.status-copy {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.status-copy.wide {
  align-items: flex-start;
}

.status-card-line.active {
  border-color: rgba(52, 199, 89, 0.18);
  background: rgba(52, 199, 89, 0.08);
}

.status-card-line.wide {
  align-items: flex-start;
}

.console-primary-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.console-primary-actions :deep(.el-button) {
  width: 100%;
  height: 40px;
  border-radius: 14px;
  margin-left: 0 !important;
}

.console-tabs {
  width: 100%;
  margin-bottom: 14px;
}

.console-card,
.delay-card,
.text-group-card {
  padding: 15px;
  border-radius: var(--oab-radius-lg);
  border: 1px solid var(--oab-border);
  background: var(--oab-card-bg);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-title,
.popover-title,
.section-title {
  color: var(--oab-text);
  font-weight: 700;
}

.card-title,
.popover-title {
  font-size: 15px;
}

.section-title {
  font-size: 14px;
}

.quick-grid,
.toggle-grid,
.hotkey-grid,
.range-row {
  display: grid;
  gap: 10px;
}

.quick-grid.two,
.toggle-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.list-head-actions :deep(.el-button) {
  min-width: 112px;
  height: 38px;
  border-radius: 14px;
  padding-inline: 16px;
  margin-left: 0 !important;
  white-space: nowrap;
}

.quick-grid :deep(.el-button) {
  width: 100%;
  min-width: 0;
  height: 40px;
  border-radius: 14px;
  margin-left: 0 !important;
  padding-inline: 14px;
  justify-content: center;
  white-space: nowrap;
}

.range-row {
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
}

.range-sep,
.delay-line {
  color: var(--oab-muted);
  font-size: 13px;
}

.wide-btn {
  width: 100%;
  height: 40px;
}

.wide-btn.dashed {
  border-style: dashed;
}

.card-actions.right {
  justify-content: flex-end;
}

.toggle-item {
  padding: 12px 13px;
  border-radius: var(--oab-radius-md);
  border: 1px solid var(--oab-border);
  background: var(--oab-panel-soft-bg);
  color: var(--oab-text-secondary);
  font-size: 13px;
  font-weight: 500;
}

.toggle-item.single,
.toggle-item.inline {
  width: 100%;
}

.toggle-item.block-gap {
  margin-top: 2px;
}

.delay-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hotkey-grid {
  grid-template-columns: 1fr;
}

.hotkey-item {
  display: grid;
  grid-template-columns: 118px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  color: var(--oab-text-secondary);
  font-size: 13px;
}

.popover-actions {
  justify-content: flex-end;
}

.console-error {
  margin-top: 14px;
}

:global(.sync-settings-popper) {
  padding: 14px !important;
  border-radius: var(--oab-radius-xl) !important;
  border: 1px solid var(--oab-border) !important;
  background: var(--oab-panel-solid-bg) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  box-shadow: none !important;
}

@media (max-width: 1320px) {
  .sync-layout {
    grid-template-columns: 1fr;
  }

  .sync-console {
    position: static;
  }
}

@media (max-width: 1100px) {
  .sync-hero-main,
  .sync-list-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-action-row,
  .list-head-actions {
    justify-content: flex-start;
  }

  .sync-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 920px) {
  .sync-metrics,
  .quick-grid.two,
  .toggle-grid,
  .range-row,
  .console-primary-actions,
  .hotkey-item {
    grid-template-columns: 1fr;
  }

  .sync-table-wrap {
    min-height: 480px;
    height: auto;
  }
}
</style>
