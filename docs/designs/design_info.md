# Techniques and Patterns used for the test doubles

This file will detail some of the shared techniques and design philosophies used in my test doubles.
It will also explain some of the general design decisions I made and why.

## Additional Info and Design Goals

Some relevant info before we get into the important stuff along with what our designs hope to
achieve.

### Resources

A list of helpful resources for designing my objects, will make a proper literature review for these later.

- https://www.jamesshore.com/v2/projects/nullables/testing-without-mocks: Great article for learning how to write bespoke test doubles without mock frameworks
- https://abseil.io/resources/swe-book/html/ch13.html: Google software engineering book test double chapter
- http://xunitpatterns.com/: Great site for test term definitions and other stuff
- Book: Test Driven Development for Embedded C (talks about this kinda stuff but more C oriented)

### Different Types of Test Objects

There are quite a few different types of test objects which fall under the category of "Test
Double": Mocks, Stubs, Fakes, Spies. However, despite having formal definitions, the terms for these
tend to be used quite loosely and interchangably in literature and resources, with "Mock object"
often being used to refer to the whole class of test doubles (likely due to the popularity and
prevalence of Mocking Frameworks in such literature) which can cause some confusion when explaining
things. A good example of this confusion is explained in [The Little Mocker](https://blog.cleancoder.com/uncle-bob/2014/05/14/TheLittleMocker.html).

The website [xunitpatterns](http://xunitpatterns.com/) by Gerard Meszaros provides some good
concrete definitions for each object type which I'll summarize here so you are aware of the formal
definitions. But first it's worth noting that due to the uniqueness of the problem we're addressing
our designs may end up fitting into multiple of these categories as we are designing general objects
which users can use for their own testing. So our usage of the terms might be a bit inconsistent, as
unfortunately "mock" is a good word to describe what our objects do (as they are "mocking" the
functionality of the hardware classes) and terms like "stub" are good for describing usage.

<!-- Have a better explanation that since this is a unique problem we can't stick to just one type sometimes, blegh -->

Based on what I've read on the xunitpatterns site, along with some other books and web resources,
these seem to be the best definitions for the concrete terms:

- **Test Double**: Overall term for any kind of faked testing object (all of the terms below are doubles)
- **Dummy Object**: An object that just fills out the interface but doesn't perform any functionality, mostly used to allow code to compile and run.
- **Test Stub**: Basic double where the tester provides the return values for function calls.
- **Test Spy**: Basically just a Stub that also records the values passed in, for later verification in tests.
- **Mock Object**: Similar to a spy/ stub but user provides the expected method calls and their arguments and the test asserts these calls took place.
  - Mocks can have quite a few different variations however, some are strict on the order of expectations and some don't care, frustrating.
- **Fake Object**: A simulated version of a depended on component which provides the same functionality but without requiring the actual object.
  - So for example: instead of running your database code tests on a real database you use a fake in-memory one that operates the same.

As previously mentioned, due to our projects uniqueness and to improve ease of testing most of our
objects are designed as a mix of some of these types. For example, for `UART` it needs to have some
faked functionality as code typically doesn't just go "write and then read", usually code will call
write, then verify all data was written via the return value, then it'll check `any()` to see how
much data can be read, and then a read finally occurs.<br>
So it's much easier and useful to design our `machine.UART` as a simulated fake which can easily be
programmed as a stub or a mock by users.

This is also why just writing dummy objects that fill out the missing classes methods and attributes
and asking users to use a mocking framework like `unittest.mock` to define functionality doesn't
really work as the objects have more complex functionality behind them which would be either
impossible or very cumbersome to describe.

Overall the goal with these designs is not to create classes that fit into a strict type but rather
to design classes which can fit into whatever the tests require with ease.

## Techniques

These are the shared techniques and patterns used for our designs.

### Multiton Registry for Shared State

To better support already existing test code I plan to have the creation of these objects use the
Multiton pattern. This means that the classes store a dictionary registry of ID's to existing
instances and when code attempts to create a new instance with an ID that exists in the registry it
will receive the already created instance.

This means that test code can create their test object, configure it for testing, and then when the
code they're testing runs and creates its object it'll receive the configured test version. This
helps support existing code without the need to rewrite it to support dependency injection.

> This is also how MicroPython handles objects on-board, if ESP32 code creates 2 `UART` objects with
> the same ID then they are both the same object in memory.
>
> ```python
> >>> u1 = machine.UART(1)
> >>> u2 = machine.UART(1)
> >>> u1 is u2
> True
> >>> print(f"{id(u1)} = {id(u2)}")
> 1073545952 = 1073545952
> ```

<!-- Removed part about class structure as not too relevant to current state of project -->
