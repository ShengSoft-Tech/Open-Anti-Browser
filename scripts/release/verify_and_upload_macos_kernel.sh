#!/usr/bin/env bash
set -euo pipefail

# scripts/release/verify_and_upload_macos_kernel.sh
#
# macOS fingerprint-chromium 内核资产的「上传前把关 + 发布」脚本(KERNEL-01/02/03)。
# 对拿到的内核产物(zip 或已解压 .app)做:
#   1. 产物就绪化(全程 ditto,保 Framework 符号链接与 ad-hoc 签名)
#   2. 双二进制架构校验(launcher stub + Framework 二进制,均须匹配 --arch)
#   3. ad-hoc 签名存活校验(codesign,轻量 sanity check)
#   4. 本机 CDP 启动冒烟(arm64 原生 / x86_64 走 Rosetta 2)
# 通过后(非 --dry-run)用 gh release upload --clobber 幂等发布到 kernel-149.0.7827.114。
#
# 用法:
#   verify_and_upload_macos_kernel.sh [--dry-run] --arch <arm64|x86_64> <artifact-path>
#
# <artifact-path> 可为 .zip 文件,或已解压的 .app 目录(自测便利路径)。
# --dry-run 仅执行校验+冒烟,不触任何上传代码(不读 backend.config,不调用 gh)。

DRY_RUN=0
ARCH=""
ARTIFACT=""

usage() {
  echo "用法: $0 [--dry-run] --arch <arm64|x86_64> <artifact-path>" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --arch)
      ARCH="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      if [[ -z "$ARTIFACT" ]]; then
        ARTIFACT="$1"
        shift
      else
        echo "错误: 未知参数或多余的位置参数: $1" >&2
        usage
      fi
      ;;
  esac
done

if [[ "$ARCH" != "arm64" && "$ARCH" != "x86_64" ]]; then
  echo "错误: --arch 仅接受 arm64 或 x86_64,得到: [$ARCH]" >&2
  exit 1
fi

if [[ -z "$ARTIFACT" ]]; then
  echo "错误: 缺少 <artifact-path> 参数" >&2
  usage
fi

if [[ ! -e "$ARTIFACT" ]]; then
  echo "错误: artifact 路径不存在: $ARTIFACT" >&2
  exit 1
fi

echo "== 阶段 1/4: 产物就绪化(ditto)=="
SCRATCH="$(mktemp -d)"

cleanup() {
  rm -rf "$SCRATCH"
}
trap cleanup EXIT

if [[ "$ARTIFACT" == *.zip ]]; then
  echo "解压 zip: $ARTIFACT -> $SCRATCH"
  ditto -x -k "$ARTIFACT" "$SCRATCH" || { echo "错误: ditto 解压失败: $ARTIFACT" >&2; exit 1; }
elif [[ -d "$ARTIFACT" && "$ARTIFACT" == *.app ]]; then
  echo "输入为已解压 .app 目录,先 ditto 打包再 ditto 解压往返(自测便利路径,证明 Framework 符号链接经 ditto 往返被保留,Pitfall 2)"
  ROUNDTRIP_ZIP="$SCRATCH/roundtrip.zip"
  ditto -c -k --keepParent --sequesterRsrc "$ARTIFACT" "$ROUNDTRIP_ZIP" || { echo "错误: ditto 打包失败: $ARTIFACT" >&2; exit 1; }
  ditto -x -k "$ROUNDTRIP_ZIP" "$SCRATCH" || { echo "错误: ditto 解压失败: $ROUNDTRIP_ZIP" >&2; exit 1; }
  rm -f "$ROUNDTRIP_ZIP"
else
  echo "错误: <artifact-path> 必须是 .zip 文件或 .app 目录: $ARTIFACT" >&2
  exit 1
fi

APP="$(find "$SCRATCH" -maxdepth 2 -name '*.app' -print -quit)"
if [[ -z "$APP" ]]; then
  echo "错误: scratch 目录内未找到 .app bundle: $SCRATCH" >&2
  exit 1
fi
echo ".app bundle 就绪: $APP"

echo "== 阶段 2/4: 双二进制架构校验(KERNEL-03,Pitfall 1)=="
LAUNCHER="$APP/Contents/MacOS/Chromium"
FRAMEWORK="$APP/Contents/Frameworks/Chromium Framework.framework/Versions/Current/Chromium Framework"

for BIN in "$LAUNCHER" "$FRAMEWORK"; do
  if [[ ! -f "$BIN" ]]; then
    echo "ARCH 校验失败: 二进制缺失: $BIN" >&2
    exit 1
  fi
  FOUND_ARCH="$(lipo -archs "$BIN" 2>&1)" || { echo "ARCH 校验失败: lipo 执行失败于 $BIN: $FOUND_ARCH" >&2; exit 1; }
  echo "lipo -archs \"$BIN\" -> $FOUND_ARCH"
  if [[ "$FOUND_ARCH" != "$ARCH" ]]; then
    echo "ARCH 不匹配: $BIN 实际为 [$FOUND_ARCH],期望 [$ARCH]" >&2
    exit 1
  fi
done

echo "== 阶段 3/4: ad-hoc 签名存活校验(codesign)=="
CODESIGN_OUT="$(codesign -dv "$APP" 2>&1)" || { echo "错误: codesign 执行失败: $CODESIGN_OUT" >&2; exit 1; }
if ! grep -q "adhoc" <<<"$CODESIGN_OUT"; then
  echo "签名校验失败: 未检出 adhoc 标记" >&2
  echo "$CODESIGN_OUT" >&2
  exit 1
fi
if ! grep -q "linker-signed" <<<"$CODESIGN_OUT"; then
  echo "签名校验失败: 未检出 linker-signed 标记" >&2
  echo "$CODESIGN_OUT" >&2
  exit 1
fi
echo "签名校验通过: adhoc, linker-signed 均存活(ditto 往返未破坏签名)"

echo "== 阶段 4/4: 本机 CDP 启动冒烟(KERNEL-03)=="

# smoke_test: 拉起 launcher(x86_64 经 arch -x86_64 走 Rosetta 2),轮询 CDP /json/version。
# 重试预算按架构区分(architecture-dependent):
#   arm64   原生启动快 -> 短预算(约 15 次 x 1s ≈ 15s)
#   x86_64  Rosetta 首启 AOT 翻译慢 -> 长预算(约 30 次 x 2s ≈ 60s,Pitfall 4)
smoke_test() {
  local launcher="$1"
  local arch="$2"
  local profile_dir
  profile_dir="$(mktemp -d)"
  local port
  port="$(python3 -c 'import socket; s = socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')"

  local retries interval
  if [[ "$arch" == "x86_64" ]]; then
    retries=30
    interval=2
  else
    retries=15
    interval=1
  fi

  local -a launch_cmd
  if [[ "$arch" == "x86_64" ]]; then
    launch_cmd=(arch -x86_64 "$launcher")
  else
    launch_cmd=("$launcher")
  fi

  echo "冒烟启动: ${launch_cmd[*]} (port=$port, retries=$retries, interval=${interval}s)"
  "${launch_cmd[@]}" \
    --user-data-dir="$profile_dir" \
    --remote-debugging-port="$port" \
    --remote-allow-origins=* \
    --no-first-run \
    --no-default-browser-check \
    --password-store=basic \
    >/dev/null 2>&1 &
  local pid=$!

  local ok=0
  local i
  for (( i = 1; i <= retries; i++ )); do
    if curl -sf "http://127.0.0.1:${port}/json/version" 2>/dev/null | grep -q "149.0.7827.114"; then
      ok=1
      break
    fi
    sleep "$interval"
  done

  if [[ "$ok" -eq 1 ]]; then
    echo "CDP 冒烟通过: /json/version 响应含 149.0.7827.114"
  else
    echo "CDP 冒烟失败: 在 $(( retries * interval ))s 内未获得含 149.0.7827.114 的 /json/version 响应" >&2
  fi

  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  rm -rf "$profile_dir"

  if [[ "$ok" -ne 1 ]]; then
    exit 1
  fi
}

smoke_test "$LAUNCHER" "$ARCH"

echo "Verified OK: $APP ($ARCH, adhoc-signed)"
