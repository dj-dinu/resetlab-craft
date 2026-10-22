import unittest

from tools.prepare_public_beta import require_no_python_advisories


class ReleaseAdvisoryGateTests(unittest.TestCase):
    def test_clear_inventory_passes_without_exempting_build_packages(self):
        require_no_python_advisories({'python_package_advisories': [
            {'name': 'pillow', 'version': '13.0.0', 'advisory_ids': []},
        ]})

    def test_blocked_inventory_identifies_package_version_and_advisory(self):
        with self.assertRaisesRegex(AssertionError,
                r'pillow==12\.3\.0: GHSA-22hg-r758-rrw9'):
            require_no_python_advisories({'python_package_advisories': [
                {'name': 'numpy', 'version': '2.3.5', 'advisory_ids': []},
                {'name': 'pillow', 'version': '12.3.0',
                 'advisory_ids': ['GHSA-22hg-r758-rrw9']},
            ]})

    def test_missing_or_incomplete_advisory_report_still_fails(self):
        for inventory in ({}, {'python_package_advisories': [
                {'name': 'pillow', 'version': '13.0.0'}]}):
            with self.subTest(inventory=inventory), self.assertRaises(KeyError):
                require_no_python_advisories(inventory)


if __name__ == '__main__':
    unittest.main()
