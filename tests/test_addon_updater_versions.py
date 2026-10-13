"""Updater regressions, runnable with Python without loading Blender."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / "setup_wizard/addon_updater/addon_updater.py"
spec = importlib.util.spec_from_file_location("updater_under_test", SOURCE)
module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"bpy": types.ModuleType("bpy"),
                             "addon_utils": types.ModuleType("addon_utils")}):
    spec.loader.exec_module(module)


def release(number, title=None):
    tag = f"v3.8.0-beta.{number}"
    return {"name": title or f"v3.8.0 Beta {number}", "tag_name": tag,
            "prerelease": True, "zipball_url": f"https://example.test/{tag}.zip"}


class UpdaterVersionTests(unittest.TestCase):
    def make_updater(self, releases):
        updater = module.SingletonUpdater()
        updater.use_releases = True
        updater.user = "test"
        updater.repo = "test"
        updater.current_version = (3, 8, 0, 9)
        updater.get_api = Mock(return_value=releases)
        updater.set_updater_json = Mock()
        updater.save_updater_json = Mock()
        return updater

    def test_beta10_is_detected_after_beta9_in_api_response(self):
        updater = self.make_updater([release(9), release(10)])
        ready, version, link = updater.check_for_update(now=True)
        self.assertTrue(ready)
        self.assertEqual(version, (3, 8, 0, 10))
        self.assertEqual(link, "https://example.test/v3.8.0-beta.10.zip")
        self.assertEqual(updater.tags, ["v3.8.0-beta.10", "v3.8.0-beta.9"])

    def test_order_is_numeric_and_independent_of_api_order(self):
        for numbers in ((9, 10, 11, 2), (2, 11, 9, 10), (11, 10, 9, 2)):
            with self.subTest(numbers=numbers):
                updater = self.make_updater([release(n) for n in numbers])
                updater.get_tags()
                self.assertEqual(updater.tags, [f"v3.8.0-beta.{n}" for n in (11, 10, 9, 2)])

    def test_stable_is_newer_than_its_betas(self):
        stable = {"name": "Stable", "tag_name": "v3.8.0", "prerelease": False,
                  "zipball_url": "https://example.test/stable.zip"}
        updater = self.make_updater([release(10), stable, release(9)])
        self.assertEqual(updater.check_for_update(now=True),
                         (True, (3, 8, 0), stable["zipball_url"]))

    def test_beta_filter_is_applied_before_selecting_latest(self):
        stable = {"name": "v3.7.3", "tag_name": "v3.7.3", "prerelease": False,
                  "zipball_url": "https://example.test/stable.zip"}
        updater = self.make_updater([release(9), release(10), stable])
        updater.skip_tag = lambda _, tag: tag["prerelease"]
        updater.get_tags()
        self.assertEqual(updater.tag_latest, "v3.7.3")
        self.assertEqual(updater.tags, ["v3.7.3"])

    def test_release_title_does_not_determine_version(self):
        updater = self.make_updater([release(9), release(10, "Texture fixes 2026")])
        self.assertEqual(updater.check_for_update(now=True)[1], (3, 8, 0, 10))

    def test_branches_remain_first_but_latest_version_and_link_match(self):
        updater = self.make_updater([release(9), release(10)])
        updater.include_branches = True
        updater.include_branch_list = ["dev", "master"]
        self.assertEqual(updater.check_for_update(now=True),
                         (True, (3, 8, 0, 10), "https://example.test/v3.8.0-beta.10.zip"))
        self.assertEqual(updater.tags[:2], ["Dev", "Master"])

    def test_already_on_beta10_does_not_offer_beta9(self):
        updater = self.make_updater([release(9), release(10)])
        updater.current_version = (3, 8, 0, 10)
        self.assertEqual(updater.check_for_update(now=True), (False, None, None))

    def test_manual_selection_uses_selected_version(self):
        updater = self.make_updater([release(9), release(10)])
        updater.get_tags()
        updater.set_tag("v3.8.0-beta.9")
        self.assertEqual(updater.update_version, "v3.8.0 beta9")
        self.assertEqual(updater.update_link, "https://example.test/v3.8.0-beta.9.zip")

    def test_empty_or_filtered_releases_do_not_offer_update(self):
        for releases in ([], [release(9), release(10)]):
            updater = self.make_updater(releases)
            updater.skip_tag = lambda _, tag: True
            self.assertEqual(updater.check_for_update(now=True), (False, None, None))

    def test_tags_endpoint_is_also_sorted_numerically(self):
        updater = self.make_updater([{"name": f"v3.8.0-beta.{n}",
                                      "zipball_url": f"https://example.test/{n}.zip"}
                                     for n in (9, 10)])
        updater.use_releases = False
        self.assertEqual(updater.check_for_update(now=True),
                         (True, (3, 8, 0, 10), "https://example.test/10.zip"))


if __name__ == "__main__":
    unittest.main()
