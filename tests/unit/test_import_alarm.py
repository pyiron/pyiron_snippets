# coding: utf-8
# Copyright (c) Max-Planck-Institut für Eisenforschung GmbH - Computational Materials Design (CM) Department
# Distributed under the terms of "New BSD License", see the LICENSE file.

import unittest
import warnings
from pyiron_base.utils.error import ImportAlarm


class TestImportAlarm(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.import_alarm = ImportAlarm()

        @self.import_alarm
        def add_one(x):
            return x + 1

        with ImportAlarm("Broken import") as alarm_broken:
            pass

        @alarm_broken
        def add_two(x):
            return x + 2

        with ImportAlarm("Working import") as alarm_working:
            pass

        @alarm_working
        def add_three(x):
            return x + 3

        self.add_one = add_one
        self.add_two = add_two
        self.add_three = add_three

    def test_no_warning(self):
        with warnings.catch_warnings(record=True) as w:
            self.add_one(0)
        self.assertEqual(
            len(w), 0, "Expected no warnings, but got {} warnings.".format(len(w))
        )

    def test_has_warning(self):
        self.import_alarm.message = "Now add_one should throw an ImportWarning"

        with warnings.catch_warnings(record=True) as w:
            self.add_one(1)
        self.assertEqual(
            len(w), 1, "Expected one warning, but got {} warnings.".format(len(w))
        )

    def test_context(self):
        """
        Usage via context manager should give same results and not suppress other errors.
        """

        with warnings.catch_warnings(record=True) as w:
            self.add_two(0)
        self.assertEqual(
            len(w), 1, "Expected one warning, but got {} warnings.".format(len(w))
        )

        with warnings.catch_warnings(record=True) as w:
            self.add_three(0)
        self.assertEqual(
            len(w), 0, "Expected one warning, but got {} warnings.".format(len(w))
        )

        with self.assertRaises(
            ZeroDivisionError, msg="Context manager should swallow unrelated exceptions"
        ), ImportAlarm("Unrelated"):
            print(1 / 0)


if __name__ == "__main__":
    unittest.main()
