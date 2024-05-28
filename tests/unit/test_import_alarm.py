import unittest
from snippets.import_alarm import ImportAlarm, ImportAlarmError


class TestImportAlarm(unittest.TestCase):

    def test_instance(self):
        no_alarm = ImportAlarm(_fail_on_warning=True)

        @no_alarm
        def add_one(x):
            return x + 1

        yes_alarm = ImportAlarm(
            "Here is a message",
            _fail_on_warning=True
        )

        @yes_alarm
        def subtract_one(x):
            return x + 1

        try:
            self.assertEqual(
                1,
                add_one(0),
                msg="Wrapped function should return the same return value."
            )
        except ImportAlarmError:
            self.fail("Without a message, the import alarm should not raise a warning (an "
                    "exception in this case, because of the private flag)")
        with self.assertRaises(
            ImportAlarmError,
            msg="With a message, the import alarm should raise a warning. (an "
                "exception in this case, because of the private flag)"
        ):
            subtract_one(0)

    def test_context(self):
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

        self.assertEqual(
            2,
            add_two(0),
            msg="Without a message, no warning (exception here) should be raised"
        )

        with self.assertRaises(
            ImportAlarmError,
            msg="With a message, a warning (exception here) should be raised"
        ):
            add_three(0)

    def test_scope(self):
        with self.assertRaises(
            ZeroDivisionError,
            msg="Context manager should swallow unrelated exceptions"
        ), ImportAlarm("Unrelated"):
            print(1 / 0)


if __name__ == "__main__":
    unittest.main()
