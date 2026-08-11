"""utils.py: Just a small file to hold any utility classes I need.

Keeping separate to avoid any cyclic import problems."""

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Callable


class IRQ:
    """Basic util class for representing IRQ objects in peripheral classes.

    When IRQ methods (like ``Pin.IRQ()``) are used on board they return the created IRQ object,
    object just holds the handler and the relevant trigger object to call the handler with.

    Each class that uses IRQ's has a slightly different implementation (UART's has a flags
    attribute, Pin doesn't) but this class should be fine to support multiple as long as the
    implementation of one attribute doesn't invalidate another. But that will likely be future
    work.
    """

    def __init__(self, handler: Callable, target, trigger: int) -> None:
        """Create a new IRQ that when called will run `handler` with `target` as the argument.

        :param handler: The handler callback function that will be ran with `target`.
        :param target: The target object to call `handler` with
        :param trigger: The IRQ value/s (bitwise or'd if multiple) to trigger the interrupt.
          Trigger is stored here as it can be changed or queried through the `trigger` function.
        """
        if not callable(handler):
            raise TypeError("Provided IRQ handler is not callable")

        self._handler = handler
        self._target = target
        self.trigger_val = trigger

    def __call__(self):
        """Triggers the IRQ by running the handler with the target."""
        self._handler(self._target)

    def trigger(self, new_trigger: int | None = None) -> int:
        """Either returns the current `trigger_val` if new_trigger is present, or sets it to
        `new_trigger` and returns previous trigger value."""
        if new_trigger is not None:
            old_trig = self.trigger_val
            self.trigger_val = new_trigger
            return old_trig

        return self.trigger_val

    def reinit(self, handler: Callable, trigger: int) -> None:
        """Reinitialize the handler and trigger for this IRQ, used to avoid creating new IRQ
        objects."""
        self._handler = handler
        self.trigger_val = trigger
