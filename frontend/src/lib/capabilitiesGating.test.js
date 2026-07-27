import test from 'node:test'
import assert from 'node:assert/strict'
import {
  isFirefoxEngineAvailable,
  visibleEngineOptions,
  isEngineSelectorLocked,
  getWindowFeatureGate,
} from './capabilitiesGating.js'

const baseOptions = [
  { label: 'Chrome', value: 'chrome' },
  { label: 'Firefox', value: 'firefox' },
]

test('isFirefoxEngineAvailable returns true when capabilities say firefox is available', () => {
  assert.equal(isFirefoxEngineAvailable({ engines: { firefox: { available: true } } }), true)
})

test('isFirefoxEngineAvailable returns false when capabilities say firefox is unavailable', () => {
  assert.equal(isFirefoxEngineAvailable({ engines: { firefox: { available: false } } }), false)
})

test('isFirefoxEngineAvailable defaults to true for undefined/null/empty capabilities (no crash, Windows zero-regression)', () => {
  assert.equal(isFirefoxEngineAvailable(undefined), true)
  assert.equal(isFirefoxEngineAvailable(null), true)
  assert.equal(isFirefoxEngineAvailable({}), true)
})

test('visibleEngineOptions keeps both options when firefox is available', () => {
  const result = visibleEngineOptions(baseOptions, { engines: { firefox: { available: true } } }, 'chrome')
  assert.deepEqual(result, baseOptions)
})

test('visibleEngineOptions removes firefox but keeps chrome when firefox is unavailable', () => {
  const result = visibleEngineOptions(baseOptions, { engines: { firefox: { available: false } } }, 'chrome')
  assert.deepEqual(result, [{ label: 'Chrome', value: 'chrome' }])
})

test('visibleEngineOptions treats undefined/null/empty capabilities as available (both options present, no throw)', () => {
  assert.deepEqual(visibleEngineOptions(baseOptions, undefined, 'chrome'), baseOptions)
  assert.deepEqual(visibleEngineOptions(baseOptions, null, 'chrome'), baseOptions)
  assert.deepEqual(visibleEngineOptions(baseOptions, {}, 'chrome'), baseOptions)
})

test('visibleEngineOptions preserves relative order of remaining options after filtering (chrome not first)', () => {
  const options = [
    { label: 'Firefox', value: 'firefox' },
    { label: 'Chrome', value: 'chrome' },
    { label: 'Other', value: 'other' },
  ]
  const result = visibleEngineOptions(options, { engines: { firefox: { available: false } } }, 'chrome')
  assert.deepEqual(result, [
    { label: 'Chrome', value: 'chrome' },
    { label: 'Other', value: 'other' },
  ])
})

test('visibleEngineOptions is a pure function: repeated calls return equal results and do not mutate inputs', () => {
  const capabilities = { engines: { firefox: { available: false } } }
  const capabilitiesSnapshot = JSON.parse(JSON.stringify(capabilities))
  const optionsSnapshot = JSON.parse(JSON.stringify(baseOptions))

  const first = visibleEngineOptions(baseOptions, capabilities, 'chrome')
  const second = visibleEngineOptions(baseOptions, capabilities, 'chrome')

  assert.deepEqual(first, second)
  assert.deepEqual(baseOptions, optionsSnapshot)
  assert.deepEqual(capabilities, capabilitiesSnapshot)
})

test('visibleEngineOptions keeps the firefox option when currentEngine is firefox even if unavailable (no dangling selection)', () => {
  const result = visibleEngineOptions(baseOptions, { engines: { firefox: { available: false } } }, 'firefox')
  assert.deepEqual(result, baseOptions)
})

test('isEngineSelectorLocked is true when editing an existing firefox profile on a machine without firefox', () => {
  assert.equal(isEngineSelectorLocked({ engines: { firefox: { available: false } } }, 'firefox'), true)
})

test('isEngineSelectorLocked is false when current engine is chrome even if firefox is unavailable', () => {
  assert.equal(isEngineSelectorLocked({ engines: { firefox: { available: false } } }, 'chrome'), false)
})

test('isEngineSelectorLocked is false when firefox is available', () => {
  assert.equal(isEngineSelectorLocked({ engines: { firefox: { available: true } } }, 'firefox'), false)
})

test('isEngineSelectorLocked does not lock on undefined/null capabilities (unknown platform is not locked)', () => {
  assert.equal(isEngineSelectorLocked(undefined, 'firefox'), false)
  assert.equal(isEngineSelectorLocked(null, 'firefox'), false)
})

test('isEngineSelectorLocked is a pure function: repeated calls return equal results and do not mutate input capabilities', () => {
  const capabilities = { engines: { firefox: { available: false } } }
  const snapshot = JSON.parse(JSON.stringify(capabilities))

  const first = isEngineSelectorLocked(capabilities, 'firefox')
  const second = isEngineSelectorLocked(capabilities, 'firefox')

  assert.equal(first, second)
  assert.deepEqual(capabilities, snapshot)
})

test('getWindowFeatureGate returns disabled true with the backend reason verbatim when sync is unavailable', () => {
  const result = getWindowFeatureGate(
    { window: { sync: { available: false, reason: '窗口同步仅在 Windows 上可用' } } },
    'sync'
  )
  assert.deepEqual(result, { disabled: true, reason: '窗口同步仅在 Windows 上可用' })
})

test('getWindowFeatureGate returns disabled false and empty reason when arrange is available with a null reason', () => {
  const result = getWindowFeatureGate({ window: { arrange: { available: true, reason: null } } }, 'arrange')
  assert.deepEqual(result, { disabled: false, reason: '' })
})

test('getWindowFeatureGate defaults to not-disabled with empty reason for undefined/null/empty capabilities (no throw)', () => {
  assert.deepEqual(getWindowFeatureGate(undefined, 'sync'), { disabled: false, reason: '' })
  assert.deepEqual(getWindowFeatureGate(null, 'sync'), { disabled: false, reason: '' })
  assert.deepEqual(getWindowFeatureGate({}, 'sync'), { disabled: false, reason: '' })
})

test('getWindowFeatureGate stays disabled true with empty reason when available is false but reason is missing/empty', () => {
  assert.deepEqual(getWindowFeatureGate({ window: { sync: { available: false } } }, 'sync'), {
    disabled: true,
    reason: '',
  })
  assert.deepEqual(getWindowFeatureGate({ window: { sync: { available: false, reason: '' } } }, 'sync'), {
    disabled: true,
    reason: '',
  })
})

test('getWindowFeatureGate reads sync and arrange independently without cross-fallback', () => {
  const capabilities = {
    window: {
      sync: { available: false, reason: '窗口同步仅在 Windows 上可用' },
      arrange: { available: true, reason: null },
    },
  }
  assert.deepEqual(getWindowFeatureGate(capabilities, 'sync'), {
    disabled: true,
    reason: '窗口同步仅在 Windows 上可用',
  })
  assert.deepEqual(getWindowFeatureGate(capabilities, 'arrange'), { disabled: false, reason: '' })
})

test('getWindowFeatureGate is a pure function: repeated calls return equal results and do not mutate input capabilities', () => {
  const capabilities = { window: { sync: { available: false, reason: '窗口同步仅在 Windows 上可用' } } }
  const snapshot = JSON.parse(JSON.stringify(capabilities))

  const first = getWindowFeatureGate(capabilities, 'sync')
  const second = getWindowFeatureGate(capabilities, 'sync')

  assert.deepEqual(first, second)
  assert.deepEqual(capabilities, snapshot)
})
