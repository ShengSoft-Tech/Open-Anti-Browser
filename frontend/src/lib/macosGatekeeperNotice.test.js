import test, { beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import {
  GATEKEEPER_NOTICE_KEY,
  GATEKEEPER_XATTR_COMMAND,
  hasSeenGatekeeperNotice,
  markGatekeeperNoticeSeen,
  shouldShowGatekeeperNotice,
  buildGatekeeperNoticeHtml,
} from './macosGatekeeperNotice.js'

// Node 的 node:test 环境没有浏览器 localStorage，这里用一个最小 Map 桩顶替，
// 并额外提供一个「所有方法都抛异常」的桩用于验证降级路径。
function createStorageStub() {
  const store = new Map()
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null
    },
    setItem(key, value) {
      store.set(key, String(value))
    },
    removeItem(key) {
      store.delete(key)
    },
    _store: store,
  }
}

function createThrowingStorageStub() {
  return {
    getItem() {
      throw new Error('localStorage unavailable')
    },
    setItem() {
      throw new Error('localStorage unavailable')
    },
    removeItem() {
      throw new Error('localStorage unavailable')
    },
  }
}

beforeEach(() => {
  globalThis.localStorage = createStorageStub()
})

test('hasSeenGatekeeperNotice returns false when storage is empty', () => {
  assert.equal(hasSeenGatekeeperNotice(), false)
})

test('hasSeenGatekeeperNotice returns false when the key exists but is an empty string', () => {
  globalThis.localStorage.setItem(GATEKEEPER_NOTICE_KEY, '')
  assert.equal(hasSeenGatekeeperNotice(), false)
})

test('markGatekeeperNoticeSeen makes hasSeenGatekeeperNotice return true', () => {
  markGatekeeperNoticeSeen()
  assert.equal(hasSeenGatekeeperNotice(), true)
})

test('markGatekeeperNoticeSeen is idempotent across repeated calls', () => {
  markGatekeeperNoticeSeen()
  markGatekeeperNoticeSeen()
  markGatekeeperNoticeSeen()
  assert.equal(hasSeenGatekeeperNotice(), true)
  assert.equal(globalThis.localStorage._store.size, 1)
  assert.equal(globalThis.localStorage.getItem(GATEKEEPER_NOTICE_KEY), '1')
})

test('all storage functions degrade silently when localStorage throws on every call', () => {
  globalThis.localStorage = createThrowingStorageStub()
  assert.doesNotThrow(() => {
    assert.equal(hasSeenGatekeeperNotice(), false)
  })
  assert.doesNotThrow(() => {
    markGatekeeperNoticeSeen()
  })
  assert.doesNotThrow(() => {
    shouldShowGatekeeperNotice({ platform: 'darwin' })
  })
})

test('shouldShowGatekeeperNotice is true on darwin before marking seen, false after', () => {
  assert.equal(shouldShowGatekeeperNotice({ platform: 'darwin' }), true)
  markGatekeeperNoticeSeen()
  assert.equal(shouldShowGatekeeperNotice({ platform: 'darwin' }), false)
})

test('shouldShowGatekeeperNotice is false for non-darwin/empty/undefined/null capabilities and never throws', () => {
  assert.equal(shouldShowGatekeeperNotice({ platform: 'win32' }), false)
  assert.equal(shouldShowGatekeeperNotice({}), false)
  assert.equal(shouldShowGatekeeperNotice(undefined), false)
  assert.equal(shouldShowGatekeeperNotice(null), false)
})

test('GATEKEEPER_NOTICE_KEY is the expected independent value, distinct from the open-source notice key', () => {
  assert.equal(GATEKEEPER_NOTICE_KEY, 'oab:macos-gatekeeper-notice:v1')
  assert.notEqual(GATEKEEPER_NOTICE_KEY, 'oab:first-use-notice:v2')
})

test('buildGatekeeperNoticeHtml includes the verbatim xattr command and references all four step keys', () => {
  const html = buildGatekeeperNoticeHtml(key => key)
  assert.ok(html.includes(GATEKEEPER_XATTR_COMMAND))
  assert.ok(html.includes('gatekeeper.step1'))
  assert.ok(html.includes('gatekeeper.step2'))
  assert.ok(html.includes('gatekeeper.step3'))
  assert.ok(html.includes('gatekeeper.step4'))
})

test('GATEKEEPER_XATTR_COMMAND targets a single .app bundle without sudo or spctl', () => {
  assert.ok(GATEKEEPER_XATTR_COMMAND.startsWith('xattr -dr com.apple.quarantine '))
  const targetPath = GATEKEEPER_XATTR_COMMAND.replace('xattr -dr com.apple.quarantine ', '')
  assert.ok(targetPath.endsWith('.app'))
  assert.ok(!GATEKEEPER_XATTR_COMMAND.includes('spctl'))
  assert.ok(!GATEKEEPER_XATTR_COMMAND.includes('sudo'))
})

test('buildGatekeeperNoticeHtml is pure: repeated calls return the same string with no storage side effects', () => {
  const before = JSON.stringify([...globalThis.localStorage._store.entries()])
  const first = buildGatekeeperNoticeHtml(key => key)
  const second = buildGatekeeperNoticeHtml(key => key)
  const after = JSON.stringify([...globalThis.localStorage._store.entries()])
  assert.equal(first, second)
  assert.equal(before, after)
})
