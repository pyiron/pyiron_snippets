import unittest
import warnings
from snippets.import_alarm import ImportAlarm, ImportAlarmError


class TestImportAlarm(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.no_alarm = ImportAlarm(_fail_on_warning=True)

        @self.no_alarm
        def add_one(x):
            return x + 1

        self.yes_alarm = ImportAlarm(
            "Here is a message",
            _fail_on_warning=True
        )

        @self.yes_alarm
        def subtract_one(x):
            return x + 1

        with ImportAlarm(
            "Working import",
            _fail_on_warning=True
        ) as alarm_working:
            # Suppose all the imports here pass fine
            pass

        with ImportAlarm(
            "Broken import",
            _fail_on_warning=True
        ) as alarm_broken:
            raise ImportError("Suppose a package imported here is not available")

        @alarm_working
        def add_two(x):
            return x + 2

        @alarm_broken
        def add_three(x):
            return x + 3

        self.add_one = add_one
        self.subtract_one = subtract_one
        self.add_two = add_two
        self.add_three = add_three

    def test_instance(self):
        self.assertEqual(
            1,
            self.add_one(0),
            msg="Without a message, the import alarm should not raise a warning (an "
                "exception in this case, because of the private flag)"
        )
        with self.assertRaises(
            ImportAlarmError,
            msg="With a message, the import alarm should raise a warning. (an "
                "exception in this case, because of the private flag)"
        ):
            self.subtract_one(0)

    def test_context(self):
        """
        Usage via context manager should give same results and not suppress other
        errors.
        """
        self.assertEqual(
            2,
            self.add_two(0),
            msg="Without a message, no warning (exception here) should be raised"
        )

        with self.assertRaises(
            ImportAlarmError,
            msg="With a message, a warning (exception here) should be raised"
        ):
            self.add_three(0)

    def test_scope(self):
        with self.assertRaises(
            ZeroDivisionError,
            msg="Context manager should swallow unrelated exceptions"
        ), ImportAlarm("Unrelated"):
            print(1 / 0)


if __name__ == "__main__":
    unittest.main()
