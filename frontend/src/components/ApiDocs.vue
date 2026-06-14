<template>
  <div class="api-docs-layout">
    <div class="page-panel api-docs-hero">
      <div class="panel-title-row">
        <div>
          <h3>{{ copy.title }}</h3>
          <p class="panel-desc">{{ copy.desc }}</p>
        </div>
        <div class="action-row">
          <el-button plain @click="openUrl('https://github.com/Kaliiiiiiiiii-Vinyzu/patchright')">Patchright</el-button>
          <el-button plain @click="openUrl('https://github.com/LoseNine/ruyipage')">RuyiPage</el-button>
        </div>
      </div>

      <div class="api-overview-grid">
        <div class="summary-item">
          <span>{{ copy.baseUrl }}</span>
          <strong>{{ baseUrl }}</strong>
        </div>
        <div class="summary-item">
          <span>{{ copy.apiKey }}</span>
          <strong class="api-key-text">{{ apiKey }}</strong>
        </div>
        <div class="summary-item">
          <span>{{ copy.authHeader }}</span>
          <strong>X-API-Key: {{ apiKey }}</strong>
        </div>
        <div class="summary-item">
          <span>{{ copy.debugPort }}</span>
          <strong>{{ copy.debugPortDesc }}</strong>
        </div>
      </div>
    </div>

    <div class="page-panel">
      <div class="panel-title-row compact">
        <div>
          <h3>{{ copy.quickStartTitle }}</h3>
          <p class="panel-desc">{{ copy.quickStartDesc }}</p>
        </div>
      </div>
      <div class="api-flow-grid">
        <div v-for="step in copy.quickSteps" :key="step.title" class="api-flow-card">
          <div class="api-flow-index">{{ step.index }}</div>
          <div>
            <strong>{{ step.title }}</strong>
            <p>{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="page-panel">
      <div class="panel-title-row compact">
        <div>
          <h3>{{ copy.endpointTitle }}</h3>
          <p class="panel-desc">{{ copy.endpointDesc }}</p>
        </div>
      </div>

      <div class="api-endpoint-list">
        <div v-for="endpoint in endpoints" :key="endpoint.path + endpoint.method" class="api-endpoint-card">
          <div class="api-endpoint-head">
            <el-tag :type="methodTag(endpoint.method)" effect="dark">{{ endpoint.method }}</el-tag>
            <code>{{ endpoint.path }}</code>
          </div>
          <h4>{{ endpoint.title }}</h4>
          <p>{{ endpoint.desc }}</p>

          <div class="api-table-wrap">
            <table class="api-doc-table">
              <thead>
                <tr>
                  <th>{{ copy.paramName }}</th>
                  <th>{{ copy.paramPosition }}</th>
                  <th>{{ copy.paramRequired }}</th>
                  <th>{{ copy.paramDesc }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="param in endpoint.params" :key="param.name + param.position">
                  <td><code>{{ param.name }}</code></td>
                  <td>{{ param.position }}</td>
                  <td>{{ param.required }}</td>
                  <td>{{ param.desc }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="api-code-grid">
            <div>
              <div class="api-code-title">{{ copy.requestExample }}</div>
              <div class="code-block">{{ endpoint.request }}</div>
            </div>
            <div>
              <div class="api-code-title">{{ copy.responseExample }}</div>
              <div class="code-block">{{ endpoint.response }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="page-panel">
      <div class="panel-title-row compact">
        <div>
          <h3>{{ copy.profilePayloadTitle }}</h3>
          <p class="panel-desc">{{ copy.profilePayloadDesc }}</p>
        </div>
      </div>

      <div class="api-automation-grid">
        <div class="api-automation-card">
          <div class="api-automation-title">
            <el-tag type="primary">Chrome</el-tag>
            <h4>{{ copy.chromePayloadTitle }}</h4>
          </div>
          <div class="api-table-wrap">
            <table class="api-doc-table">
              <thead>
                <tr>
                  <th>{{ copy.paramName }}</th>
                  <th>{{ copy.paramRequired }}</th>
                  <th>{{ copy.paramDesc }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="field in chromeProfileFields" :key="field.name">
                  <td><code>{{ field.name }}</code></td>
                  <td>{{ field.required }}</td>
                  <td>{{ field.desc }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="api-code-title">{{ copy.requestExample }}</div>
          <div class="code-block">{{ chromeProfileExample }}</div>
        </div>

        <div class="api-automation-card">
          <div class="api-automation-title">
            <el-tag type="warning">Firefox</el-tag>
            <h4>{{ copy.firefoxPayloadTitle }}</h4>
          </div>
          <div class="api-table-wrap">
            <table class="api-doc-table">
              <thead>
                <tr>
                  <th>{{ copy.paramName }}</th>
                  <th>{{ copy.paramRequired }}</th>
                  <th>{{ copy.paramDesc }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="field in firefoxProfileFields" :key="field.name">
                  <td><code>{{ field.name }}</code></td>
                  <td>{{ field.required }}</td>
                  <td>{{ field.desc }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="api-code-title">{{ copy.requestExample }}</div>
          <div class="code-block">{{ firefoxProfileExample }}</div>
        </div>
      </div>
    </div>

    <div class="page-panel">
      <div class="panel-title-row compact">
        <div>
          <h3>{{ copy.automationTitle }}</h3>
          <p class="panel-desc">{{ copy.automationDesc }}</p>
        </div>
      </div>

      <div class="api-automation-grid">
        <div class="api-automation-card">
          <div class="api-automation-title">
            <el-tag type="primary">Chrome</el-tag>
            <h4>{{ copy.chromeAutomationTitle }}</h4>
          </div>
          <p>{{ copy.chromeAutomationDesc }}</p>
          <div class="code-block">{{ chromeAutomationExample }}</div>
        </div>

        <div class="api-automation-card">
          <div class="api-automation-title">
            <el-tag type="warning">Firefox</el-tag>
            <h4>{{ copy.firefoxAutomationTitle }}</h4>
          </div>
          <p>{{ copy.firefoxAutomationDesc }}</p>
          <div class="code-block">{{ firefoxAutomationExample }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { api } from '../lib/api.js'
import { useProfileStore } from '../stores/profile.js'

const { locale } = useI18n()
const store = useProfileStore()

const apiInfo = computed(() => store.apiInfo)
const baseUrl = computed(() => apiInfo.value?.current_base_url || 'http://127.0.0.1:8000/open-api')
const apiKey = computed(() => apiInfo.value?.api_key || 'YOUR_API_KEY')
const profileId = computed(() => store.profiles?.[0]?.id || 'PROFILE_ID')

const copy = computed(() => {
  if (locale.value === 'en-US') {
    return {
      title: 'Open-Anti-Browser API Guide',
      desc: 'A readable guide for local API calls, launch responses, debug ports, and automation examples',
      baseUrl: 'Base URL',
      apiKey: 'API Key',
      authHeader: 'Required request header',
      debugPort: 'Launch response',
      debugPortDesc: 'The start API returns port, debug_port, debug_url and runtime.remote_debugging_port. Firefox also returns marionette_port, selenium_port and runtime.marionette_port',
      quickStartTitle: 'Quick start',
      quickStartDesc: 'Call the API, launch a browser profile, then connect your automation client to the returned port',
      quickSteps: [
        { index: '1', title: 'Get profiles', desc: 'Use GET /profiles to find the target profile id' },
        { index: '2', title: 'Start profile', desc: 'Use POST /profiles/{profile_id}/start and read the returned port' },
        { index: '3', title: 'Connect automation', desc: 'Chrome uses Patchright over CDP, Firefox uses RuyiPage with port, or Selenium with selenium_port / marionette_port' },
      ],
      endpointTitle: 'Main endpoints',
      endpointDesc: 'The examples below use the current local address and API Key from this app',
      profilePayloadTitle: 'Profile payload fields',
      profilePayloadDesc: 'Use these nested fields when creating or updating Chrome and Firefox profiles',
      chromePayloadTitle: 'Chrome profile fields',
      firefoxPayloadTitle: 'Firefox profile fields',
      paramName: 'Name',
      paramPosition: 'Position',
      paramRequired: 'Required',
      paramDesc: 'Description',
      requestExample: 'Request example',
      responseExample: 'Response example',
      automationTitle: 'Browser automation examples',
      automationDesc: 'Use the port returned by the start API to control the launched browser instance',
      chromeAutomationTitle: 'Patchright for Chrome',
      chromeAutomationDesc: 'Patchright follows the Playwright style API and connects to the Chromium debugging port returned by the API',
      firefoxAutomationTitle: 'RuyiPage / Selenium for Firefox',
      firefoxAutomationDesc: 'RuyiPage attaches to the port returned by the API. Selenium connects through GeckoDriver with selenium_port or marionette_port',
      yes: 'Yes',
      no: 'No',
      header: 'Header',
      path: 'Path',
      query: 'Query',
      body: 'Body',
      none: 'None',
      endpoints: {
        healthTitle: 'Check API status',
        healthDesc: 'Returns whether the local Open API service is alive',
        listTitle: 'List browser profiles',
        listDesc: 'Returns all saved Chrome and Firefox profiles, including runtime status',
        createTitle: 'Create or update a browser profile',
        createDesc: 'Creates a profile when id is new, or updates the profile when id already exists',
        startTitle: 'Start a browser profile',
        startDesc: 'Starts the selected browser profile and returns the debugging port for automation',
        stopTitle: 'Stop a browser profile',
        stopDesc: 'Stops the selected browser profile',
        deleteTitle: 'Delete a browser profile',
        deleteDesc: 'Deletes the specified browser profile',
        settingsTitle: 'Read global settings',
        settingsDesc: 'Returns global settings, engine paths and saved API settings',
        proxiesTitle: 'List saved proxies',
        proxiesDesc: 'Returns saved proxies that can be assigned to browser profiles',
        proxyTestTitle: 'Test proxy',
        proxyTestDesc: 'Tests a proxy and returns the resolved IP, language and timezone',
      },
    }
  }

  return {
    title: 'Open-Anti-Browser API 调用说明',
    desc: '这里按真实使用流程说明本地 API、启动返回值、调试端口和自动化接入方式',
    baseUrl: '调用地址',
    apiKey: 'API Key',
    authHeader: '请求必须携带的请求头',
    debugPort: '启动接口返回',
    debugPortDesc: '启动接口会返回 port、debug_port、debug_url 和 runtime.remote_debugging_port，Firefox 还会返回 marionette_port、selenium_port 和 runtime.marionette_port',
    quickStartTitle: '快速流程',
    quickStartDesc: '先查配置，再启动浏览器，最后用返回的端口接入自动化工具',
    quickSteps: [
      { index: '1', title: '读取配置', desc: '调用 GET /profiles 找到要启动的配置 id' },
      { index: '2', title: '启动配置', desc: '调用 POST /profiles/{profile_id}/start，并读取返回里的 port' },
      { index: '3', title: '接入自动化', desc: 'Chrome 用 Patchright 连接 CDP，Firefox 用 RuyiPage 传入 port，Selenium 使用 selenium_port / marionette_port' },
    ],
    endpointTitle: '主要接口',
    endpointDesc: '下面示例会自动使用当前窗口的本地地址和 API Key',
    profilePayloadTitle: '浏览器配置请求体字段',
    profilePayloadDesc: '创建或更新配置时，Chrome 和 Firefox 的专属字段都写在这里',
    chromePayloadTitle: 'Chrome 配置字段',
    firefoxPayloadTitle: 'Firefox 配置字段',
    paramName: '名称',
    paramPosition: '位置',
    paramRequired: '必填',
    paramDesc: '说明',
    requestExample: '请求示例',
    responseExample: '返回示例',
    automationTitle: '浏览器自动化示例',
    automationDesc: '启动接口返回的 port 就是后续自动化连接要用的端口',
    chromeAutomationTitle: 'Chrome 使用 Patchright',
    chromeAutomationDesc: 'Patchright 用法和 Playwright 风格一致，使用返回端口连接 Chrome 的 CDP 调试地址',
    firefoxAutomationTitle: 'Firefox 使用 RuyiPage / Selenium',
    firefoxAutomationDesc: 'RuyiPage 使用启动接口返回的 port 连接内核，Selenium 通过 GeckoDriver 使用 selenium_port 或 marionette_port 连接',
    yes: '是',
    no: '否',
    header: '请求头',
    path: '路径',
    query: '查询',
    body: '请求体',
    none: '无',
    endpoints: {
      healthTitle: '检查 API 状态',
      healthDesc: '确认本地 Open API 服务是否可用',
      listTitle: '获取浏览器配置列表',
      listDesc: '返回所有 Chrome 和 Firefox 配置，并带上当前运行状态',
      createTitle: '创建或更新浏览器配置',
      createDesc: 'id 不存在时创建配置，id 已存在时更新配置',
      startTitle: '启动浏览器配置',
      startDesc: '启动指定配置，并返回后续自动化要用的调试端口',
      stopTitle: '停止浏览器配置',
      stopDesc: '停止指定配置',
      deleteTitle: '删除浏览器配置',
      deleteDesc: '删除指定的浏览器配置',
      settingsTitle: '读取全局设置',
      settingsDesc: '返回全局设置、内核路径和 API 设置',
      proxiesTitle: '获取已保存代理',
      proxiesDesc: '返回代理管理里保存的代理列表',
      proxyTestTitle: '测试代理',
      proxyTestDesc: '测试代理连通性，并返回解析到的 IP、语言和时区',
    },
  }
})

const authParam = computed(() => ({
  name: 'X-API-Key',
  position: copy.value.header,
  required: copy.value.yes,
  desc: locale.value === 'en-US' ? 'Use the API Key shown on the API Access page' : '填写 API 调用页面显示的 API Key',
}))

const chromeProfileFields = computed(() => {
  if (locale.value === 'en-US') {
    return [
      { name: 'id', required: copy.value.no, desc: 'Profile id. Omit it when creating a new profile' },
      { name: 'name', required: copy.value.no, desc: 'Profile name. Auto-numbered when empty' },
      { name: 'group', required: copy.value.no, desc: 'Optional profile group' },
      { name: 'remark', required: copy.value.no, desc: 'Optional note for this profile' },
      { name: 'engine', required: copy.value.yes, desc: 'Use chrome' },
      { name: 'proxy.type / host / port / username / password', required: copy.value.no, desc: 'Proxy object for this profile' },
      { name: 'storage.root_dir', required: copy.value.no, desc: 'Custom user-data root for this profile' },
      { name: 'chrome.fingerprint.seed', required: copy.value.no, desc: 'Fixed fingerprint id. Leave empty to auto-generate once on save' },
      { name: 'chrome.fingerprint.auto_timezone', required: copy.value.no, desc: 'Resolve language and timezone from IP automatically' },
      { name: 'chrome.fingerprint.language', required: copy.value.no, desc: 'Manual browser language when auto_timezone is false' },
      { name: 'chrome.fingerprint.accept_language', required: copy.value.no, desc: 'Manual Accept-Language header when auto_timezone is false' },
      { name: 'chrome.fingerprint.timezone', required: copy.value.no, desc: 'Manual timezone when auto_timezone is false' },
      { name: 'chrome.fingerprint.platform', required: copy.value.no, desc: 'windows / macos / linux' },
      { name: 'chrome.fingerprint.hardware_concurrency_mode', required: copy.value.no, desc: 'auto / manual / random' },
      { name: 'chrome.fingerprint.hardware_concurrency', required: copy.value.no, desc: 'Manual CPU thread count when mode is manual' },
      { name: 'chrome.fingerprint.disable_spoofing[]', required: copy.value.no, desc: 'Disable specific spoofing modules such as font, audio, canvas, clientrects, gpu' },
      { name: 'chrome.startup.window_size', required: copy.value.no, desc: 'Window size such as 1600,900' },
      { name: 'chrome.startup.open_urls[]', required: copy.value.no, desc: 'URLs opened after launch' },
      { name: 'chrome.launch_args[]', required: copy.value.no, desc: 'Extra browser launch arguments' },
      { name: 'chrome.disabled_global_extension_ids[]', required: copy.value.no, desc: 'Global Chrome extensions disabled only for this profile' },
    ]
  }

  return [
    { name: 'id', required: copy.value.no, desc: '配置 id，创建新配置时可以不传' },
    { name: 'name', required: copy.value.no, desc: '配置名称，留空会自动按顺序补成 1、2、3' },
    { name: 'group', required: copy.value.no, desc: '可选分组' },
    { name: 'remark', required: copy.value.no, desc: '备注说明' },
    { name: 'engine', required: copy.value.yes, desc: '固定填 chrome' },
    { name: 'proxy.type / host / port / username / password', required: copy.value.no, desc: '当前配置要使用的代理对象' },
    { name: 'storage.root_dir', required: copy.value.no, desc: '当前配置单独使用的用户目录根路径' },
    { name: 'chrome.fingerprint.seed', required: copy.value.no, desc: '固定 fingerprint id，留空时保存时自动生成一个固定值' },
    { name: 'chrome.fingerprint.auto_timezone', required: copy.value.no, desc: '是否按 IP 自动解析语言和时区' },
    { name: 'chrome.fingerprint.language', required: copy.value.no, desc: '关闭自动解析后手动指定浏览器语言' },
    { name: 'chrome.fingerprint.accept_language', required: copy.value.no, desc: '关闭自动解析后手动指定 Accept-Language' },
    { name: 'chrome.fingerprint.timezone', required: copy.value.no, desc: '关闭自动解析后手动指定时区' },
    { name: 'chrome.fingerprint.platform', required: copy.value.no, desc: 'windows / macos / linux' },
    { name: 'chrome.fingerprint.hardware_concurrency_mode', required: copy.value.no, desc: 'CPU 线程数来源：auto / manual / random' },
    { name: 'chrome.fingerprint.hardware_concurrency', required: copy.value.no, desc: '手动线程数，仅在 manual 时生效' },
    { name: 'chrome.fingerprint.disable_spoofing[]', required: copy.value.no, desc: '禁用指定伪装模块，例如 font、audio、canvas、clientrects、gpu' },
    { name: 'chrome.startup.window_size', required: copy.value.no, desc: '窗口大小，例如 1600,900' },
    { name: 'chrome.startup.open_urls[]', required: copy.value.no, desc: '启动后自动打开的网址列表' },
    { name: 'chrome.launch_args[]', required: copy.value.no, desc: '额外启动参数列表' },
    { name: 'chrome.disabled_global_extension_ids[]', required: copy.value.no, desc: '只对当前配置禁用的全局 Chrome 扩展 id 列表' },
  ]
})

const firefoxProfileFields = computed(() => {
  if (locale.value === 'en-US') {
    return [
      { name: 'id', required: copy.value.no, desc: 'Profile id. Omit it when creating a new profile' },
      { name: 'name', required: copy.value.no, desc: 'Profile name. Auto-numbered when empty' },
      { name: 'group', required: copy.value.no, desc: 'Optional profile group' },
      { name: 'remark', required: copy.value.no, desc: 'Optional note for this profile' },
      { name: 'engine', required: copy.value.yes, desc: 'Use firefox' },
      { name: 'proxy.type / host / port / username / password', required: copy.value.no, desc: 'Proxy object for this profile' },
      { name: 'storage.root_dir', required: copy.value.no, desc: 'Custom user-data root for this profile' },
      { name: 'firefox.fingerprint.auto_timezone', required: copy.value.no, desc: 'Resolve language and timezone from IP automatically' },
      { name: 'firefox.fingerprint.language', required: copy.value.no, desc: 'Manual browser language when auto_timezone is false' },
      { name: 'firefox.fingerprint.timezone', required: copy.value.no, desc: 'Manual timezone when auto_timezone is false' },
      { name: 'firefox.fingerprint.font_system', required: copy.value.no, desc: 'windows / mac / linux' },
      { name: 'firefox.fingerprint.screen.mode / width / height', required: copy.value.no, desc: 'Screen mode and manual size values' },
      { name: 'firefox.fingerprint.webgl.mode', required: copy.value.no, desc: 'auto / manual / random' },
      { name: 'firefox.fingerprint.webgl.vendor / renderer / version / glsl_version', required: copy.value.no, desc: 'Manual WebGL values when mode is manual' },
      { name: 'firefox.fingerprint.webgl.unmasked_vendor / unmasked_renderer', required: copy.value.no, desc: 'Manual unmasked WebGL values' },
      { name: 'firefox.fingerprint.webgl.max_texture_size / max_cube_map_texture_size / max_texture_image_units / max_vertex_attribs / aliased_point_size_max / max_viewport_dim', required: copy.value.no, desc: 'Manual WebGL numeric limits' },
      { name: 'firefox.fingerprint.hardware_concurrency_mode / hardware_concurrency', required: copy.value.no, desc: 'CPU thread mode and manual value' },
      { name: 'firefox.fingerprint.webrtc.mode / local_ip / public_ip', required: copy.value.no, desc: 'WebRTC mode and manual IP values' },
      { name: 'firefox.fingerprint.load_webrtc_block_extension', required: copy.value.no, desc: 'Enable the built-in WebRTC block extension' },
      { name: 'firefox.fingerprint.extra_fields[]', required: copy.value.no, desc: 'Extra fingerprint file lines as { key, value }' },
      { name: 'firefox.fingerprint_file_path', required: copy.value.no, desc: 'Custom fingerprint file path. Leave empty to auto-generate inside the profile' },
      { name: 'firefox.startup.window_size', required: copy.value.no, desc: 'Window size such as 1600,900' },
      { name: 'firefox.startup.open_urls[]', required: copy.value.no, desc: 'URLs opened after launch' },
      { name: 'firefox.launch_args[]', required: copy.value.no, desc: 'Extra browser launch arguments' },
      { name: 'firefox.disabled_global_extension_ids[]', required: copy.value.no, desc: 'Global Firefox extensions disabled only for this profile' },
    ]
  }

  return [
    { name: 'id', required: copy.value.no, desc: '配置 id，创建新配置时可以不传' },
    { name: 'name', required: copy.value.no, desc: '配置名称，留空会自动按顺序补成 1、2、3' },
    { name: 'group', required: copy.value.no, desc: '可选分组' },
    { name: 'remark', required: copy.value.no, desc: '备注说明' },
    { name: 'engine', required: copy.value.yes, desc: '固定填 firefox' },
    { name: 'proxy.type / host / port / username / password', required: copy.value.no, desc: '当前配置要使用的代理对象' },
    { name: 'storage.root_dir', required: copy.value.no, desc: '当前配置单独使用的用户目录根路径' },
    { name: 'firefox.fingerprint.auto_timezone', required: copy.value.no, desc: '是否按 IP 自动解析语言和时区' },
    { name: 'firefox.fingerprint.language', required: copy.value.no, desc: '关闭自动解析后手动指定浏览器语言' },
    { name: 'firefox.fingerprint.timezone', required: copy.value.no, desc: '关闭自动解析后手动指定时区' },
    { name: 'firefox.fingerprint.font_system', required: copy.value.no, desc: '字体系统，可选 windows / mac / linux' },
    { name: 'firefox.fingerprint.screen.mode / width / height', required: copy.value.no, desc: '屏幕模式与手动宽高' },
    { name: 'firefox.fingerprint.webgl.mode', required: copy.value.no, desc: 'WebGL 来源：auto / manual / random' },
    { name: 'firefox.fingerprint.webgl.vendor / renderer / version / glsl_version', required: copy.value.no, desc: '手动 WebGL 文本字段' },
    { name: 'firefox.fingerprint.webgl.unmasked_vendor / unmasked_renderer', required: copy.value.no, desc: '手动 WebGL unmasked 字段' },
    { name: 'firefox.fingerprint.webgl.max_texture_size / max_cube_map_texture_size / max_texture_image_units / max_vertex_attribs / aliased_point_size_max / max_viewport_dim', required: copy.value.no, desc: '手动 WebGL 数值上限' },
    { name: 'firefox.fingerprint.hardware_concurrency_mode / hardware_concurrency', required: copy.value.no, desc: 'CPU 线程数来源与手动值' },
    { name: 'firefox.fingerprint.webrtc.mode / local_ip / public_ip', required: copy.value.no, desc: 'WebRTC 来源与手动 IP' },
    { name: 'firefox.fingerprint.load_webrtc_block_extension', required: copy.value.no, desc: '是否附带内置 WebRTC 屏蔽扩展' },
    { name: 'firefox.fingerprint.extra_fields[]', required: copy.value.no, desc: '额外写入指纹文件的字段，结构为 { key, value }' },
    { name: 'firefox.fingerprint_file_path', required: copy.value.no, desc: '自定义指纹文件路径，留空就写到当前配置目录' },
    { name: 'firefox.startup.window_size', required: copy.value.no, desc: '窗口大小，例如 1600,900' },
    { name: 'firefox.startup.open_urls[]', required: copy.value.no, desc: '启动后自动打开的网址列表' },
    { name: 'firefox.launch_args[]', required: copy.value.no, desc: '额外启动参数列表' },
    { name: 'firefox.disabled_global_extension_ids[]', required: copy.value.no, desc: '只对当前配置禁用的全局 Firefox 扩展 id 列表' },
  ]
})

const endpoints = computed(() => [
  {
    method: 'GET',
    path: '/health',
    title: copy.value.endpoints.healthTitle,
    desc: copy.value.endpoints.healthDesc,
    params: [authParam.value],
    request: `curl -H "X-API-Key: ${apiKey.value}" "${baseUrl.value}/health"`,
    response: JSON.stringify({ status: 'ok' }, null, 2),
  },
  {
    method: 'GET',
    path: '/profiles',
    title: copy.value.endpoints.listTitle,
    desc: copy.value.endpoints.listDesc,
    params: [authParam.value],
    request: `curl -H "X-API-Key: ${apiKey.value}" "${baseUrl.value}/profiles"`,
    response: JSON.stringify([
      {
        id: profileId.value,
        name: 'Example Profile',
        engine: 'chrome',
        status: 'stopped',
        port: null,
        runtime: null,
      },
    ], null, 2),
  },
  {
    method: 'POST',
    path: '/profiles',
    title: copy.value.endpoints.createTitle,
    desc: copy.value.endpoints.createDesc,
    params: [
      authParam.value,
      { name: 'id', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Profile id, omit to create a new one' : '配置 id，创建新配置时可以不传' },
      { name: 'name', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Profile name, auto-numbered when empty' : '配置名称，留空会自动按序号生成' },
      { name: 'group / remark', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Optional group and remark fields' : '可选分组和备注' },
      { name: 'engine', position: copy.value.body, required: copy.value.yes, desc: 'chrome / firefox' },
      { name: 'proxy', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Proxy object: type, host, port, username, password' : '代理对象，包含 type、host、port、username、password' },
      { name: 'storage.root_dir', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Custom user-data root for this profile' : '当前配置单独使用的用户目录根路径' },
      { name: 'chrome.*', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Chrome fingerprint, startup, args and extension override fields listed below' : 'Chrome 的指纹、启动参数、扩展禁用字段见下方完整字段表' },
      { name: 'firefox.*', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Firefox fingerprint, startup, args and extension override fields listed below' : 'Firefox 的指纹、启动参数、扩展禁用字段见下方完整字段表' },
    ],
    request: `curl -X POST "${baseUrl.value}/profiles" \\
  -H "X-API-Key: ${apiKey.value}" \\
  -H "Content-Type: application/json" \\
  -d "{\\"name\\":\\"Test Chrome\\",\\"engine\\":\\"chrome\\",\\"proxy\\":{\\"type\\":\\"none\\"}}"`,
    response: JSON.stringify({
      id: profileId.value,
      name: 'Test Chrome',
      engine: 'chrome',
      status: 'stopped',
    }, null, 2),
  },
  {
    method: 'POST',
    path: '/profiles/{profile_id}/start',
    title: copy.value.endpoints.startTitle,
    desc: copy.value.endpoints.startDesc,
    params: [
      authParam.value,
      { name: 'profile_id', position: copy.value.path, required: copy.value.yes, desc: locale.value === 'en-US' ? 'The profile id returned by GET /profiles' : 'GET /profiles 返回的配置 id' },
    ],
    request: `curl -X POST -H "X-API-Key: ${apiKey.value}" "${baseUrl.value}/profiles/${profileId.value}/start"`,
    response: JSON.stringify({
      id: profileId.value,
      engine: 'chrome',
      status: 'running',
      port: 9222,
      debug_port: 9222,
      debug_url: 'http://127.0.0.1:9222',
      marionette_port: 2828,
      selenium_port: 2828,
      runtime: {
        remote_debugging_port: 9222,
        marionette_port: 2828,
        resolved_ip: '203.0.113.10',
        resolved_timezone: 'Asia/Tokyo',
        resolved_language: 'ja-JP',
      },
    }, null, 2),
  },
  {
    method: 'POST',
    path: '/profiles/{profile_id}/stop',
    title: copy.value.endpoints.stopTitle,
    desc: copy.value.endpoints.stopDesc,
    params: [
      authParam.value,
      { name: 'profile_id', position: copy.value.path, required: copy.value.yes, desc: locale.value === 'en-US' ? 'The profile id to stop' : '要停止的配置 id' },
    ],
    request: `curl -X POST -H "X-API-Key: ${apiKey.value}" "${baseUrl.value}/profiles/${profileId.value}/stop"`,
    response: JSON.stringify({ id: profileId.value, status: 'stopped', port: null }, null, 2),
  },
  {
    method: 'DELETE',
    path: '/profiles/{profile_id}',
    title: copy.value.endpoints.deleteTitle,
    desc: copy.value.endpoints.deleteDesc,
    params: [
      authParam.value,
      { name: 'profile_id', position: copy.value.path, required: copy.value.yes, desc: locale.value === 'en-US' ? 'The profile id to delete' : '要删除的配置 id' },
    ],
    request: `curl -X DELETE -H "X-API-Key: ${apiKey.value}" "${baseUrl.value}/profiles/${profileId.value}"`,
    response: JSON.stringify({ ok: true }, null, 2),
  },
  {
    method: 'DELETE',
    path: '/profiles',
    title: locale.value === 'en-US' ? 'Delete a profile by name' : '按名称删除浏览器配置',
    desc: locale.value === 'en-US'
      ? 'Deletes the first profile matching the given name, so keep names unique. Returns 404 when nothing matches.'
      : '按名称删除配置，删除第一个匹配项，请自行保证名称唯一；找不到时返回 404。',
    params: [
      authParam.value,
      { name: 'profile_name', position: copy.value.body, required: copy.value.yes, desc: locale.value === 'en-US' ? 'Name of the profile to delete' : '要删除的配置名称' },
    ],
    request: `curl -X DELETE "${baseUrl.value}/profiles" \\
  -H "X-API-Key: ${apiKey.value}" \\
  -H "Content-Type: application/json" \\
  -d "{\\"profile_name\\":\\"Test Chrome\\"}"`,
    response: JSON.stringify({ ok: true }, null, 2),
  },
  {
    method: 'POST',
    path: '/profiles/create-and-start',
    title: locale.value === 'en-US' ? 'Create a profile and start it' : '创建配置并启动',
    desc: locale.value === 'en-US'
      ? 'Creates a profile from task_id (proxy optional — omit for a direct connection), starts it, and returns debug_url (the CDP WebSocket proxy). Returns 409 when the task id already exists.'
      : '用 task_id 创建配置并立即启动（proxy 可选，省略即直连），返回 debug_url（CDP WebSocket 代理地址）；同名任务已存在时返回 409。',
    params: [
      authParam.value,
      { name: 'task_id', position: copy.value.body, required: copy.value.yes, desc: locale.value === 'en-US' ? 'Unique task id, also used as the profile name' : '唯一任务标识，同时作为配置名称' },
      { name: 'proxy', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Proxy URL string, e.g. http://user:pass@host:port. Omit for a direct connection.' : '代理 URL 字符串，如 http://user:pass@host:port；省略即直连不使用代理。' },
      { name: 'engine', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'chrome / firefox, defaults to chrome' : 'chrome / firefox，默认 chrome' },
    ],
    request: `curl -X POST "${baseUrl.value}/profiles/create-and-start" \\
  -H "X-API-Key: ${apiKey.value}" \\
  -H "Content-Type: application/json" \\
  -d "{\\"task_id\\":\\"task-001\\",\\"proxy\\":\\"http://user:pass@127.0.0.1:7890\\",\\"engine\\":\\"chrome\\"}"`,
    response: JSON.stringify({
      id: profileId.value,
      name: 'task-001',
      engine: 'chrome',
      status: 'running',
      port: 9222,
      debug_url: `ws://127.0.0.1:8000/ws/cdp/${profileId.value}`,
    }, null, 2),
  },
  {
    method: 'GET',
    path: '/settings',
    title: copy.value.endpoints.settingsTitle,
    desc: copy.value.endpoints.settingsDesc,
    params: [authParam.value],
    request: `curl -H "X-API-Key: ${apiKey.value}" "${baseUrl.value}/settings"`,
    response: JSON.stringify({ user_data_root: 'D:\\\\BrowserData', theme_mode: 'system' }, null, 2),
  },
  {
    method: 'GET',
    path: '/saved-proxies',
    title: copy.value.endpoints.proxiesTitle,
    desc: copy.value.endpoints.proxiesDesc,
    params: [authParam.value],
    request: `curl -H "X-API-Key: ${apiKey.value}" "${baseUrl.value}/saved-proxies"`,
    response: JSON.stringify([{ id: 'proxy_id', name: 'US Proxy', type: 'http', host: '127.0.0.1', port: 7890 }], null, 2),
  },
  {
    method: 'GET',
    path: '/extensions?engine=chrome',
    title: locale.value === 'en-US' ? 'List managed extensions' : '获取已上传扩展',
    desc: locale.value === 'en-US'
      ? 'Returns globally managed extensions. Use engine=chrome or engine=firefox to filter.'
      : '返回全局扩展列表，可用 engine=chrome 或 engine=firefox 过滤。',
    params: [
      authParam.value,
      { name: 'engine', position: copy.value.query, required: copy.value.no, desc: locale.value === 'en-US' ? 'Optional query: chrome / firefox' : '可选查询参数：chrome / firefox' },
    ],
    request: `curl -H "X-API-Key: ${apiKey.value}" "${baseUrl.value}/extensions?engine=chrome"`,
    response: JSON.stringify([{ id: 'ext_id', engine: 'chrome', name: 'My Extension', enabled: true }], null, 2),
  },
  {
    method: 'PUT',
    path: '/extensions/{extension_id}',
    title: locale.value === 'en-US' ? 'Enable or disable an extension' : '启用或停用扩展',
    desc: locale.value === 'en-US'
      ? 'Updates the global extension state. Use enabled=false to stop loading it for all profiles.'
      : '更新全局扩展状态，enabled=false 后所有配置启动时都不会再自动加载它。',
    params: [
      authParam.value,
      { name: 'extension_id', position: copy.value.path, required: copy.value.yes, desc: locale.value === 'en-US' ? 'Extension id returned by GET /extensions' : 'GET /extensions 返回的扩展 id' },
      { name: 'enabled', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'true or false' : 'true 或 false' },
      { name: 'name', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Optional display name' : '可选显示名称' },
    ],
    request: `curl -X PUT "${baseUrl.value}/extensions/ext_id" \\
  -H "X-API-Key: ${apiKey.value}" \\
  -H "Content-Type: application/json" \\
  -d "{\\"enabled\\":false}"`,
    response: JSON.stringify({ id: 'ext_id', engine: 'chrome', name: 'My Extension', enabled: false }, null, 2),
  },
  {
    method: 'DELETE',
    path: '/extensions/{extension_id}',
    title: locale.value === 'en-US' ? 'Delete an extension' : '删除扩展',
    desc: locale.value === 'en-US'
      ? 'Removes a globally managed extension. Returns 404 when the id does not exist.'
      : '删除一个全局扩展，id 不存在时返回 404。',
    params: [
      authParam.value,
      { name: 'extension_id', position: copy.value.path, required: copy.value.yes, desc: locale.value === 'en-US' ? 'Extension id returned by GET /extensions' : 'GET /extensions 返回的扩展 id' },
    ],
    request: `curl -X DELETE -H "X-API-Key: ${apiKey.value}" "${baseUrl.value}/extensions/ext_id"`,
    response: JSON.stringify({ ok: true }, null, 2),
  },
  {
    method: 'POST',
    path: '/proxy/test',
    title: copy.value.endpoints.proxyTestTitle,
    desc: copy.value.endpoints.proxyTestDesc,
    params: [
      authParam.value,
      { name: 'type', position: copy.value.body, required: copy.value.yes, desc: 'none / http / https / socks5' },
      { name: 'host', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Proxy host, required when type is not none' : '代理主机，非直连时必填' },
      { name: 'port', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Proxy port, required when type is not none' : '代理端口，非直连时必填' },
      { name: 'username / password', position: copy.value.body, required: copy.value.no, desc: locale.value === 'en-US' ? 'Proxy auth fields' : '代理账号密码' },
    ],
    request: `curl -X POST "${baseUrl.value}/proxy/test" \\
  -H "X-API-Key: ${apiKey.value}" \\
  -H "Content-Type: application/json" \\
  -d "{\\"type\\":\\"http\\",\\"host\\":\\"127.0.0.1\\",\\"port\\":7890}"`,
    response: JSON.stringify({ ok: true, data: { ip: '203.0.113.10', language: 'ja-JP', timezone: 'Asia/Tokyo' } }, null, 2),
  },
  {
    method: 'POST',
    path: '/proxy/check-ip',
    title: locale.value === 'en-US' ? 'Check proxy IP quality' : '检测代理 IP 质量',
    desc: locale.value === 'en-US'
      ? 'Resolves geo info for a proxy URL string: IP, country, city, timezone, and whether it is a datacenter IP.'
      : '解析代理 URL 字符串的地理信息：IP、国家、城市、时区，以及是否数据中心 IP。',
    params: [
      authParam.value,
      { name: 'proxy', position: copy.value.body, required: copy.value.yes, desc: locale.value === 'en-US' ? 'Proxy URL string, e.g. http://user:pass@host:port' : '代理 URL 字符串，如 http://user:pass@host:port' },
    ],
    request: `curl -X POST "${baseUrl.value}/proxy/check-ip" \\
  -H "X-API-Key: ${apiKey.value}" \\
  -H "Content-Type: application/json" \\
  -d "{\\"proxy\\":\\"http://user:pass@127.0.0.1:7890\\"}"`,
    response: JSON.stringify({
      ipAddress: '203.0.113.10',
      country: 'Japan',
      countryCode: 'JP',
      city: 'Tokyo',
      lat: 35.68,
      lon: 139.69,
      timezone: 'Asia/Tokyo',
      isDataCenter: false,
    }, null, 2),
  },
])

const chromeProfileExample = computed(() => `{
  "name": "JP Chrome",
  "engine": "chrome",
  "proxy": {
    "type": "http",
    "host": "127.0.0.1",
    "port": 7890,
    "username": "",
    "password": ""
  },
  "storage": {
    "root_dir": "D:\\\\BrowserData"
  },
  "chrome": {
    "fingerprint": {
      "seed": 183927364,
      "auto_timezone": true,
      "language": "",
      "accept_language": "",
      "timezone": "",
      "platform": "windows",
      "hardware_concurrency_mode": "random",
      "hardware_concurrency": null,
      "disable_spoofing": ["canvas", "gpu"]
    },
    "startup": {
      "window_size": "1600,900",
      "open_urls": ["https://browserleaks.com/client-hints"]
    },
    "launch_args": ["--disable-gpu"],
    "disabled_global_extension_ids": []
  }
}`)

const firefoxProfileExample = computed(() => `{
  "name": "US Firefox",
  "engine": "firefox",
  "proxy": {
    "type": "socks5",
    "host": "127.0.0.1",
    "port": 10808,
    "username": "",
    "password": ""
  },
  "firefox": {
    "fingerprint": {
      "auto_timezone": true,
      "language": "",
      "timezone": "",
      "font_system": "windows",
      "screen": {
        "mode": "auto",
        "width": null,
        "height": null
      },
      "webgl": {
        "mode": "random",
        "vendor": "",
        "renderer": "",
        "version": "",
        "glsl_version": "",
        "unmasked_vendor": "",
        "unmasked_renderer": "",
        "max_texture_size": null,
        "max_cube_map_texture_size": null,
        "max_texture_image_units": null,
        "max_vertex_attribs": null,
        "aliased_point_size_max": null,
        "max_viewport_dim": null
      },
      "hardware_concurrency_mode": "random",
      "hardware_concurrency": null,
      "webrtc": {
        "mode": "random",
        "local_ip": "",
        "public_ip": ""
      },
      "load_webrtc_block_extension": true,
      "extra_fields": []
    },
    "fingerprint_file_path": "",
    "startup": {
      "window_size": "1500,900",
      "open_urls": ["https://browserleaks.com/javascript"]
    },
    "launch_args": ["--private-window"],
    "disabled_global_extension_ids": []
  }
}`)

const chromeAutomationExample = computed(() => `import requests
from patchright.sync_api import sync_playwright

BASE_URL = "${baseUrl.value}"
API_KEY = "${apiKey.value}"
PROFILE_ID = "${profileId.value}"

headers = {"X-API-Key": API_KEY}
result = requests.post(f"{BASE_URL}/profiles/{PROFILE_ID}/start", headers=headers).json()
port = result["port"]

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://browserleaks.com/client-hints")
    print(page.title())`)

const firefoxAutomationExample = computed(() => `import requests
from ruyipage import launch

BASE_URL = "${baseUrl.value}"
API_KEY = "${apiKey.value}"
PROFILE_ID = "${profileId.value}"

headers = {"X-API-Key": API_KEY}
result = requests.post(f"{BASE_URL}/profiles/{PROFILE_ID}/start", headers=headers).json()
port = result["port"]

page = launch(
    port=port,
)
page.goto("https://browserleaks.com/javascript")
print(page.title)

# Selenium / Java uses the returned selenium_port.
# Start geckodriver with:
# geckodriver --connect-existing --marionette-port <selenium_port>`)

onMounted(async () => {
  if (!store.apiInfo) {
    await store.refreshApiInfo()
  }
  if (!store.profiles?.length) {
    await store.refreshProfiles()
  }
})

function methodTag(method) {
  if (method === 'GET') return 'success'
  if (method === 'POST') return 'primary'
  if (method === 'DELETE') return 'danger'
  return 'info'
}

async function openUrl(url) {
  try {
    await api.post('/api/system/open-url', { url })
  } catch (error) {
    ElMessage.error(error.message || '打开失败')
  }
}
</script>
