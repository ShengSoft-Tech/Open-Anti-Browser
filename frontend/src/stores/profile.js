import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import { api } from '../lib/api.js'

function nowIso() {
  return new Date().toISOString()
}

export function createDefaultProfile(settings = null) {
  return {
    id: uuidv4().replace(/-/g, ''),
    name: '',
    group: '',
    remark: '',
    engine: 'chrome',
    proxy: {
      type: 'none',
      host: '',
      port: null,
      username: '',
      password: '',
    },
    proxy_bypass_rules: [],
    storage: {
      root_dir: settings?.user_data_root || '',
    },
    chrome: {
      executable_path: '',
      startup: {
        open_urls: [],
        window_size: '',
      },
      launch_args: [],
      disabled_global_extension_ids: [],
      fingerprint: {
        seed: null,
        auto_timezone: true,
        language: '',
        accept_language: '',
        timezone: '',
        platform: 'windows',
        platform_version: '',
        brand: 'Google Chrome',
        brand_version: '',
        hardware_concurrency_mode: 'random',
        hardware_concurrency: null,
        disable_spoofing: [],
      },
    },
    firefox: {
      executable_path: '',
      fingerprint_file_path: '',
      extension_paths: [],
      startup: {
        open_urls: [],
        window_size: '',
      },
      launch_args: [],
      disabled_global_extension_ids: [],
      fingerprint: {
        auto_timezone: true,
        language: '',
        timezone: '',
        font_system: 'windows',
        screen: {
          mode: 'auto',
          width: null,
          height: null,
        },
        webgl: {
          mode: 'random',
          vendor: '',
          renderer: '',
          version: '',
          glsl_version: '',
          unmasked_vendor: '',
          unmasked_renderer: '',
          max_texture_size: null,
          max_cube_map_texture_size: null,
          max_texture_image_units: null,
          max_vertex_attribs: null,
          aliased_point_size_max: null,
          max_viewport_dim: null,
        },
        hardware_concurrency_mode: 'random',
        hardware_concurrency: null,
        webrtc: {
          mode: 'random',
          local_ip: '',
          public_ip: '',
        },
        load_webrtc_block_extension: false,
        extra_fields: [],
      },
    },
    created_at: nowIso(),
    updated_at: nowIso(),
    last_used: null,
    status: 'stopped',
    runtime: null,
  }
}

export const useProfileStore = defineStore('profile', () => {
  const profiles = ref([])
  const settings = ref(null)
  const engines = ref({})
  const downloads = ref({})
  const capabilities = ref({})
  const apiInfo = ref(null)
  const synchronizer = ref(null)
  const syncMonitors = ref([])
  const loading = ref(false)
  const searchQuery = ref('')
  const filterGroup = ref('')
  const filterEngine = ref('')
  const selectedProfileIds = ref([])
  const startingProfileIds = ref({})

  const groups = computed(() => {
    const values = new Set()
    profiles.value.forEach(item => {
      if (item.group) values.add(item.group)
    })
    return Array.from(values).sort()
  })

  const savedProxies = computed(() => settings.value?.saved_proxies || [])
  const managedExtensions = computed(() => settings.value?.managed_extensions || [])

  const filteredProfiles = computed(() => {
    let list = [...profiles.value]
    if (filterGroup.value) {
      list = list.filter(item => item.group === filterGroup.value)
    }
    if (filterEngine.value) {
      list = list.filter(item => item.engine === filterEngine.value)
    }
    if (searchQuery.value.trim()) {
      const query = searchQuery.value.trim().toLowerCase()
      list = list.filter(item =>
        [item.name, item.group, item.remark]
          .filter(Boolean)
          .some(text => String(text).toLowerCase().includes(query))
      )
    }
    return list
  })

  const stats = computed(() => {
    const total = profiles.value.length
    const running = profiles.value.filter(item => item.status === 'running').length
    const chrome = profiles.value.filter(item => item.engine === 'chrome').length
    const firefox = profiles.value.filter(item => item.engine === 'firefox').length
    return {
      total,
      running,
      stopped: total - running,
      chrome,
      firefox,
    }
  })

  const groupList = computed(() => {
    const map = new Map()
    profiles.value.forEach(item => {
      const key = item.group || ''
      if (!map.has(key)) {
        map.set(key, { name: key, count: 0, running: 0, chrome: 0, firefox: 0 })
      }
      const group = map.get(key)
      group.count += 1
      if (item.status === 'running') group.running += 1
      if (item.engine === 'chrome') group.chrome += 1
      if (item.engine === 'firefox') group.firefox += 1
    })
    return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name))
  })

  async function bootstrap() {
    loading.value = true
    try {
      const data = await api.get('/api/bootstrap')
      settings.value = data.settings
      profiles.value = data.profiles
      engines.value = data.engines
      downloads.value = data.downloads || {}
      capabilities.value = data.capabilities || {}
      await refreshApiInfo()
      await refreshSynchronizer()
      return data
    } finally {
      loading.value = false
    }
  }

  async function refreshProfiles() {
    profiles.value = await api.get('/api/profiles')
  }

  async function refreshEngines() {
    engines.value = await api.get('/api/engines')
  }

  async function refreshDownloads() {
    downloads.value = await api.get('/api/downloads')
  }

  async function saveProfile(profile) {
    const saved = await api.post('/api/profiles', profile)
    await refreshProfiles()
    return saved
  }

  async function deleteProfile(id) {
    await api.delete(`/api/profiles/${id}`)
    await refreshProfiles()
  }

  async function deleteProfiles(ids) {
    for (const id of ids) {
      await api.delete(`/api/profiles/${id}`)
    }
    await refreshProfiles()
  }

  async function duplicateProfile(id) {
    const result = await api.post(`/api/profiles/${id}/duplicate`, {})
    await refreshProfiles()
    return result
  }

  async function startProfile(id) {
    if (startingProfileIds.value[id]) return null
    startingProfileIds.value = { ...startingProfileIds.value, [id]: true }
    try {
      const result = await api.post(`/api/profiles/${id}/start`, {})
      await refreshProfiles()
      return result
    } finally {
      const next = { ...startingProfileIds.value }
      delete next[id]
      startingProfileIds.value = next
    }
  }

  async function stopProfile(id) {
    const result = await api.post(`/api/profiles/${id}/stop`, {})
    await refreshProfiles()
    return result
  }

  function isProfileStarting(id) {
    return !!startingProfileIds.value[id]
  }

  async function startGroup(name) {
    const groupName = name ? encodeURIComponent(name) : '_ungrouped_'
    const result = await api.post(`/api/groups/${groupName}/start`, {})
    await refreshProfiles()
    return result
  }

  async function stopGroup(name) {
    const groupName = name ? encodeURIComponent(name) : '_ungrouped_'
    const result = await api.post(`/api/groups/${groupName}/stop`, {})
    await refreshProfiles()
    return result
  }

  async function testProxy(proxy) {
    return api.post('/api/proxy/test', proxy)
  }

  async function updateSettings(nextSettings) {
    const saved = await api.put('/api/settings', nextSettings)
    settings.value = saved
    await refreshEngines()
    await refreshApiInfo()
    return saved
  }

  async function saveSavedProxy(proxy) {
    const saved = await api.post('/api/saved-proxies', proxy)
    settings.value = await api.get('/api/settings')
    return saved
  }

  async function deleteSavedProxy(id) {
    await api.delete(`/api/saved-proxies/${id}`)
    settings.value = await api.get('/api/settings')
  }

  async function refreshSettings() {
    settings.value = await api.get('/api/settings')
    return settings.value
  }

  async function uploadManagedExtension(engine, file, name = '') {
    const form = new FormData()
    form.append('engine', engine)
    form.append('name', name || '')
    form.append('file', file)
    const saved = await api.post('/api/extensions/upload', form)
    await refreshSettings()
    return saved
  }

  async function importManagedExtensionFolder(engine, folderPath, name = '') {
    const saved = await api.post('/api/extensions/import-folder', {
      engine,
      folder_path: folderPath,
      name,
    })
    await refreshSettings()
    return saved
  }

  async function updateManagedExtension(id, payload) {
    const saved = await api.put(`/api/extensions/${id}`, payload)
    await refreshSettings()
    return saved
  }

  async function deleteManagedExtension(id) {
    await api.delete(`/api/extensions/${id}`)
    await refreshSettings()
    await refreshProfiles()
  }

  async function assignSavedProxy(proxyId, profileIds) {
    const result = await api.post(`/api/saved-proxies/${proxyId}/assign`, { profile_ids: profileIds })
    await refreshProfiles()
    return result
  }

  async function downloadEngine(engine) {
    const result = await api.post(`/api/engines/${engine}/download`, {})
    downloads.value = { ...downloads.value, [engine]: result }
    return result
  }

  async function importProfiles(file) {
    const form = new FormData()
    form.append('file', file)
    const result = await api.post('/api/import', form)
    await refreshProfiles()
    return result
  }

  async function exportProfiles() {
    return api.get('/api/export')
  }

  async function refreshApiInfo() {
    apiInfo.value = await api.get('/api/open-api/info')
    return apiInfo.value
  }

  async function refreshSynchronizer() {
    synchronizer.value = await api.get('/api/synchronizer/status')
    return synchronizer.value
  }

  async function refreshSyncMonitors() {
    syncMonitors.value = await api.get('/api/synchronizer/monitors')
    return syncMonitors.value
  }

  async function startSynchronizer(payload) {
    synchronizer.value = await api.post('/api/synchronizer/start', payload)
    return synchronizer.value
  }

  async function stopSynchronizer() {
    synchronizer.value = await api.post('/api/synchronizer/stop', {})
    return synchronizer.value
  }

  async function navigateSynchronizer(payload) {
    synchronizer.value = await api.post('/api/synchronizer/navigate', payload)
    return synchronizer.value
  }

  async function syncMasterUrlToFollowers() {
    synchronizer.value = await api.post('/api/synchronizer/sync-master-url', {})
    return synchronizer.value
  }

  async function showSyncWindows(profileIds) {
    return api.post('/api/synchronizer/show-windows', { profile_ids: profileIds })
  }

  async function uniformSyncWindows(profileIds) {
    return api.post('/api/synchronizer/uniform-size', { profile_ids: profileIds })
  }

  async function arrangeSyncWindows(payload) {
    return api.post('/api/synchronizer/arrange-windows', payload)
  }

  async function runSyncTextAction(payload) {
    return api.post('/api/synchronizer/text-action', payload)
  }

  async function runSyncTabAction(payload) {
    return api.post('/api/synchronizer/tab-action', payload)
  }

  async function regenerateApiKey() {
    apiInfo.value = await api.post('/api/open-api/regenerate-key', {})
    if (settings.value?.api_access) {
      settings.value = {
        ...settings.value,
        api_access: {
          ...settings.value.api_access,
          api_key: apiInfo.value.api_key,
        },
      }
    }
    return apiInfo.value
  }

  async function getBackendModeStatus() {
    const backendMode = await api.get('/api/backend-mode/status')
    apiInfo.value = apiInfo.value
      ? { ...apiInfo.value, backend_mode: backendMode }
      : { backend_mode: backendMode }
    return backendMode
  }

  async function startBackendMode() {
    const backendMode = await api.post('/api/backend-mode/start', {})
    apiInfo.value = apiInfo.value
      ? { ...apiInfo.value, backend_mode: backendMode }
      : { backend_mode: backendMode }
    return backendMode
  }

  async function stopBackendMode() {
    const backendMode = await api.post('/api/backend-mode/stop', {})
    apiInfo.value = apiInfo.value
      ? { ...apiInfo.value, backend_mode: backendMode }
      : { backend_mode: backendMode }
    return backendMode
  }

  async function exitDesktopApp() {
    return api.post('/api/app/exit', {})
  }

  async function pickDirectory(title = '', initialDir = '') {
    return api.post('/api/system/pick-directory', {
      title,
      initial_dir: initialDir,
    })
  }

  return {
    profiles,
    settings,
    engines,
    downloads,
    capabilities,
    apiInfo,
    synchronizer,
    syncMonitors,
    loading,
    searchQuery,
    filterGroup,
    filterEngine,
    selectedProfileIds,
    startingProfileIds,
    groups,
    savedProxies,
    filteredProfiles,
    stats,
    groupList,
    managedExtensions,
    bootstrap,
    refreshSettings,
    refreshProfiles,
    refreshEngines,
    refreshDownloads,
    saveProfile,
    deleteProfile,
    deleteProfiles,
    duplicateProfile,
    startProfile,
    stopProfile,
    isProfileStarting,
    startGroup,
    stopGroup,
    testProxy,
    updateSettings,
    saveSavedProxy,
    deleteSavedProxy,
    uploadManagedExtension,
    importManagedExtensionFolder,
    updateManagedExtension,
    deleteManagedExtension,
    assignSavedProxy,
    downloadEngine,
    importProfiles,
    exportProfiles,
    refreshApiInfo,
    refreshSynchronizer,
    refreshSyncMonitors,
    startSynchronizer,
    stopSynchronizer,
    navigateSynchronizer,
    syncMasterUrlToFollowers,
    showSyncWindows,
    uniformSyncWindows,
    arrangeSyncWindows,
    runSyncTextAction,
    runSyncTabAction,
    regenerateApiKey,
    getBackendModeStatus,
    startBackendMode,
    stopBackendMode,
    exitDesktopApp,
    pickDirectory,
  }
})
