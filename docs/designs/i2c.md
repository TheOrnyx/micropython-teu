# The design, implementation, and usage of our I2C class

## Original board implementation

On the ESP32 port there are 2 types of `I2C`, `machine.I2C` for hardware I2C, and `machine.SoftI2C`
for software-based I2C.

For our implementation I will focus on `machine.I2C` as that is the main class typically
used. `SoftI2C` may be implemented but it depends on how we implement the base `I2C`, as they should
be identical apart from the SoftI2C not using an ID.

<details>
<summary> Important I2C Device details </summary>

## Understanding I2C

I2C can be a bit complicated and there's quite a few different types of devices I'lll need to
support so I'm just gonna document some stuff here so I can keep it in my mind.

> [!note]
> Leaving this section here post-implementation as it explains the different types of I2C devices
> that should be supported

#### Register and Non-Register devices

There seems to be 2 main types of I2C devices: those which are register-based (like the `DS1307`
RTC), and those which are just read and written to normally (usually simple devices like a GPIO
extension).

Register-based devices make up the majority of I2C devices and will likely be the main focus for our
test class design (with non-register based devices being supported but likely just with basic
response support). They work by the controller doing the normal transmission of the device address
and the read/write bit, they then also transmit the address of the register that they want to access
and then either write the data or initiate a new read to read the data.

Most register-based devices I've looked into seem to be mostly consistent with this, they keep an
internal register for the read/write register address, which needs to be set by the controller
before doing a read or a write. Then for multiple reads (say read 8 bytes) they'll typically just
keep incrementing and reading.

Most I2C devices use a normal 7-bit addressing mode, but there is technically support for a 10-bit
addressing mode where 2 bytes are used for the device address instead of 1. From my research I
haven't been able to find any mainstream devices that use 10-bit addressing so our implementation
will mostly ignore them.

Thankfully I don't need to worry about replicating most of this as MicroPython already abstracts a
lot of this for us, you don't need to manually do a write to set the target register address as you
can just `I2C.readfrom_mem()`. But it's nice to understand how it works under the hood on-board.

</details>

## Design Goals and ideas

The goal for this design is quite similar to the UART design, we want to be able to represent any
generic I2C device in a way that's easy for test authors to specify without a lot of boilerplate.

The base idea for the design is to separate the base I2C bus and the actual I2C devices as different
classes (so `I2C` and `I2CDevice`). This means that the bus can be mostly just a fake which operates
on devices, and the devices being the main configured test object that will be used to mock the
device that the code under test is using. This also just means it's much easier to define and reuse
test objects.

But there's a few aspects of `I2CDevice` that need to be decided, as the idea is to easily support
the vast majority of usecases without needing lots of extra boilerplate.

<!-- Talk about how since I2C is less structured on back and forth than UART we don't reall need to care about writes. -->

### Register addressing

As previously mentioned, most I2C devices are register-based with reads being able to sequentially
read a range of registers, or randomly access them. This means that we need to decide how the
registers should be represented.

> [!note] DS1307 example

> The DS1307 is a common I2C-based RTC device, it uses registers for the different parts of the
> datetime (`reg0` is seconds, `reg1` is minutes, etc).
>
> The device can be read through manually reading the registers or the whole date could be read by
> sequentially reading 7 bytes with a single `i2c.readfrom_mem(addr, reg0, 7)`.

Since code under test could either read a sequential register range, or read the registers
individually, it would be good to bake this support into our `I2CDevice` so test authors don't need
to define values for both the sequential and individual reads.

> [!note]

> It's also worth noting that while most drivers being tested are unlikely to use a mix of both
> sequential and random access of the same set of registers in the same unit of code, it's still
> nice to support the functionality to increase the code we can support and make our object more
> flexible.

The current idea is to have users set the register values through a call like
`.set_reg_data(start_addr, single_or_sequential_data)` and have that set-up a virtual set of
registers starting from `start_addr`. Then read calls can either access single registers or the
range, without the need for multiple declarations.

**Register sizing**:

There's another potential problem, some I2C devices don't stick to a standard register size. A read
from a register address could either return an 8-bit value or it could be a 16-bit value (as 2
reads), etc. The register sizes can also be mixed.

To support this my idea is to allow a `reg_size` when using the `.set_single_reg()` which will allow a
register to store multiple bytes without needing multiple addresses.

There are also devices that technically have responses that aren't 8-bit aligned (like the ADS1015
which has 12-bit responses), but the actual data transmission is 8-bit aligned with padding. So it
might be nice to have an option for padding.

**Sequential Read Wrapping**:

When you sequentially read from registers typically the device will keep reading each following
registers value. But if the controller keeps reading and the device runs out of registers it usually
ends up wrapping around to the start. But this functionality isn't in every device so we'd need to
decide how to handle this (or give users a way of controlling it).

## Implementation details

Due to time constraints the implementation of `I2C` ended up being quite limited, but it's a good
start. This section will explain the implementation details, some of which will be quite similar to
the design section.

### I2C and I2CDevice

The main part of this design is the separation of the I2C bus and the registered devices into
different classes.

The `fake_machine.I2C` class represents a fake simulated I2C bus which holds registered `I2CDevice`
objects and can communicate with them, and `fake_machine.I2CDevice` represents a fake I2C peripheral
which gets registered on the bus. This separation allows us to keep the basic I2C implementation
quite slim and focus on the device as the main test object. It also allows test authors to more
easily implement complex logic by subclassing `I2CDevice` rather than the bus.

The `I2CDevice` class will be quite similar to the `fake_machine.UART`, it will be a basic faked
implementation with utilities to allow test authors to program it as the kind of device they need by
configuring how it responds to reads and writes.

The implementation of `I2CDevice` will focus on memory-based I2C devices as they are the most common
form of I2C device, they are communicated with using the `.readfrom_mem(...)` instead of
`readfrom()`.

### Controlling the read responses

In the current implementation of `I2CDevice` a device can be read through either a memory address
with `.readfrom_mem()` or read normally with `.readfrom()`, with each having a different way to
configure and use.

> [!note]
> In a real I2C device a memory address would be readable through writing the register address
> first, but due to time constraints and ease of testing register-based reads and regular reads are
> specified separately, but all drivers I've encountered use the helper memory read methods instead
> of manually writing the address. (See [future work](#Future-Work) for more info)

#### **Non-memory-based reads:**

Regular non-register-based devices that get read with `.readfrom()` are pretty basic and are
represented with a basic response payload in the form of a bytearray which can be set by the user
through a call to `.set_read_response()` which will set the `read_response` that the regular reads
will load data from. Unfortunately, there isn't much support beyond that at this time.

If the code under test attempts to read more bytes than is present in the `read_response` then a
`ValueError` will be raised, this obviously isn't accurate to a real device but is fine for a test
environment by specifying that you must map data that will be read (see [future
work](#Improved-configurability-and-error-handling) for more info).

```python
i2c = fake_machine.I2C(0)
device = fake_machine.I2CDevice(addr=0x9, i2c_bus=i2c)
device.set_read_response(b"\x01\x02\x03")

i2c.readfrom(0x9, nbytes=3)  # Will respond with b"\x01\x02\x03"
i2c.readfrom(0x9, nbytes=2)  # Will respond with b"\x01\x02"
i2c.readfrom(0x9, nbytes=4)  # Will raise a ValueError
```

#### **Memory-based reads:**

Devices that have memory/ registers that get read with `.readfrom_mem()` can be configured to have a
set of faked registers at specific memory addresses which internally are represented with a
dictionary of address to bytearray object which holds the backing data. Then when the devices memory
gets read it starts from the starting address and reads the `nbytes` from the register, sequentially
reading the next register/s if `nbytes` is larger than the single register and there's a register
mapped to the following address. So a 2-byte register followed by a 1-byte register will be both be
read with `nbytes=3`.

Registers can be configured through one of the following methods:

A single register of any size can be defined by calling `.set_single_reg(reg_addr, data)` which will
create a single register entry at `reg_addr` containing the provided data. This method can also be
used to set a register to an int value, which will be converted with `int.to_bytes()`:

```python
device.set_single_reg(0x2, b"\x01\x02")  # readfrom_mem(dev_addr, 0x2, 2) would read b"\x01\x02"
device.set_single_reg(0x3, 772, int_nbytes=2, endianness="big")  # reg_0x3 will contain b"\x03\x04"
# At this point registers dict looks like {2: bytearray(b'\x01\x02'), 3: bytearray(b'\x03\x04')}
i2c.readfrom_mem(dev_addr, 0x2, nbytes=4)  # Will read b"\x01\x02\x03\x04"
i2c.readfrom_mem(dev_addr, 0x2, nbytes=5)  # Will raise a ValueError, no 0x4 register to read after 0x3
```

A sequential set of registers can be set with either `.set_reg_block(start_addr, data)` which will
set a series of sequential 1-byte registers, one for each byte in the input. Or
`.set_reg_list(start_addr, [data_list])` which will make a series of sequential registers with
varying sizes, with each register containing the data from the respective `[data_list]` entry.

```python
device.set_reg_block(0x2, b"\x01\x02\x03")  # Makes 3 1-byte registers
# Registers would be {2: bytearray(b'\x01'), 3: bytearray(b'\x02'), 4: bytearray(b'\x03')}
device.set_reg_list(0x5, [b"\x04\x05", b"\x06"])  # Creates reg_0x5 with 2 bytes and 0x6 with 1 byte.
i2c.readfrom_mem(dev_addr, 0x2, nbytes=6) # Will read b"\x01\x02\x03\x04\x05\x06"
```

### Controlling write handling

The default implementation of `I2CDevice` can optionally be configured to handle write operations if
needed. By default writing does nothing but return the expected response (length of data for regular
write and `None` for memory write).

**Non-memory-based writes:**

For regular non-register-based devices written with `I2C.writeto(...)` a callback can be set with
`.set_write_callbacks(write_cb=..)`, this callback takes in the `I2CDevice` being written to, along
with the data being written.

**Memory-based writes:**

There is a bit more supported for register-based devices written to with `I2C.writeto_mem(...)`. A
basic callback can still be set with `.set_write_callbacks(memwrite_cb=..)` and takes in the
`I2CDevice` being written to, the address of the register being written to, and the data being
written.

By calling `device.allow_register_overwriting()` the device will switch to overwriting the
configured register data when written to.

```python
import fake_machine
i2c = fake_machine.I2C(0)
dev_addr = 0x8
device = fake_machine.I2CDevice(dev_addr, i2c)

# Set block of registers from 0x0->0x3, one byte in each
reg_data = b"\x01\x02\x03\x04"
device.set_reg_block(0x0, reg_data)
assert i2c.readfrom_mem(dev_addr, 0x0, len(reg_data)) == reg_data

# Allow overwriting then write will overwrite walked registers
write_data = b"moo"  # Only 3 bytes so \x04 byte will be left untouched
device.allow_register_overwriting()
i2c.writeto_mem(dev_addr, 0x0, write_data)

assert i2c.readfrom_mem(dev_addr, 0x0, len(reg_data)) == write_data + b"\x04"
```

<!-- TODO - add an examples section with examples for doing stuff like subtyping -->

## Dev notes

Just some notes about board version while developing

- If `I2C()` is called with either id=-1 or no id with other arguments it attempts to use softi2c and warns
  - Likely won't implement this specific thing but is good to note

## Future Work

Some ideas for future features that could be implemented to improve the devices our class can easily
simulate.

### SoftI2C support

Currently `machine.SoftI2C` is implemented in `fake_machine.SoftI2C` as a basic subclass of `I2C`
with slightly different initialization (no ID) and a singleton instead of a multiton.

However, this basic implementation could be improved for further work. A proper implementation would
need the `read()`, `write()`, `start()`, and `stop()` methods and maybe communicate through
bit-banging the Pins.

### Register reading without mem method

I may be incorrect about this, but I'm pretty sure that the `*_mem()` read and write methods are
convenience methods, meaning that the functionality of them can be replicated with regular
operations.

A memory read involves first writing the address you want to access and then reading, this means it
should be replicable with the regular methods. Currently due to our separation of memory reads and
regular reads this functionality isn't supported, as most code for register-based devices I've seen
uses the memory methods explicitly. It would be good to add the ability for regular reads to be able
to read from the registers but currently considering out of scope due to time.

An example of memory being accessed like this can be seen in this [old DS1307
driver](https://www.fredscave.com/drivers/017-ds1307.html), in the get_reg (even though this driver
is outdated as `write` is now `writeto`.

It would probably be best to implement this by having there either be assigned register data or
assigned regular data and have only one operation be allowed at a time.

I also assume that this is the reason for the `stop` parameter in the regular read methods, to allow
users to read a few bytes without sending the stop signal (which doesn't terminate the
communication), and perform another read later to read more.

### Better support for non-register based devices

Due to time constraints the `I2CDevice` mainly focuses on supporting register-based devices, with
support for regular devices being mostly implemented by setting a read buffer to be used for regular
`readfrom()` calls, with the option for a write callback if needed.

To improve our test support it could be nice to implement additional features to support changing
the read contents when a write occurs, like with UART. Currently not prioritizing as can't think of
enough devices that would be used like that to warrant implementation.

### Improved configurability and error handling

Currently the `I2CDevice` implementation doesn't have the best error handling. Due to time
constraints I made the design quite strict, reads and writes above the defined ranges currently
raise a `ValueError`. I decided on this as it made the most sense for testing and I didn't have
access to an I2C setup to inspect how MicroPython handles these on the ESP32.

But obviously for a future improved implementation it would be better to allow test authors to
configure how the device handles these anomalous operations, as each device could handle them
differently. Such as longer reads which will end up wrapping around in some real devices.
