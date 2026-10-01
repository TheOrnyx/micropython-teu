# PythingsOS SIM800L Driver test

This folder contains a custom test file based on the [PythingsOS SIM800L GPRS driver](https://github.com/pythings/Drivers/blob/master/SIM800L.py).<br>
This device uses the same AT command syntax as the Quilty projects modem.

This driver handles the sending of AT commands through UART and the processing and parsing of the
responses. There are helper functions that parse specific responses, such as `.scan_networks()`
which returns a dictionary of available networks.

Currently the original repo has a few tests implemented by taking the function that reads and
processes the raw UART response and overriding it with one that returns an expected processed
output. But there's only two tests and neither covers the actual UART response processing logic.

Our custom tests will properly test this processing logic and that the expected raises occur. We
will also test some of the helper methods to make sure they parse the data correctly.

The original License for this driver is also stored in this folder, just in case.
