<template>
  <div class="page-panel">
    <div class="profile-toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="store.searchQuery"
          :placeholder="t('profile.searchPlaceholder')"
          clearable
          :prefix-icon="Search"
          style="width: 260px"
        />
        <el-select
          v-model="store.filterGroup"
          clearable
          :placeholder="t('profile.allGroups')"
          style="width: 150px"
        >
          <el-option v-for="group in store.groups" :key="group" :label="group" :value="group" />
        </el-select>
        <el-select
          v-model="store.filterEngine"
          clearable
          :placeholder="t('profile.allEngines')"
          style="width: 140px"
        >
          <el-option label="Chrome" value="chrome" />
          <el-option v-if="firefoxEngineVisible" label="Firefox" value="firefox" />
        </el-select>
      </div>

      <div class="toolbar-right">
        <transition name="toolbar-fade">
          <div v-if="selectedIds.length" class="action-row">
            <el-button
              type="danger"
              plain
              @click="handleBatchDelete"
            >
              {{ t('profile.deleteSelected', { n: selectedIds.length }) }}
            </el-button>
            <el-button
              type="success"
              plain
              @click="handleBatchStart"
            >
              {{ t('profile.startSelected', { n: selectedIds.length }) }}
            </el-button>
          </div>
        </transition>
      </div>
    </div>

    <el-table
      v-if="store.filteredProfiles.length"
      :data="pagedProfiles"
      row-key="id"
      stripe
    >
      <el-table-column width="48">
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

      <el-table-column :label="t('profile.columns.profile')" min-width="260">
        <template #default="{ row }">
          <div class="profile-card-row">
            <div class="profile-avatar engine">
              <img
                class="profile-avatar-icon"
                :src="row.engine === 'chrome' ? chromeIcon : firefoxIcon"
                :alt="row.engine"
              />
            </div>
            <div>
              <div class="profile-name">{{ row.name || t('common.unnamed') }}</div>
              <div class="profile-meta">
                {{ row.remark || t('profile.noDescription') }}
              </div>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column :label="t('profile.columns.engine')" width="160">
        <template #default="{ row }">
          <div class="engine-tag-stack">
            <el-tag :type="row.engine === 'chrome' ? 'primary' : 'warning'" effect="plain" size="small">
              {{ row.engine === 'chrome' ? 'Chrome' : 'Firefox' }}
            </el-tag>
            <el-tag v-if="row.engine === 'firefox' && !firefoxEngineVisible" type="info" size="small">
              {{ t('platformLimits.windowsOnlyTag') }}
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column :label="t('profile.columns.group')" width="130">
        <template #default="{ row }">
          <el-tag v-if="row.group" type="info" effect="plain" size="small">{{ row.group }}</el-tag>
          <span v-else class="muted-text">—</span>
        </template>
      </el-table-column>

      <el-table-column :label="t('profile.columns.proxy')" min-width="200">
        <template #default="{ row }">
          <template v-if="row.proxy.type !== 'none' && row.proxy.host">
            <div class="proxy-line">
              <el-tag size="small" :type="row.proxy.type === 'socks5' ? 'warning' : 'success'" effect="plain">
                {{ row.proxy.type.toUpperCase() }}
              </el-tag>
              <span>{{ row.proxy.host }}:{{ row.proxy.port }}</span>
            </div>
          </template>
          <span v-else class="muted-text">{{ t('common.direct') }}</span>
        </template>
      </el-table-column>

      <el-table-column :label="t('profile.columns.status')" width="170">
        <template #default="{ row }">
          <div class="status-block">
            <div>
              <span class="status-dot" :class="row.status"></span>
              <span>{{ t(`common.${row.status}`) }}</span>
            </div>
            <div v-if="row.runtime?.resolved_ip" class="status-subtext">
              {{ row.runtime.resolved_ip }} / {{ row.runtime.resolved_timezone || '--' }}
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column :label="t('profile.columns.lastUsed')" width="160">
        <template #default="{ row }">
          <span class="muted-text">{{ formatTime(row.last_used) || t('common.never') }}</span>
        </template>
      </el-table-column>

      <el-table-column :label="t('profile.columns.actions')" width="220" fixed="right">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button
              v-if="row.status !== 'running'"
              type="success"
              size="small"
              plain
              :loading="row.status === 'starting' || store.isProfileStarting(row.id)"
              :disabled="row.status === 'starting' || store.isProfileStarting(row.id)"
              @click.stop="handleStart(row)"
            >
              <el-icon v-if="row.status !== 'starting' && !store.isProfileStarting(row.id)"><VideoPlay /></el-icon>
              {{ row.status === 'starting' || store.isProfileStarting(row.id) ? t('common.starting') : t('common.start') }}
            </el-button>
            <el-button
              v-else
              type="warning"
              size="small"
              plain
              @click.stop="handleStop(row)"
            >
              <el-icon><VideoPause /></el-icon>
              {{ t('common.stop') }}
            </el-button>
            <el-button size="small" plain @click.stop="$emit('edit', row)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-dropdown trigger="click" @command="cmd => handleCommand(cmd, row)">
              <el-button size="small" text>
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="duplicate">
                    <el-icon><CopyDocument /></el-icon>
                    {{ t('common.duplicate') }}
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <span class="danger-text">
                      <el-icon><Delete /></el-icon>
                      {{ t('common.delete') }}
                    </span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="store.filteredProfiles.length" class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="store.filteredProfiles.length"
        :pager-count="5"
        layout="total, prev, pager, next"
        background
        small
      />
    </div>

    <div v-else class="empty-state large">
      <el-icon><Monitor /></el-icon>
      <h3>{{ t('profile.emptyTitle') }}</h3>
      <p>{{ t('profile.emptyDesc') }}</p>
      <el-button type="primary" size="large" @click="$emit('create')">
        {{ t('profile.emptyAction') }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Monitor,
  Edit,
  Delete,
  MoreFilled,
  CopyDocument,
  VideoPlay,
  VideoPause,
} from '@element-plus/icons-vue'
import { useProfileStore } from '../stores/profile.js'
import { isFirefoxEngineAvailable } from '../lib/capabilitiesGating.js'
import chromeIcon from '../assets/chrome.svg'
import firefoxIcon from '../assets/firefox.png'

const { t } = useI18n()
defineEmits(['create', 'edit'])
const store = useProfileStore()

const firefoxEngineVisible = computed(() => isFirefoxEngineAvailable(store.capabilities))

const pageSize = 10
const currentPage = ref(1)

const pagedProfiles = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return store.filteredProfiles.slice(start, start + pageSize)
})

watch(
  () => [store.searchQuery, store.filterGroup, store.filterEngine],
  () => { currentPage.value = 1 },
)

const selectedIds = computed({
  get: () => store.selectedProfileIds || [],
  set: value => {
    store.selectedProfileIds = Array.isArray(value) ? value : []
  },
})
const visibleIds = computed(() => pagedProfiles.value.map(item => item.id))
const allVisibleSelected = computed(() => {
  if (!visibleIds.value.length) return false
  return visibleIds.value.every(id => selectedIds.value.includes(id))
})
const someVisibleSelected = computed(() => {
  if (!visibleIds.value.length) return false
  const visibleSelectedCount = visibleIds.value.filter(id => selectedIds.value.includes(id)).length
  return visibleSelectedCount > 0 && visibleSelectedCount < visibleIds.value.length
})

watch(
  () => store.profiles,
  () => {
    selectedIds.value = selectedIds.value.filter(id => store.profiles.some(item => item.id === id))
  },
  { deep: false },
)

function isSelected(profileId) {
  return selectedIds.value.includes(profileId)
}

function handleSelect(profileId, checked) {
  const next = new Set(selectedIds.value)
  if (checked) {
    next.add(profileId)
  } else {
    next.delete(profileId)
  }
  selectedIds.value = Array.from(next)
}

function handleSelectAll(checked) {
  const next = new Set(selectedIds.value)
  if (checked) {
    visibleIds.value.forEach(id => next.add(id))
  } else {
    visibleIds.value.forEach(id => next.delete(id))
  }
  selectedIds.value = Array.from(next)
}

function formatTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = item => String(item).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

async function handleStart(row) {
  if (row.status === 'starting' || store.isProfileStarting(row.id)) return
  try {
    await store.startProfile(row.id)
    ElMessage.success(t('profile.started', { name: row.name }))
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function handleStop(row) {
  try {
    await store.stopProfile(row.id)
    ElMessage.success(t('profile.stopped', { name: row.name }))
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function handleCommand(command, row) {
  if (command === 'duplicate') {
    try {
      await store.duplicateProfile(row.id)
      ElMessage.success(t('profile.duplicated'))
    } catch (error) {
      ElMessage.error(error.message)
    }
    return
  }

  await ElMessageBox.confirm(
    t('profile.confirmDelete', { name: row.name }),
    t('profile.confirmDeleteTitle'),
    {
      type: 'warning',
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
    },
  )
  try {
    await store.deleteProfile(row.id)
    ElMessage.success(t('profile.deleted'))
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(
    t('profile.confirmBatchDelete', { n: selectedIds.value.length }),
    t('profile.confirmDeleteTitle'),
    {
      type: 'warning',
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
    },
  )
  try {
    await store.deleteProfiles(selectedIds.value)
    selectedIds.value = []
    ElMessage.success(t('profile.deleted'))
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function handleBatchStart() {
  try {
    const queuedIds = store.filteredProfiles
      .filter(item => selectedIds.value.includes(item.id))
      .filter(item => item.status === 'stopped' && !store.isProfileStarting(item.id))
      .map(item => item.id)

    for (const id of queuedIds) {
      await store.startProfile(id)
    }
    ElMessage.success(t('profile.batchStarted', { n: queuedIds.length }))
    selectedIds.value = []
  } catch (error) {
    ElMessage.error(error.message)
  }
}
</script>

<style scoped>
.toolbar-fade-enter-active,
.toolbar-fade-leave-active {
  transition: all 0.25s ease;
}

.toolbar-fade-enter-from,
.toolbar-fade-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

.engine-tag-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
