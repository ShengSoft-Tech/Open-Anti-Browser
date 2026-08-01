import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "release"))

import check_version_consistency as vc  # noqa: E402


def _write_package_json(dir_path: Path, version: str) -> Path:
    path = dir_path / "package.json"
    path.write_text(json.dumps({"version": version}), encoding="utf-8")
    return path


def _write_main_py(dir_path: Path, versions: list[str]) -> Path:
    path = dir_path / "main.py"
    lines = [f'app = FastAPI(title="X", version="{v}")' for v in versions]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_template(dir_path: Path, version: str) -> Path:
    path = dir_path / "RELEASE_NOTES_TEMPLATE.md"
    path.write_text(f"<!-- RELEASE_VERSION: {version} -->\n\n## 本次更新\n", encoding="utf-8")
    return path


class NormalizeTagTests(unittest.TestCase):
    def test_normalize_tag_strips_leading_v(self) -> None:
        self.assertEqual(vc.normalize_tag("v0.2.0"), "0.2.0")

    def test_normalize_tag_no_leading_v_is_noop(self) -> None:
        self.assertEqual(vc.normalize_tag("0.2.0"), "0.2.0")

    def test_normalize_tag_strips_only_one_leading_char(self) -> None:
        # 证明用的是 removeprefix(只剥一个前导字符),不是会把前缀当字符集
        # 反复吞掉的 lstrip("v")。
        self.assertEqual(vc.normalize_tag("vv0.2.0"), "v0.2.0")


class CurrentRepoStateTests(unittest.TestCase):
    """在当前仓库真实文件上跑,只断言相等关系,不断言具体数字(会随发版变化)。"""

    def test_read_main_versions_returns_at_least_two_matching_entries(self) -> None:
        versions = vc.read_main_versions()
        self.assertGreaterEqual(len(versions), 2)
        self.assertEqual(len(set(versions)), 1)

    def test_package_version_matches_main_version_in_current_repo(self) -> None:
        package_version = vc.read_package_version()
        main_versions = vc.read_main_versions()
        self.assertEqual(package_version, main_versions[0])

    def test_template_anchor_version_matches_package_version_in_current_repo(self) -> None:
        template_version = vc.read_template_version()
        package_version = vc.read_package_version()
        self.assertEqual(template_version, package_version)


class CheckVersionConsistencyTagModeTests(unittest.TestCase):
    def test_tag_mode_all_three_consistent_returns_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            package_path = _write_package_json(tmp_path, "1.2.3")
            main_path = _write_main_py(tmp_path, ["1.2.3", "1.2.3"])
            template_path = _write_template(tmp_path, "1.2.3")
            result = vc.check_version_consistency(
                "v1.2.3",
                True,
                package_path=package_path,
                main_path=main_path,
                template_path=template_path,
            )
            self.assertEqual(result, "1.2.3")

    def test_tag_mode_mismatch_raises_with_all_three_values_in_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            package_path = _write_package_json(tmp_path, "1.2.3")
            main_path = _write_main_py(tmp_path, ["1.2.3", "1.2.3"])
            template_path = _write_template(tmp_path, "1.2.3")
            with self.assertRaises(vc.VersionMismatch) as ctx:
                vc.check_version_consistency(
                    "v9.9.9",
                    True,
                    package_path=package_path,
                    main_path=main_path,
                    template_path=template_path,
                )
            message = str(ctx.exception)
            self.assertIn("9.9.9", message)
            self.assertIn("1.2.3", message)


class CheckVersionConsistencyNonTagModeTests(unittest.TestCase):
    def test_non_tag_mode_package_and_main_agree_returns_package_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            package_path = _write_package_json(tmp_path, "2.0.0")
            main_path = _write_main_py(tmp_path, ["2.0.0", "2.0.0"])
            template_path = _write_template(tmp_path, "2.0.0")
            # ref_name 是分支名,不应影响结果——传一个与实际版本毫不相干的分支名。
            result = vc.check_version_consistency(
                "feature/something-unrelated",
                False,
                package_path=package_path,
                main_path=main_path,
                template_path=template_path,
            )
            self.assertEqual(result, "2.0.0")

    def test_non_tag_mode_mismatch_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            package_path = _write_package_json(tmp_path, "2.0.0")
            main_path = _write_main_py(tmp_path, ["2.0.1", "2.0.1"])
            template_path = _write_template(tmp_path, "2.0.0")
            with self.assertRaises(vc.VersionMismatch):
                vc.check_version_consistency(
                    "main",
                    False,
                    package_path=package_path,
                    main_path=main_path,
                    template_path=template_path,
                )


class CheckVersionConsistencyTemplateTests(unittest.TestCase):
    def test_tag_mode_all_four_consistent_returns_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            package_path = _write_package_json(tmp_path, "1.2.3")
            main_path = _write_main_py(tmp_path, ["1.2.3", "1.2.3"])
            template_path = _write_template(tmp_path, "1.2.3")
            result = vc.check_version_consistency(
                "v1.2.3",
                True,
                package_path=package_path,
                main_path=main_path,
                template_path=template_path,
            )
            self.assertEqual(result, "1.2.3")

    def test_tag_mode_template_not_bumped_raises_with_template_value_in_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            package_path = _write_package_json(tmp_path, "1.2.3")
            main_path = _write_main_py(tmp_path, ["1.2.3", "1.2.3"])
            # 模拟漏改模板:package.json/main.py 都已 bump,模板锚点还停留在旧版本。
            template_path = _write_template(tmp_path, "1.2.2")
            with self.assertRaises(vc.VersionMismatch) as ctx:
                vc.check_version_consistency(
                    "v1.2.3",
                    True,
                    package_path=package_path,
                    main_path=main_path,
                    template_path=template_path,
                )
            message = str(ctx.exception)
            self.assertIn("template=1.2.2", message)

    def test_non_tag_mode_template_not_bumped_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            package_path = _write_package_json(tmp_path, "2.0.0")
            main_path = _write_main_py(tmp_path, ["2.0.0", "2.0.0"])
            template_path = _write_template(tmp_path, "2.0.1")
            with self.assertRaises(vc.VersionMismatch):
                vc.check_version_consistency(
                    "main",
                    False,
                    package_path=package_path,
                    main_path=main_path,
                    template_path=template_path,
                )

    def test_missing_template_anchor_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template_path = tmp_path / "RELEASE_NOTES_TEMPLATE.md"
            template_path.write_text(
                "# 没有锚点的模板\n\n这份文件里没有任何 RELEASE_VERSION 注释。\n",
                encoding="utf-8",
            )
            with self.assertRaises(vc.VersionMismatch):
                vc.read_template_version(template_path)


class MainPyMatchCountTests(unittest.TestCase):
    def test_fewer_than_two_main_matches_raises_with_count_and_claude_md_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            package_path = _write_package_json(tmp_path, "1.0.0")
            main_path = _write_main_py(tmp_path, ["1.0.0"])
            with self.assertRaises(vc.VersionMismatch) as ctx:
                vc.check_version_consistency(
                    "v1.0.0", True, package_path=package_path, main_path=main_path
                )
            message = str(ctx.exception)
            self.assertIn("1", message)
            self.assertIn("CLAUDE.md", message)


if __name__ == "__main__":
    unittest.main()
