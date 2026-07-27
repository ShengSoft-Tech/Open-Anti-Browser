import test from 'node:test'
import assert from 'node:assert/strict'
import { isFirefoxEngineAvailable, visibleEngineOptions, isEngineSelectorLocked } from './capabilitiesGating.js'

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
