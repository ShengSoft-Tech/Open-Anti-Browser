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

// 分组管理的 Firefox 计数列按需显示（UAT A8 决议）。
// 该列报告的是「现有配置构成」而非「可创建的引擎」，所以不受 UI-01 的隐藏要求约束；
// 但对没有任何 firefox 配置的全新 macOS 用户，它是一个恒为 0 的噪音列。
// 折中：引擎可用（Windows）时始终显示；不可用时，仅当确实存在既有 firefox 配置才显示，
// 以免「配置数」与「Chrome」对不上而少掉的条目无从解释（D-01「不删不藏」）。
export function shouldShowFirefoxColumn(capabilities, groups) {
  if (isFirefoxEngineAvailable(capabilities)) {
    return true
  }
  if (!Array.isArray(groups)) {
    return false
  }
  return groups.some(group => Number(group?.firefox) > 0)
}

export function getWindowFeatureGate(capabilities, feature) {
  const featureCapability = capabilities?.window?.[feature]
  const disabled = featureCapability?.available === false
  const rawReason = featureCapability?.reason
  const reason = typeof rawReason === 'string' && rawReason ? rawReason : ''
  return { disabled, reason }
}
