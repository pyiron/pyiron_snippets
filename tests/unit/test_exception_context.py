import unittest

from pyiron_snippets.exception_context import ExceptionExitStack


class TestExceptionContext(unittest.TestCase):
    def test_exception_exit_stack(self):
        def rollback(history: list[str], message: str) -> None:
            history.append(message)

        with self.subTest("Callback on all exceptions when no types are specified"):
            history = []
            try:
                with ExceptionExitStack() as stack:
                    stack.callback(rollback, history, "with no types")
                    raise RuntimeError("Application error")
            except RuntimeError:
                self.assertEqual(history, ["with no types"])

        with self.subTest("Callback on matching exception with specifier"):
            history = []
            try:
                with ExceptionExitStack(RuntimeError) as stack:
                    stack.callback(rollback, history, "with matching type")
                    raise RuntimeError("Application error")
            except RuntimeError:
                self.assertEqual(history, ["with matching type"])

        with self.subTest("No callback on mis-matching exception with specifier(s)"):
            history = []
            try:
                with ExceptionExitStack(TypeError, ValueError) as stack:
                    stack.callback(rollback, history, "with mis-matching types")
                    raise RuntimeError("Application error")
            except RuntimeError:
                self.assertEqual(history, [])

        with self.subTest("No callback without exceptions"):
            history = []
            with ExceptionExitStack() as stack:
                stack.callback(rollback, history, "we shouldn't see this")
                # because there's no exception here
            self.assertEqual(history, [])
