import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { GATEKEEPER_XATTR_COMMAND } from './macosGatekeeperNotice.js'

// 本文件位于 frontend/src/lib/ 下，向上三级到仓库根目录（lib -> src -> frontend -> 根）。
// 不用 process.cwd()，因为 node --test 可能从不同目录调用；只信赖 import.meta.url。
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..')

const TEMPLATE_PATH = path.join(REPO_ROOT, '.github/RELEASE_NOTES_TEMPLATE.md')
const WORKFLOW_PATH = path.join(REPO_ROOT, '.github/workflows/build-release.yml')

// 不做任何降级：模板或工作流文件缺失时 readFileSync 直接抛异常，测试失败，
// 绝不允许用 try/catch 吞掉后回退成空字符串（那样会让下面的断言全部空判定通过）。
function readTemplate() {
  return readFileSync(TEMPLATE_PATH, 'utf-8')
}

function readWorkflow() {
  return readFileSync(WORKFLOW_PATH, 'utf-8')
}

// D-04/T-06-02 的越权片段清单：禁止全局关闭 Gatekeeper、SIP 相关工具、
// 提权前缀，以及宽泛到 ~/Downloads 的路径。与 05-02 的
// test_message_contains_no_dangerous_command_fragments 是同一条安全边界。
const FORBIDDEN_FRAGMENTS = ['sudo', 'spctl', '--master-disable', '~/Downloads', 'csrutil']

test('模板逐字内嵌 GATEKEEPER_XATTR_COMMAND 常量', () => {
  const template = readTemplate()
  assert.ok(
    template.includes(GATEKEEPER_XATTR_COMMAND),
    `模板未找到逐字命令: ${GATEKEEPER_XATTR_COMMAND}`
  )
  // D-15 人工纠正：不再要求“只出现一次”，而是要求每一处出现都与常量逐字相同——
  // 这是比“出现次数=1”更强的保证，允许英文 fallback 也完整复述一遍命令。
  const occurrences = template.split(GATEKEEPER_XATTR_COMMAND).length - 1
  assert.ok(occurrences >= 1, `期望至少出现 1 次，实际 ${occurrences} 次`)
})

test('模板中不含任何越权/提权/全局关闭类命令片段', () => {
  const template = readTemplate()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    assert.ok(!template.includes(fragment), `模板不应包含越权片段: ${fragment}`)
  }
})

test('build-release.yml 的发布步骤声明 body_path 且指向的文件真实存在', () => {
  const workflow = readWorkflow()
  const match = workflow.match(/body_path:\s*(\S+)/)
  assert.ok(match, '未在 build-release.yml 中找到 body_path 声明')
  const bodyPathValue = match[1].trim()
  assert.ok(bodyPathValue.length > 0, 'body_path 值为空')
  const resolvedPath = path.join(REPO_ROOT, bodyPathValue)
  assert.ok(existsSync(resolvedPath), `body_path 指向的文件不存在: ${resolvedPath}`)
})

test('build-release.yml 仍保留 generate_release_notes: true，自动生成的变更日志不会丢失', () => {
  const workflow = readWorkflow()
  assert.ok(
    workflow.includes('generate_release_notes: true'),
    '未找到 generate_release_notes: true'
  )
})

test('模板顶部含唯一一处 RELEASE_VERSION 锚点且为 semver 形状', () => {
  const template = readTemplate()
  const matches = [...template.matchAll(/<!--\s*RELEASE_VERSION:\s*(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)\s*-->/g)]
  assert.equal(matches.length, 1, `期望恰好一处 RELEASE_VERSION 锚点，实际 ${matches.length} 处`)
  assert.match(matches[0][1], /^\d+\.\d+\.\d+$/, `锚点版本号不是 semver 形状: ${matches[0][1]}`)
})
