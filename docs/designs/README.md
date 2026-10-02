# Test Double Design Documentation

This is the folder where the documentation for the test double designs will be stored.

These files will contain information for the implemented test fake classes explaining:

- What the purpose/ functionality of the class is in the original implementation. Basically the "problem" we'll be solving
- The goal of the design, the basics of how it should operate. The top-level details.
- Implementation details and how the implementation works. Mostly how the class works and how it can be used for testing.
- Quirks and limitations with the implementation. What couldn't be replicated and any notable quirks.

The [design_info.md](design_info.md) file contains design information for techniques that are
shared across multiple classes along with some general design philosophies used in the designs.

Current docs:

- [design_info.md](design_info.md): General design info and approaches (bit old).
- [uart.md](uart.md): Design documentation for the `UART` classes test fake.
- [i2c.md](i2c.md): Design documentation for the `I2C` classes test fake.
