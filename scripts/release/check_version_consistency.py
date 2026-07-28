#!/usr/bin/env python3
"""scripts/release/check_version_consistency.py

发布把关工具(D-08):在 CI 的 ``Resolve version`` 步骤里被调用,判定 tag /
``frontend/package.json`` / ``backend/main.py`` 三处版本号是否一致。

- tag 触发(``is_tag=True``):要求 tag(去掉一个前导 ``v``)与 package.json、
  main.py 三者全等。
- 手动 ``workflow_dispatch`` 触发(``is_tag=False``):没有 tag 可比,只要求
  package.json 与 main.py 两者相等,不参照传入的 ref_name(分支名对版本号
  没有约束力),这样才不会堵死 D-04 的调试通道。

成功时把版本号本身打到 stdout(只有版本号,方便 shell 直接捕获),诊断信息
打到 stderr;失败时抛 ``VersionMismatch``,``main()`` 把异常文本打到 stderr
并返回非零退出码。

用法::

    python3 scripts/release/check_version_consistency.py <ref_name> <is_tag>

``<is_tag>`` 接受 ``true``/``false``(大小写不敏感)。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 仓库根路径:从 __file__ (scripts/release/check_version_consistency.py) 上溯两级
# 到 scripts/release/ 的父父目录,即仓库根。
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACKAGE_JSON_PATH = REPO_ROOT / "frontend" / "package.json"
DEFAULT_MAIN_PY_PATH = REPO_ROOT / "backend" / "main.py"

# semver 形状(三段数字,可选 -prerelease/+build 后缀)而非宽松的 [^"]+,
# 避免 backend/main.py 里任何其他 version="..." 字面量把校验误伤成不一致。
_SEMVER_VERSION_RE = re.compile(
    r'version\s*=\s*"(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)"'
)


class VersionMismatch(RuntimeError):
    """版本号在参与比对的各处之间不一致,或 main.py 里的匹配数不满足预期。"""


def read_package_version(path: "Path | None" = None) -> str:
    """读取 ``frontend/package.json`` 的 ``version`` 字段。"""
    package_path = path or DEFAULT_PACKAGE_JSON_PATH
    data = json.loads(package_path.read_text(encoding="utf-8"))
    return str(data["version"])


def read_main_versions(path: "Path | None" = None) -> list[str]:
    """读取 ``backend/main.py`` 里所有 semver 形状的 ``version="..."`` 匹配,按出现顺序返回。"""
    main_path = path or DEFAULT_MAIN_PY_PATH
    text = main_path.read_text(encoding="utf-8")
    return _SEMVER_VERSION_RE.findall(text)


def normalize_tag(ref_name: str) -> str:
    """只剥掉一个前导 ``v``(用 ``str.removeprefix``,不是会反复吞掉前导字符的
    那个字符串方法——那个方法会把 ``"vv0.2.0"`` 错误地吞成 ``"0.2.0"``)。
    """
    return ref_name.removeprefix("v")


def check_version_consistency(
    ref_name: str,
    is_tag: bool,
    package_path: "Path | None" = None,
    main_path: "Path | None" = None,
) -> str:
    """判定版本号一致性,返回一致时的版本字符串;不一致时抛 ``VersionMismatch``。"""
    main_versions = read_main_versions(main_path)
    if len(main_versions) < 2:
        raise VersionMismatch(
            "backend/main.py 里 semver 形状的 version= 匹配少于 2 个"
            f"(实际匹配数: {len(main_versions)}, 匹配到: {main_versions})。"
            "CLAUDE.md 约定版本号需在 frontend/package.json 与 backend/main.py"
            "的两处 FastAPI version= 字段一起同步,请检查 backend/main.py。"
        )
    if len(set(main_versions)) != 1:
        raise VersionMismatch(
            "backend/main.py 里的多个 version= 字段彼此不一致: "
            f"{main_versions}"
        )
    main_version = main_versions[0]

    package_version = read_package_version(package_path)

    if is_tag:
        expected_version = normalize_tag(ref_name)
        if expected_version == package_version == main_version:
            return expected_version
        raise VersionMismatch(
            "版本不一致: "
            f"tag={expected_version} package.json={package_version} main.py={main_version}"
        )

    # 非 tag 模式(workflow_dispatch 手动触发,ref_name 是分支名):不参照
    # ref_name,只要求 package.json 与 main.py 两者相等。
    if package_version == main_version:
        return package_version
    raise VersionMismatch(
        "版本不一致(非 tag 模式,忽略分支名): "
        f"package.json={package_version} main.py={main_version}"
    )


def main(argv: "list[str] | None" = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(
            "用法: check_version_consistency.py <ref_name> <is_tag: true|false>",
            file=sys.stderr,
        )
        return 1

    ref_name, is_tag_raw = args
    is_tag = is_tag_raw.strip().lower() == "true"

    try:
        version = check_version_consistency(ref_name, is_tag)
    except VersionMismatch as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    print(f"版本一致: {version}", file=sys.stderr)
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
