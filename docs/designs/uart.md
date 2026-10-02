# The design, implementation, and usage of the UART class (WIP)

## Original board implementation

In MicroPython the
[`machine.UART`](https://docs.micropython.org/en/latest/library/machine.UART.html) class represents
a UART connection with a device. A created `UART` instance acts as a stream object and allows you
to write to the device and read from it.

These are the noteworthy operations of the board version:

- Create an object with `machine.UART(id, ...)` constructor
- Write to the device with `UART.write(buf)`
- See how many characters can be read from device with `UART.any()`
- Read characters from device using: `UART.read([nbytes])`, `UART.readinto(buf, [nbytes])`, or `UART.readline()`
- Send a break condition to device with `UART.sendbreak()`
- Configure interrupt handler for UART event with `UART.irq(handler, trigger)`.

## Goal of the design

Since the `UART` class represents a generic device it's important that the design is flexible enough
to represent whatever device is being tested, whether this is basic single responses or a more
complicated series of responses.

The overall goal for this class's design:

- Implement a basic simulated fake which matches the board versions API exactly, so code being
  tested needs minimal changes.
- Fake the underlying I/O operations by buffering a response on a write.
- Allow test authors to easily configure how the object responds to avoid needless subclassing for
  most configurations.
- Provide methods to inspect written data, for confirming writes in tests.
- Match common board version side effects/ quirks and default values.
- Match basic board method parameter validations, so obvious invalid values will raise like on-board.

## Architecture and implementation details

In this section I'll go over the different parts of the implementation and how they work.

> [!note]
> This section will go over most of the top-level design and implementation info but to
> save space some of the more technical information will be in the method docstrings, so make
> sure to read them for more details.

### Multiton Registry and initialization

A multiton registry is implemented to allow existing code to be tested and to match board
operation. It works by storing a dictionary of ID to `UART` instances, and when a new `UART` object
is created the `__new__` method checks if an instance with the provided ID matches and either
returns that or creates and registers a new instance.<br>
This means that test code that doesn't support providing the UART object through dependency
injection can be tested by creating and configuring the `UART` instance before the code under test
is ran.

The initialization logic also has a few quirks on-board which are replicated, mostly around how
re-initialization is handled. On the ESP32 port a created `UART` object can be configured by either
calling `uart.init()` or by creating a new instance with the same ID (which updates existing
instances with the same ID since they're the same object). When these are called the user provides
the attributes they want to change and only the provided arguments are updated, with the rest being
left as their previous value.

This was implemented by including an initialization guard in the constructor, so when the object is
first created it creates the attributes and assigns default values, then the regular `init()` method
is called and it sets the provided arguments. This allows code that re-initializes to run without
breaking any test customization since those attributes are set in the guard and any instance
returned from a `__new__` has its constructor called, even if it's already been instantiated.

#### Sentinel values

To ensure that the "keep previous value" logic works properly for re-initialization, default
sentinel values are used for the parameters of the initialization functions, these have a few
different conventions to attempt to closely match the ESP32 implementation.

- Numeric arguments like `baudrate`, `txbuf`, and `rxbuf` are kept as their previous value if the
  provided value is `<= 0`.
- `bits = 0` for previous value.
- For constrained arguments like `parity`, `timeout`, `timeout_char`, `invert`, and `flow` use `-1`
  to keep the previous value.
- Pin fields `rx`, `tx`, `rts`, and `cts` are slightly different with `None` keeping the previous
  value and `-1` unassigning the pin.

### ID validation and default pins

The generic ESP32 port of MicroPython (which is our reference port) only allows `UART` objects to be
created with an ID of either `1` or `2` (`0` is reserved for REPL connection and can technically be
used but has extra logic that didn't get around to implementing), our code respects this and raises
the appropriate `ValueError` if code tries to create a UART with a different ID.

Additionally, the ESP32 port has default Pins for these 2 ID's which are used if no Pin is specified.

| UART ID | Default TX | Default RX |
| ------- | ---------- | ---------- |
| 1       | Pin 5      | Pin 4      |
| 2       | Pin 17     | Pin 16     |

### Response strategy pattern

When our `UART` test objects are written to with `write()` a response is buffered to be returned on
a future `read()` call.

This buffered response is the main place which needs to be configured as a generic UART device can
respond to a write in numerous ways, and multiple responses may be necessary for more complex
operations which may make multiple write->read calls.

The strategy pattern is used to achieve this by delegating the response handling to a
`UARTResponseStrategy` object, which accepts the data being written and returns the response to be
appended to the read buffer. This allows test authors to customize their mocked device's responses
in a few different ways by using one of the already implemented response strategy subclasses.

The main response strategy we recommend is the `MappingResponseStrategy` which specifies the
responses as a dictionary mapping of data written to response `{"Data": "Response"}`. This is
preferred as it allows for a more explicit mapping of written data to buffered response and by
default is in a strict mode which ensures only expected data is written, with unmapped data causing
a raise.

But to support other uses there are a few other options:

| Strategy                   | Behaviour                                                                             | Notes                                                                                                                               |
| -------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `EchoResponseStrategy`     | Echoes back whatever was written.                                                     | Default strategy if none is given.                                                                                                  |
| `MappingResponseStrategy`  | Dict of "data written" -> "response to queue" (e.g. `{"AT\r": b"OK\r\n"}`).           | When in strict mode aka `is_strict=True` (default) raises `KeyError` on unmapped input, if not in strict mode then echo back input. |
| `ListResponseStrategy`     | A FIFO queue of responses; each `write()` pops the next item.                         | `on_exhausted` controls what happens once the list runs out: `"empty"`, `"repeat_last"`,`"raise"`, or `"cycle"`.                    |
| `ConstantResponseStrategy` | Always queues the same fixed response.                                                | Useful for simulating an always-broken/always-OK device.                                                                            |
| `CallbackResponseStrategy` | Runs a user callback `Callable[[bytes, UART], bytes]` and queues whatever it returns. | Use when the response needs custom logic (e.g. depends on call count, or on other UART state).                                      |

There are also utility methods to easily set or customize the response strategy as well as a static
`UART.create_stub()` factory for creating a `UART` instance and configuring the response strategy in
one line (see API reference section).

### Read and write buffers

The `_read_buf` attribute is a bytearray which holds the buffered data waiting to be consumed by a
`read()`/`readline()`/`read_into()` call, this is what gets appended to when the device is written to.

The `_write_buf` attribute is a basic ring buffer which just stores the data that was written during
`write()` calls, it can be read with `get_written_data()` and can be useful for validating that
specific data was written. Might be reworked in future to improve spying functionality.

## API Reference

Here is the API for the Board-identical items as well as additional ones added to aid testing.

### Board-identical surface

| Member                                    | Description                                                                                 |
| ----------------------------------------- | ------------------------------------------------------------------------------------------- |
| `UART(id, ...)`                           | Constructor / multiton lookup. Can also reinitialize                                        |
| `.init(...)`                              | Reinitialize, only setting explicitly provided attributes.                                  |
| `.write(buf) -> int`                      | Write bytes, queues a response via the active strategy.                                     |
| `.read([nbytes]) -> bytes \| None`        | Read (and consume) from the buffer. `None` on empty (simulated timeout).                    |
| `.readinto(buf, [nbytes]) -> int \| None` | Read into an existing buffer.                                                               |
| `.readline([size]) -> bytes \| None`      | Read up to and including the next `\n`.                                                     |
| `.any() -> int`                           | Number of bytes available to read without blocking.                                         |
| `.deinit()`                               | Stub - does nothing.                                                                        |
| `.irq(handler, trigger, hard)`            | Stub - currently does basic param validation and returns canned IRQ object.                 |
| `.sendbreak()`                            | Runs a basic callback (if set)                                                              |
| `.flush()` / `.txdone()`                  | Stubs - no-ops / always return `True`.                                                      |
| `.ioctl(op, arg)`                         | Minimal support for poll/flush/close, for future stream use if needed (currently disabled). |
| Iteration (`for line in uart:`)           | Delegates to `readline()`.                                                                  |
| `str(uart)` / `repr(uart)`                | Matches the board's field-by-field format with `invert` and `flow` appearing only if set.   |

### Test-only extensions (not on the real board)

These are the extra method items that are available in our `fake_machine.UART` that aren't present on the board.<br>
These are mostly for controlling the stub attributes and configuring/ switching the current response strategy.

| Member                                                                                | Description                                                                    |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `UART.create_stub(...)`                                                               | Helper factory for building a pre-configured stub with strategy in one call.   |
| `UART.reset_registry()`                                                               | Clears `_UART_REGISTRY`. Call between tests to avoid state leaking.            |
| `.push_response(buf)`                                                                 | Directly queue bytes onto the read buffer, without going through `write()`.    |
| `.get_written_data() -> bytes`                                                        | Drains and returns everything sent via `write()` so far.                       |
| `.set_mappings(mappings, is_strict=False)`                                            | Configure/replace a `MappingResponseStrategy`.                                 |
| `.add_mapping(input_, response)`                                                      | Add a single mapping (requires strategy already be `MappingResponseStrategy`). |
| `.set_constant_response(response)`                                                    | Configure/replace a `ConstantResponseStrategy`.                                |
| `.set_response_list(responses, on_exhaust)`                                           | Configure/replace a `ListResponseStrategy`.                                    |
| `.add_responses_to_list(responses, reset_index)`                                      | Append to an existing `ListResponseStrategy`.                                  |
| `.response_strategy` (property)                                                       | Get/set the active strategy instance directly, for full control.               |
| `.register_device()`                                                                  | Manually re-add the instance to the registry, shouldn't be needed.             |
| `.reset_stub(reset_strategy)`                                                         | Resets the UARTs stub attributes (write/read buffer, callbacks, strategy)      |
| `.set_read_callback(cb)`                                                              | Sets a basic callback that gets called when a read method occurs.              |
| `.set_break_callback(cb)`                                                             | Sets a basic callback to be called when `.sendbreak()` runs.                   |
| Constructor-only kwargs: `override_id_checks`, `add_to_registry`, `response_strategy` | Control multiton/registry/strategy behaviour at construction time.             |

## Basic usage examples

Some basic examples for how to use the `fake_machine.UART` test double in tests, more detailed
examples will be added later, likely to a dedicated folder. You can also see the examples and
existing tests in this codebase for more examples of use.

### Shadowing the built-in module

Shadowing the built-in module can be done through the top-level `teu.shadow_builtins()`,
which will also shadow/ register the custom `time`, `esp`, `esp32`, `espnow`, `aioespnow`, and
`network` modules.

Otherwise you can also just import `fake_machine` from `teu` and then use `fake_machine.shadow_builtin_machine()`.

```python

from teu import fake_machine

fake_machine.shadow_builtin_machine()

# Any subsequent `import machine` in the process now resolves to fake_machine
# and will no longer cause ImportErrors.
from machine import UART  # Receives fake_machine.UART (normally would ImportError without shadow)
uart = UART(1)  # Fake UART

# This modem driver imports machine and will receive fake_machine
from drivers import modem as modem_driver
```

Shadow **before** importing the module under test, otherwise it'll import the real `machine` module
(which won't get updated if shadow happens later).

### Factory: `create_stub()`

The one-call factory is the easiest way to get a fully configured device in one line:

```python
uart = fake_machine.UART.create_stub(
    1, mappings={"AT\r": b"OK\r\n"}
)
```

### Manual construction

Equivalent to the above, useful when you want to configure the strategy after construction, or reuse
a UART already created elsewhere (e.g. one instantiated by the driver-under-test during construction).:

```python
uart: fake_machine.UART = self.modem.serial  # driver already created its own UART(1)
uart.set_mappings({"AT\r": b"OK\r\n"})
```

### Using test setUp to reduce boilerplate and prevent leaking

Continuing on from the previous, the constructor can also useful for reducing the boilerplate in
each test by setting up the UART as an attribute of the test class in the `setUp()` method.

It's also important to include a cleanup call to `UART.reset_registry()` in the `setUp()` method, as
otherwise the registry will persist between tests, meaning stub configurations won't be reset.

Here's how you can setup the cleanups and instantiate both the driver being tested and the UART
object to configure in tests.

```python
def setUp(self):
    # Can choose one of these two, or both to be safe.
    fake_machine.UART.reset_registry()
    self.addCleanup(fake_machine.UART.reset_registry)

    # Instantiate driver being tested, which creates the UART we can extract.
    # The UART could be created first if desired
    self.modem = modem_driver.Modem()
    self.uart: fake_machine.UART = self.modem.serial  # Cast helps completion tools

#...
def test_modem_method(self):
    self.uart.set_mappings({"AT\r": b"OK\r\n"})
    response = self.modem.method_to_test()
    #...
```

### Common misc patterns

**Programming a multi-command device**:

```python
self.uart.set_mappings({
    "MSG-A": "RESP-A",
    "MSG-B": "RESP-B",
})
```

**Simulating unsolicited data** (data that appears without a preceding write, e.g. a boot greeting):

```python
self.uart.push_response(b"greeting text")
self.uart.read()  # Returns b"greeting text"
```

**Simulating devices that constantly stream read data**:

You can also register a read callback with `.set_read_callback(cb)` which gets ran whenever one of the read methods is called.<br>
This is useful for if you're mimicking a device which constantly streams data, or if you want to modify something on a read:

```python
def read_cb(uart):
    # Inject more data when reading
    uart.push_response(b"data")

uart = fake_machine.UART(1)
uart.set_read_callback(read_cb)
uart.read()  # Returns None since no data yet
uart.read()  # Returns b"data" since previous call ran callback
uart.readline()  # Returns b"data"
```

**Asserting on outbound data**:

```python
uart = fake_machine.UART(1)
driver = Driver(uart)
driver.run_command()  # Method that writes b"AT\r" to device

# Check the write occured
self.assertEqual(self.uart.get_written_data(), b"AT\r")
```

**Swapping strategy**:

```python
# Can either use the helper methods to switch
self.uart.set_constant_response("BAD")
self.uart.set_response_list(["A", "B", "C", "D"], on_exhaust="repeat_last")

# Or set it manually
self.uart.response_strategy = fake_machine.uart.ConstantResponseStrategy("BAD")
```

## Quirks and limitations

The current implementation has a few quirks and limitations with it that I'll briefly explain here:

### Pin objects are not currently used

At the moment the UART object holds Pin objects for the tx and rx but they go unused and data
transmission with the pins is not simulated. This means that code which relies on interrupts for
these pins likely won't be easily testable.

I decided not to implement this functionality as it would be quite hard to test and also I consider
it out of scope as it's a functionality that I can't imagine being used too much.

### IoBase functionality

The board version of `UART` technically subclasses the `io.IOBase` class so the device can be used in print statements as a file etc.

We have the necessary methods for this subclass implemented but there were problems with it causing
a crash when trying to make the `super().__new__()` call in the `UART.__new__()`, I believe this was
because it was crashing trying to find the IOBase new method or something.

This caused it to be disabled for a while but it should now be working as the call to
`super().__new__()` has been replaced with `object.__new__(cls)` which doesn't cause the
crash. Everything I've tested still works but the functionality might not fully work.

Please see [#79](https://gitlab.ecs.vuw.ac.nz/course-work/project489/2026/project/silouzaki/micropython-esp32-unix/-/work_items/79) for more info.

## Things to add/ ideas

- Callback for when the device is connected to (the client code creates a UART device to use)
- Could add a kinda pin observer so the UART will run a callback whenever a Pin value is changed
  (for simulating devices that rely on external connected pins)
