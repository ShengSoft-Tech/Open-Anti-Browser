// 单一事实源(D-00):本 phase 所有平台门控判断都必须经过本模块，
// 任何组件都不得自行从浏览器 navigator 对象推导平台。
// capabilities 契约来自后端 `GET /api/bootstrap` 的 `data.capabilities`
// （参见 backend/browser_manager.py 的 get_platform_capabilities()）。

export function isFirefoxEngineAvailable(capabilities) {
  return capabilities?.engines?.firefox?.available !== false
}

export function visibleEngineOptions(baseOptions, capabilities, currentEngine) {
  const options = [...baseOptions]
  if (isFirefoxEngineAvailable(capabilities)) {
    return options
  }
  return options.filter(option => option.value !== 'firefox' || currentEngine === 'firefox')
}

export function isEngineSelectorLocked(capabilities, currentEngine) {
  return currentEngine === 'firefox' && !isFirefoxEngineAvailable(capabilities)
}

export function getWindowFeatureGate(capabilities, feature) {
  const featureCapability = capabilities?.window?.[feature]
  const disabled = featureCapability?.available === false
  const rawReason = featureCapability?.reason
  const reason = typeof rawReason === 'string' && rawReason ? rawReason : ''
  return { disabled, reason }
}
