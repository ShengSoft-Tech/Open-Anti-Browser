<template>
  <div class="settings-stack">
    <div class="page-panel">
      <div class="panel-title-row">
        <div>
          <h3>{{ t('settings.generalTitle') }}</h3>
          <p class="panel-desc">{{ t('settings.generalDesc') }}</p>
        </div>
      </div>

      <el-form label-position="top">
        <el-form-item :label="t('settings.userDataRoot')">
          <el-input v-model="form.user_data_root" :placeholder="t('settings.userDataRootPlaceholder')" />
          <div class="form-tip">{{ t('settings.userDataRootTip') }}</div>
        </el-form-item>
      </el-form>

      <div class="action-row">
        <el-button type="success" @click="saveSettings">{{ t('common.save') }}</el-button>
      </div>
    </div>

    <div class="page-panel" v-if="platformLimitsVisible">
      <div class="panel-title-row">
        <div>
          <h3>{{ t('platformLimits.title') }}</h3>
          <p class="panel-desc">{{ t('platformLimits.desc') }}</p>
        </div>
      </div>
      <ul class="platform-limits-list">
        <li>{{ t('platformLimits.firefoxItem') }}</li>
        <li>{{ t('platformLimits.windowItem') }}</li>
        <li>
          {{ t('platformLimits.gatekeeperItem') }}
          <code class="platform-limits-command">{{ GATEKEEPER_XATTR_COMMAND }}</code>
        </li>
      </ul>
      <div class="action-row">
        <el-button plain size="small" @click="openGatekeeperGuide">{{ t('platformLimits.reopenGatekeeper') }}</el-button>
      </div>
    </div>

    <div class="page-panel">
      <div class="panel-title-row">
        <div>
          <h3>{{ t('settings.chromeTitle') }}</h3>
          <p class="panel-desc">{{ t('settings.chromeDesc') }}</p>
        </div>
        <el-tag :type="engineTag(store.engines.chrome)">{{ engineLabel(store.engines.chrome) }}</el-tag>
      </div>
    </div>

    <div class="page-panel">
      <div class="panel-title-row">
        <div>
          <h3>{{ t('settings.firefoxTitle') }}</h3>
          <p class="panel-desc">{{ t('settings.firefoxDesc') }}</p>
        </div>
        <div class="panel-tag-group">
          <el-tag :type="engineTag(store.engines.firefox)">{{ engineLabel(store.engines.firefox) }}</el-tag>
          <el-tag v-if="platformLimitsVisible" type="info" size="small">{{ t('platformLimits.kernelWindowsOnly') }}</el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProfileStore } from '../stores/profile.js'
import { buildGatekeeperNoticeHtml, GATEKEEPER_XATTR_COMMAND } from '../lib/macosGatekeeperNotice.js'

const { t } = useI18n()
const store = useProfileStore()
const form = ref(defaultSettings())

// D-03:平台限制说明卡片只在非 Windows 且 capabilities 已解析时展示,避免 Windows 上出现
// 空洞的“本平台无限制”卡片,也避免 pre-bootstrap 阶段闪现(D-00:不从 navigator 推导平台)。
const platformLimitsVisible = computed(() => {
  const platform = store.capabilities?.platform
  return !!platform && platform !== 'win32'
})

watch(
  () => store.settings,
  value => {
    if (value) {
      form.value = JSON.parse(JSON.stringify(value))
    }
  },
  { immediate: true, deep: true },
)

function defaultSettings() {
  return {
    language: 'zh-CN',
    theme_mode: 'system',
    user_data_root: '',
    chrome: {
      executable_path: '',
      installer_url: '',
      download_path: '',
      keep_installer: true,
    },
    firefox: {
      executable_path: '',
      installer_url: '',
      download_path: '',
      keep_installer: true,
    },
    api_access: {
      enabled: true,
      api_key: '',
      backend_only_port: 18000,
    },
    saved_proxies: [],
  }
}

function engineTag(engine) {
  if (!engine?.installed) return 'danger'
  if (engine?.capability_ok === false) return 'warning'
  return 'success'
}

function engineLabel(engine) {
  if (!engine?.installed) return t('engine.notInstalled')
  if (engine?.capability_ok === false) return t('engine.needFingerprintBuild')
  return t('engine.ready')
}

function openGatekeeperGuide() {
  // buildGatekeeperNoticeHtml(t) 只组装开发者自撰 i18n 文案与模块常量,不拼接任何
  // API/用户/store 来源的动态值,避免向 dangerouslyUseHTMLString 引入注入面(T-04-02)。
  ElMessageBox.alert(buildGatekeeperNoticeHtml(t), t('gatekeeper.title'), {
    confirmButtonText: t('gatekeeper.confirm'),
    dangerouslyUseHTMLString: true,
    customClass: 'gatekeeper-notice-box',
  })
}

async function saveSettings() {
  try {
    await store.updateSettings(form.value)
    ElMessage.success(t('settings.saved'))
  } catch (error) {
    ElMessage.error(error.message)
  }
}
</script>

<style scoped>
.panel-tag-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.platform-limits-list {
  margin: 0 0 16px;
  padding-left: 20px;
  color: var(--oab-text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.platform-limits-list li + li {
  margin-top: 8px;
}

.platform-limits-command {
  display: inline-block;
  margin-left: 6px;
  padding: 2px 6px;
  border-radius: var(--oab-radius-sm);
  background: var(--oab-panel-soft-bg);
  border: 1px solid var(--oab-border);
  font-family: "SF Mono", Consolas, "SFMono-Regular", Menlo, monospace;
  font-size: 12px;
}
</style>
