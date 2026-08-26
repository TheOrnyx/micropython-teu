# Test Double Design Documentation

This is the folder where the documentation for the test double designs will be stored.

These files will contain information for each of the implemented classes explaining:

- What the purpose/ functionality of the class is in the original implementation. Basically the "problem" we'll be solving
- The goal of the design, the basics of how it should operate. The top-level details.
- Implementation details and how the implementation works. Mostly what each of the methods and stuff does and how a user would use it in testing.
  - More in-depth guides for how to use will likely be put in a different folder later.
- Quirks and limitations with the implementation. What couldn't be replicated and any notable quirks.

The [design_info.md](design_info.md) file contains design information for techniques that are
shared across multiple classes along with some general design philosophies.

Current docs:

- [uart.md](uart.md): Design doc for the `UART` classes test double.
