# panda-node
Node.js Library for the [Panda](https://shop.comma.ai/products/panda-obd-ii-dongle) ODBII Dongle from [comma.ai](https://github.com/commaai)


### Inspiration
Most of the comma.ai libraries are written in Python, I'm more of a JavaScript Dev.


### Usage Notes
I've tested working on Ubuntu 16.04.3 in Parallels on an iMac Pro with High Sierra. I was receiving an error when attempting to use the usb library on the mac directly. I've tested the white & grey models successfully.


### Development Notes
I'm new to USB development so there are extra comments scattered around in the code currently. As this repo develops it will become more structured and usable. I'll list in on npm then. Currently I'm reverse engineering the Python code within the official [panda repo](https://github.com/commaai/panda) from comma.ai. The main   [`Panda`](https://github.com/commaai/panda/blob/master/python/__init__.py) class (linked to comma.ai's panda code) has a lot of the functionality. 

### Installation

```bash
# clone repo

cd panda-node
yarn

# currently prompts for sudo permissions for usb access
```

### Run

```bash
# Ensure Panda is connected and not being used by another program

yarn start

# Check console logs for test data output.
```
