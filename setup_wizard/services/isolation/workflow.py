"""Completion checks for Gacha Setup's synchronous EXEC_DEFAULT chain."""

from contextlib import contextmanager


@contextmanager
def checked_workflow(import_order, steps):
    """
    Observes operator results in the isolated background worker.
    If an intermediate step fails, cancels, or stops before the final step,
    catches the failure explicitly rather than treating incomplete output as success.
    """
    if not steps or len(steps) < 2:
        raise RuntimeError("The selected setup workflow is empty.")

    factory = import_order.ComponentFunctionFactory
    descriptor = factory.__dict__["create_component_function"]
    original = factory.create_component_function
    completed = set()
    failures = []

    def create_checked(component_name):
        operation = original(component_name)

        def execute_checked(*args, **kwargs):
            try:
                result = operation(*args, **kwargs)
            except Exception as exc:
                failures.append(f"{component_name}: {exc}")
                raise
            if result != {"FINISHED"}:
                failures.append(f"{component_name}: returned {result!r}")
            else:
                completed.add(component_name)
            return result

        return execute_checked

    factory.create_component_function = staticmethod(create_checked)
    try:
        yield
        if failures:
            raise RuntimeError("Setup did not finish successfully: " + "; ".join(failures))
        if steps[-1] not in completed:
            raise RuntimeError(f"Setup stopped before its final step: {steps[-1]}")
    finally:
        factory.create_component_function = descriptor
