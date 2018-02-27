# panda-node
Node.js Library for the [Panda](https://shop.comma.ai/products/panda-obd-ii-dongle) ODBII Dongle from [comma.ai](https://github.com/commaai)


## Inspiration
Most of the comma.ai libraries are written in Python, I'm more of a JavaScript Dev.


## Usage Notes
I've tested working on Ubuntu 16.04.3 in Parallels on an iMac Pro with High Sierra, and on the iMac within High Sierra directly. I've tested the white & grey models successfully.


## Development Notes
I'm new to USB development so there are extra comments scattered around in the code currently. As this repo develops it will become more structured and usable. I'll list in on npm then. Currently I'm reverse engineering the Python code within the official [panda repo](https://github.com/commaai/panda) from comma.ai. [This class](https://github.com/commaai/panda/blob/master/python/__init__.py) from comma.ai's code contains a lot of functionality. I've temporarily copied that code for reference and added notes. See [`modules/_reference/__init__.py`](modules/_reference/__init__.py)

## Installation

```bash
# clone repo

cd panda-node
yarn

# currently prompts for sudo permissions for usb access
```

## Run

```bash
# Ensure Panda is connected and not being used by another program

yarn start

# Check console logs for test data output.
```
