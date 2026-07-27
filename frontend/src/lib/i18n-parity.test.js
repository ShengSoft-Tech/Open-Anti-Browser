import test from 'node:test'
import assert from 'node:assert/strict'
import zhCN from '../i18n/zh-CN.js'
import enUS from '../i18n/en-US.js'

// 递归把嵌套字典拍平成完整点分路径的 key 数组（叶子为止，数组值按叶子处理）。
function flattenKeys(obj, prefix = '') {
  const keys = []
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      keys.push(...flattenKeys(value, path))
    } else {
      keys.push(path)
    }
  }
  return keys
}

// 拍平成 { path: value } 映射，方便按路径取叶子值。
function flattenEntries(obj, prefix = '') {
  const entries = {}
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(entries, flattenEntries(value, path))
    } else {
      entries[path] = value
    }
  }
  return entries
}

test('zh-CN and en-US locale key sets are mutual subsets (parity)', () => {
  const zhKeys = new Set(flattenKeys(zhCN))
  const enKeys = new Set(flattenKeys(enUS))

  const missingInEn = [...zhKeys].filter(key => !enKeys.has(key)).sort()
  const missingInZh = [...enKeys].filter(key => !zhKeys.has(key)).sort()

  assert.deepEqual(missingInEn, [], `en-US.js missing keys present in zh-CN.js: ${missingInEn.join(', ')}`)
  assert.deepEqual(missingInZh, [], `zh-CN.js missing keys present in en-US.js: ${missingInZh.join(', ')}`)
})

test('every leaf value in both locales is a non-empty trimmed string', () => {
  const zhEntries = flattenEntries(zhCN)
  const enEntries = flattenEntries(enUS)

  const badZh = Object.entries(zhEntries)
    .filter(([, value]) => typeof value !== 'string' || value.trim().length === 0)
    .map(([path]) => path)
  const badEn = Object.entries(enEntries)
    .filter(([, value]) => typeof value !== 'string' || value.trim().length === 0)
    .map(([path]) => path)

  assert.deepEqual(badZh, [], `zh-CN.js has empty/non-string leaf values at: ${badZh.join(', ')}`)
  assert.deepEqual(badEn, [], `en-US.js has empty/non-string leaf values at: ${badEn.join(', ')}`)
})

test('zh-CN and en-US have the same non-zero number of leaf keys', () => {
  const zhCount = flattenKeys(zhCN).length
  const enCount = flattenKeys(enUS).length

  assert.ok(zhCount > 0, 'zh-CN.js has zero leaf keys')
  assert.equal(zhCount, enCount, `leaf count mismatch: zh-CN has ${zhCount}, en-US has ${enCount}`)
})
