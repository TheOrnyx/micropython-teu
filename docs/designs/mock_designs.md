# Designs for the MicroPython Mocks

This is where I'll put my ideas and notes for designing the testing mocks along with the
final implementation. Please note that I'll kinda use this as a dumping ground for ideas
initially so anything here is subject to change while I'm still designing things.

## General Mock Designs

The website [xunitpatterns](http://xunitpatterns.com/) has some good info but they're very
opinionated about their terms. Might need to read more of this and reword some things.

Still a bit unsure about Mocks vs Fakes as a term, cuz they mostly seem to do the same
thing I'm ngl. Seems like Mocks are for verifying the user inputs and stuff whereas fakes
are for simulating the whole component, like an in memory database. idk I'm confused

## Ideas/ Things to look into

Gonna just put a list of some ideas or things I should look into here:

- Could use fluent interfaces for configuring the stubs, let the user compose the stubbed responses in one statement
  - Like going `stub_uart = UARTStubBuilder(id=1, singleton=True).with_mappings({"A": "Resp_A"}).build()`

## Communication devices

When discussing communication devices I am talking about the classes which perform a 2-way
communication with a hardware device on a bus by both writing to and reading from the bus. By
mocking these classes the test code can control the faked processing and responses from read and
write commands.

The classes in particular are:

- `UART`
- `SPI`
- `I2C`
- `I2CTarget` (maybe)

For designing the mocks for the communication devices I would like to settle on a design
that's consistent across the different types, so the basic design that I settle on should
be for each of these classes.

Ideally the chosen design should be flexible and make testing as easy as possible by
reducing the amount needed to implement in tests. They should also require very minimal
(or ideally no) changes to be made to the code being tested.

### Singletons

In order for the mock objects to be accessible in the main code being tested my idea is to
allow registering a created object to a static lookup table based on the ID, this lookup
table will then be used in the base classes `__new__` to return the mocked instance rather
than constructing a new one. So no changes need to be made to the code being tested.

### Class Structure

One of the first aspects I want to decide is how to structure the classes. Currently my
idea is to have the base class be a very simple stub interface which will have some
private helpers for child classes to use. This base class can be inherited and extended by
test authors which will allow them to redefine the basic operations and attributes fully.

I also had the idea of defining another class which extends the base and provides
functions and attributes that allow controlling the basic operations, either setting full
function callbacks for events or just specifying basic return values or input->output
bindings. The idea is to provide both a basic stub for users who want to extend it to
implement detailed fakes as well as a.

Current idea is maybe to have smth like this for UART (for example)

- `UART` (basic dummy or basic stub, meant to be extended to make fakes)
  - Could also have this be the regular stub but not sure
- `UARTStub`
  - Small programmable stub (could be done in fluent interface) with functions for defining read->response mappings

#### The Callback Stub

For the callback mock I want it to be a basic mock helper for basic scripting that doesn't
require writing a whole class (like when you just want to say, yeah this should return
`"OK"` when read.

Need to decide whether the callback functions should take in the UART object or the buffer
for more fine control.

Could either have a single class for the callback/ scripting mock with finetuned controls
or have a few different scriptable mocks, will have to decide later but I feel like having
a mock class for defining write->read mappings could be good. Like give it a dictionary like:

```python
# Input : Output
write_resp_mapping = {
	"AT" : "OK",
	"AT+CPWROFF" : "pwroff",
	# Etc
}
```

And it'll use that for loading the read responses. Could also potentially allow mapping to
functions too.
