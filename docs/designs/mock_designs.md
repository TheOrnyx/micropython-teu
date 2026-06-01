# Designs for the MicroPython Mocks

This is where I'll put my ideas and notes for designing the testing doubles along with the final
implementation. Please note that I'll kinda use this as a dumping ground for ideas initially so
anything here is subject to change while I'm still designing things.

## Resources

Gonna put a list of helpful resources and things for me to look at again later here

- https://abseil.io/resources/swe-book/html/ch13.html - Google software engineering book test double chapter
- http://xunitpatterns.com/ - Great site for test term definitions and other stuff
- Book: Test Driven Development for Embedded C (talks about this kinda stuff but more C oriented)

## General Double Designs

The website [xunitpatterns](http://xunitpatterns.com/) has some good info but they're very
opinionated about their terms. Might need to read more of this and reword some things.

Based on what I've read on the xunitpatterns site, along with some other books and web
resources, these seem to be the best definitions for the terms:

- Test Double: Overall term for any kind of faked testing object
- Test Stub: Basic double where the tester provides the return values for function calls (with specific args)
- Test Spy: Literally just a Stub that also records the values passed in, for later confirmation.
  - Will probably treat Test Spy and Test Stub as basically the same thing
- Mock Object: Kinda like a stub except you specify an expected order of inputs, along with outputs.
  Performs assertions to assure method calls happen in an exact order with exact args
  - NOTE: see next paragraph.
- Fake Object: A simulated version of a depended on component which provides the same functionality but without requiring the actual object.
  - So for example: instead of running your database code tests on a real database you use a fake in-memory one.

Just to note: Mocks don't always need to specify an exact order for their expectations, what I'm
referring to are strict mocks, lenient mocks which support out-of-order (and even missing)
expectations do exist and are the norm in most modern mock frameworks. However, most of my reference
material is embedded C based which typically defines in-order mocks, so I'll use strict as my
baseline. The best option depends on a few factors and I will revisit lenient mocks in the future.

Overall, most of our test doubles will likely end up being partly fakes anyway, as there are some
parts of these classes that need to perform simulated operations under the hood, like `UART.write()`
can't just return the response, it needs to be added to the buffer, the `UART.any()` needs to return
the size of the buffer and the `UART.read()` needs to return the response. However, the requirements
of these fakes will become more apparent later once we begin to implement the doubles. So just keep
in mind when I refer to my implementations just as a "basic stub" I mean a basic stub which also has
the required fake implementations.

My hope is to design base classes for the important objects which will fake any required
functionality for the user and expose mechanisms for stubbing (and likely spying too) where testers
can provide mappings of inputs to outputs.

## Ideas/ Things to look into

Gonna just put a list of some ideas or things I should look into here:

- Should the stubs and mocks be configured to raise an exception if the input is not mapped.

## Communication devices

When discussing communication devices I am talking about the classes which perform a 2-way
communication with a hardware device on a bus by both writing to and reading from the bus. These
will be implemented with basic fakes which include stubbing support or can be subclassed to add more
bespoke functionality if needed.

The communication devices I am talking about are mostly these modules:

| Module   | Extra Info                                                                                                                                                                                      |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `UART`   | Will likely share a common design with `SPI` and `I2C`                                                                                                                                          |
| `SPI`    |                                                                                                                                                                                                 |
| `I2C`    |                                                                                                                                                                                                 |
| `SDCard` | Likely gonna be evil to implement                                                                                                                                                               |
| `Pin`    | Will likely need to implement a kind of multiton pattern with these so there's a singleton instance for each pin and the state is shared across objects, Pins are used by everything basically. |

For designing the mocks for the communication devices I would like to settle on a design that's
consistent across similar objects. So however `UART` is designed to be stubbed I'd like to do the
same with `SPI` and `I2C`. If `UART` gets input->output mappings through a `set_mappings()` method
then the other two should have the same method, for consistency. Additionally, any naming
conventions for mock expectation methods should also be consistent across classes.

The next sections will describe some of the aspects of the designs and how I plan to implement
them. At the current point these implementations will be mostly referring to the `UART` class, as it
is the simplest protocol (and is used by the Router which is a good test benchmark). Once `UART` is
mostly complete and work begins on other classes I will update the descriptions (or split them off
into sections).

### Multiton Registry for Shared State

To better support already existing test code I plan to have the creation of these objects use the
Multiton pattern which will allow testers to create an instance of the class, provide the stub
mappings etc, and then register it in a static registry in the class.

Then when the code being tested tries to create a new instance of the device the `__new__` method
will perform a lookup into the registry, and if an instance already exists with the same ID then
that one is returned instead of a new one. Thus ensuring that testers can create their test object
and have the system being tested use it without requiring a rewrite to support dependency injection.

For most of the stubs I will supply factory methods for them to make creating stubs easier for test
creators.

### Class Structure (WIP)

One of the first aspects I want to decide is how to structure the classes. Currently my idea is to
have the base class be a simple stubbed fake which will have some private helpers for child classes
to use. This base class can be used as a basic `WhenXThenReturnY` object or can be inherited and
extended by test authors which will allow them to redefine the basic operations and attributes
fully.

Current idea is maybe to have smth like this for UART (for example)

- `UART`
  - A basic fake with support for stubbing by specifying write->read mappings and support for
    subclassing to implement fake devices (E.g, fully faked modem)
  - Will maybe have optional support for spying on call and return values (optional at the moment
    due to potential memory constraints, could be a subclass)
- `UARTMock`
  - A subclass of regular `UART` that has extra methods and assertions built in for test authors to
    define expected calls and have the object assert them.
    - NOTE: see [General Mock Designs](general-mock-designs) for info about the strict and lenient mocks.

### The Stub Design

Basically all of the missing classes in modules like `machine` and `esp32` will need to be stubbed
in some way or another, whether these stubs just be basic versions with basic programmable return
values, or fully fledged faked stubs which can be programmed and controlled in various ways. This
will depend on the importance, complexity and hardware dependence of the class (as implementing a
class such as `esp32.Partition` would likely be too advanced and out of scope for this project).

For this section know when I refer to "return value" or "response" I am referring to either the
return value of the function call, or for communication devices, the bytes appended to the response
buffer to be returned when next reading.

For classes with full programmable stub implementations (E.g communication devices like `UART` and
`I2C`), I would like the classes to provide a few different ways of specifying the mappings, which
ideally can be mixed together thanks to pythons flexibility. The ways I'm currently thinking of are:

- Basic dictionary values
  - Key is input and value is output `{b"Write-A": b"Resp-A"}`
  - Current idea is that the value response can either be a callable or just a value, so if more
    complex calculation for a single value is needed it can be specified. Something like:
    ```python
      mappings = {
      	b"status": b"ok!",
      	b"get_time": lambda b: datetime.datetime.now(),
      }
    ```
- Response list
  - For when you don't care about the different inputs and just want to specify the order of responses.
  - Just something like `x.set_ordered_responses([b"First", b"Second", b"Third"])`
- Single value
  - For when you just want the same value to be returned for all calls.
- Full callback
  - For when you want control over the entire response handling without any mappings, semantics will
    be slightly different for each class but will likely take in the class instance and the input buffer.

I will also supply factory methods for these stubs, so instead of requiring test authors to use the
constructor and then calls to set mappings etc (and also to prevent having to include this
information in the constructor) they can do something like
`stub = machine.UART.create_stub(uid=1, mappings={b"A": b"RESP-A"})`.
