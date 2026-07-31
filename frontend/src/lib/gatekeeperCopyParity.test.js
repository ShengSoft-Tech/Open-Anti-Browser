import test from 'node:test'
import assert from 'node:assert/strict'
import zhCN from '../i18n/zh-CN.js'
import enUS from '../i18n/en-US.js'

// D-02（06-03）：锁定首启放行提示的 gatekeeper.step1-step4 措辞顺序，防止未来编辑
// 悄悄把"再双击一次"这条已在真机测得有效的主路径又降级回"系统设置"优先。
// 直接 import 两份 locale 模块并断言字符串值，写法与 i18n-parity.test.js 一致。

const FORBIDDEN_FRAGMENTS = ['sudo', 'spctl', '--master-disable', 'csrutil', '~/Downloads']

// 系统设置这条 fallback 的中英文特征词，用来判断某个 step 是否提到了它。
const SETTINGS_MARKERS = ['系统设置', 'System Settings']

function includesAny(value, markers) {
  return markers.some(marker => value.includes(marker))
}

test('gatekeeper.step1 describes double-clicking the app again as the primary action (both locales)', () => {
  assert.match(zhCN.gatekeeper.step1, /双击/, 'zh-CN step1 应提到"双击"')
  assert.match(zhCN.gatekeeper.step1, /再|第二次|重新/, 'zh-CN step1 应提到"再次/第二次"这一动作')
  assert.match(enUS.gatekeeper.step1, /double-click/i, 'en-US step1 should mention double-clicking')
  assert.match(enUS.gatekeeper.step1, /again/i, 'en-US step1 should mention doing it again')
})

test('gatekeeper.step1 does not mention the System Settings fallback in either locale', () => {
  assert.ok(
    !includesAny(zhCN.gatekeeper.step1, SETTINGS_MARKERS),
    'zh-CN step1 不应提及系统设置这条 fallback'
  )
  assert.ok(
    !includesAny(enUS.gatekeeper.step1, SETTINGS_MARKERS),
    'en-US step1 should not mention the System Settings fallback'
  )
})

test('gatekeeper.step2 is the System Settings -> Privacy & Security fallback (both locales)', () => {
  assert.ok(
    includesAny(zhCN.gatekeeper.step2, SETTINGS_MARKERS),
    'zh-CN step2 应描述"系统设置"这条 fallback'
  )
  assert.match(zhCN.gatekeeper.step2, /隐私与安全性/, 'zh-CN step2 应提到"隐私与安全性"')
  assert.ok(
    includesAny(enUS.gatekeeper.step2, SETTINGS_MARKERS),
    'en-US step2 should describe the System Settings fallback'
  )
  assert.match(enUS.gatekeeper.step2, /Privacy (&|and) Security/i, 'en-US step2 should mention Privacy & Security')
})

test('neither locale\'s gatekeeper block contains a forbidden privilege-escalation fragment', () => {
  for (const locale of [{ name: 'zh-CN', values: zhCN.gatekeeper }, { name: 'en-US', values: enUS.gatekeeper }]) {
    for (const [key, value] of Object.entries(locale.values)) {
      for (const fragment of FORBIDDEN_FRAGMENTS) {
        assert.ok(
          !value.includes(fragment),
          `${locale.name}.gatekeeper.${key} 不应包含被禁止的片段 "${fragment}"，实际值："${value}"`
        )
      }
    }
  }
})

test('gatekeeper.step4 leads into the command block without restating GATEKEEPER_XATTR_COMMAND', () => {
  assert.ok(
    !zhCN.gatekeeper.step4.includes('xattr'),
    'zh-CN step4 不应逐字复述终端命令，命令块已由 buildGatekeeperNoticeHtml 单独渲染'
  )
  assert.ok(
    !enUS.gatekeeper.step4.includes('xattr'),
    'en-US step4 should not restate the terminal command literally'
  )
})
