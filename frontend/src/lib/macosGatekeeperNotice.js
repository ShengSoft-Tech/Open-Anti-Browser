// UI-04 首启放行提示的纯逻辑模块（D-04）。
// 与被 backend/_g.py 哈希锁定的 openSourceNotice.js 完全独立：独立文件、独立
// localStorage key，避免任何形式的修改触碰那份反篡改锁定资产。
// 本模块不引入任何 UI 组件库或 Vue 运行时依赖，以便被 node:test 直接 import 测试；
// 04-04（设置页重看按钮）与 04-05（App.vue 首启弹窗）两个消费方共用同一份文案构建函数。

export const GATEKEEPER_NOTICE_KEY = 'oab:macos-gatekeeper-notice:v1'

// 逐字终端命令：只限定到单个已安装的应用 bundle，不指向 ~/Downloads 或 /Applications
// 这类宽泛目录，也不引导用户全局关闭 Gatekeeper（不含 spctl，不含 sudo）。
export const GATEKEEPER_XATTR_COMMAND = 'xattr -dr com.apple.quarantine "/Applications/Open-Anti-Browser.app"'

export function hasSeenGatekeeperNotice() {
  try {
    return localStorage.getItem(GATEKEEPER_NOTICE_KEY) === '1'
  } catch {
    return false
  }
}

export function markGatekeeperNoticeSeen() {
  try {
    localStorage.setItem(GATEKEEPER_NOTICE_KEY, '1')
  } catch {
    // localStorage 不可用或配额已满时静默降级，不向上抛出，避免打断 App.vue 的 onMounted。
  }
}

export function shouldShowGatekeeperNotice(capabilities) {
  return capabilities?.platform === 'darwin' && !hasSeenGatekeeperNotice()
}

// 纯函数：不读写 localStorage，也不插入除开发者自撰 i18n 文案与本模块常量之外的
// 任何动态值——返回值会以 dangerouslyUseHTMLString 方式注入 DOM，插入动态值即构成 XSS 通路。
export function buildGatekeeperNoticeHtml(t) {
  return `
    <div class="gatekeeper-notice">
      <p>${t('gatekeeper.intro')}</p>
      <p class="gatekeeper-steps-title">${t('gatekeeper.stepsTitle')}</p>
      <ol>
        <li>${t('gatekeeper.step1')}</li>
        <li>${t('gatekeeper.step2')}</li>
        <li>${t('gatekeeper.step3')}</li>
        <li>${t('gatekeeper.step4')}</li>
      </ol>
      <p class="gatekeeper-command-title">${t('gatekeeper.commandTitle')}</p>
      <p><code>${GATEKEEPER_XATTR_COMMAND}</code></p>
      <p>${t('gatekeeper.commandHint')}</p>
      <p>${t('gatekeeper.settingsHint')}</p>
    </div>
  `
}
