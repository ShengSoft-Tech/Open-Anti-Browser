<template>
  <div class="page-panel">
    <div class="panel-title-row">
      <div>
        <h3>{{ t('group.title') }}</h3>
        <p class="panel-desc">{{ t('group.description') }}</p>
      </div>
      <el-tag v-if="store.groupList.length" type="info" effect="plain">
        {{ store.groupList.length }}
      </el-tag>
    </div>

    <el-table v-if="store.groupList.length" :data="store.groupList" stripe>
      <el-table-column :label="t('group.name')" min-width="220">
        <template #default="{ row }">
          <span style="font-weight: 600">{{ displayGroupName(row.name) }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('group.profileCount')" width="100">
        <template #default="{ row }">
          <el-tag effect="plain" size="small">{{ row.count }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('group.runningCount')" width="100">
        <template #default="{ row }">
          <el-tag type="success" effect="plain" size="small">{{ row.running }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Chrome" width="100">
        <template #default="{ row }">
          <el-tag type="primary" effect="plain" size="small">{{ row.chrome }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="firefoxColumnVisible" label="Firefox" width="100">
        <template #default="{ row }">
          <el-tag type="warning" effect="plain" size="small">{{ row.firefox }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('profile.columns.actions')" width="200">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button size="small" type="success" plain @click="startGroup(row.name)">
              {{ t('group.startAll') }}
            </el-button>
            <el-button size="small" type="warning" plain @click="stopGroup(row.name)">
              {{ t('group.stopAll') }}
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div v-else class="empty-state">
      <el-icon><FolderOpened /></el-icon>
      <h3>{{ t('group.emptyTitle') }}</h3>
      <p>{{ t('group.emptyDescription') }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { FolderOpened } from '@element-plus/icons-vue'
import { useProfileStore } from '../stores/profile.js'
import { shouldShowFirefoxColumn } from '../lib/capabilitiesGating.js'

const { t } = useI18n()
const store = useProfileStore()

const firefoxColumnVisible = computed(() =>
  shouldShowFirefoxColumn(store.capabilities, store.groupList)
)

async function startGroup(name) {
  try {
    await store.startGroup(name)
    ElMessage.success(t('group.started', { name: displayGroupName(name) }))
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function stopGroup(name) {
  try {
    await store.stopGroup(name)
    ElMessage.success(t('group.stopped', { name: displayGroupName(name) }))
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function displayGroupName(name) {
  return name || t('group.ungrouped')
}
</script>
