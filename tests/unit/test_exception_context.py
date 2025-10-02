import contextlib
import unittest

from pyiron_snippets.exception_context import ExceptionExitStack, on_error


def its_historical(history: list[str], message: str) -> None:
    history.append(message)


class TestExceptionContext(unittest.TestCase):
    def test_exception_exit_stack(self):
        with self.subTest("Callback on all exceptions when no types are specified"):
            history = []
            try:
                with ExceptionExitStack() as stack:
                    stack.callback(its_historical, history, "with no types")
                    raise RuntimeError("Application error")
            except RuntimeError:
                self.assertEqual(history, ["with no types"])

        with self.subTest("Callback on matching exception with specifier"):
            history = []
            try:
                with ExceptionExitStack(RuntimeError) as stack:
                    stack.callback(its_historical, history, "with matching type")
                    raise RuntimeError("Application error")
            except RuntimeError:
                self.assertEqual(history, ["with matching type"])

        with self.subTest("No callback on mis-matching exception with specifier(s)"):
            history = []
            try:
                with ExceptionExitStack(TypeError, ValueError) as stack:
                    stack.callback(its_historical, history, "with mis-matching types")
                    raise RuntimeError("Application error")
            except RuntimeError:
                self.assertEqual(history, [])

        with self.subTest("No callback without exceptions; combining is ok"):
            history = []
            msg = "but we should see this"
            with ExceptionExitStack() as exc_stack, contextlib.ExitStack() as reg_stack:
                exc_stack.callback(its_historical, history, "we shouldn't see this")
                # because there's no exception here
                reg_stack.callback(its_historical, history, msg)
            self.assertEqual(history, [msg])

        with self.subTest("Clean error message on garbage input"):
            with self.assertRaises(ValueError):
                ExceptionExitStack("these", "aren't", "exceptions")

    def test_on_error(self):
        with self.subTest("Callback on all exceptions when no types are specified"):
            history = []
            msg = "with no types"
            try:
                with contextlib.ExitStack() as stack:
                    stack.enter_context(
                        on_error(
                            its_historical,
                            None,
                            history,
                            message=msg,
                        )
                    )
                    raise RuntimeError("Application error")
            except RuntimeError:
                self.assertEqual(history, [msg])

        with self.subTest("Callback on matching exception with specifier"):
            history = []
            msg = "with matching type"
            try:
                with contextlib.ExitStack() as stack:
                    stack.enter_context(
                        on_error(
                            its_historical,
                            RuntimeError,
                            history,
                            message=msg,
                        )
                    )
                    raise RuntimeError("Application error")
            except RuntimeError:
                self.assertEqual(history, [msg])

        with self.subTest("No callback on mis-matching exception with specifier(s)"):
            history = []
            try:
                with contextlib.ExitStack() as stack:
                    stack.enter_context(
                        on_error(
                            its_historical,
                            (TypeError, ValueError),
                            history,
                            message="with mis-matching types",
                        )
                    )
                    raise RuntimeError("Application error")
            except RuntimeError:
                self.assertEqual(history, [])

        with self.subTest("No callback without exceptions"):
            history = []
            msg = "but we should see this"
            with contextlib.ExitStack() as stack:
                stack.enter_context(
                    on_error(
                        its_historical,
                        (TypeError, ValueError),
                        history,
                        message="we shouldn't see this",
                    )
                )
                # because there's no exception here
                stack.callback(its_historical, history, msg)
            self.assertEqual(history, [msg])

        with self.subTest("Clean error message on garbage input"):
            history = []
            with self.assertRaises(ValueError), contextlib.ExitStack() as stack:
                stack.enter_context(
                    on_error(
                        its_historical,
                        "this is not an exception type",
                        history,
                        message="we shouldn't see this",
                    )
                )


if __name__ == "__main__":
    unittest.main()
