const usb = require('usb')
const log = require('./modules/log')


/** Constants, Panda USB VendorID & ProductID */
const VID = '0xbbaa'
const PID = '0xddcc'
const USB_DEBUG_LEVEL = 1

/** Set debug level for usb library */
usb.setDebugLevel(USB_DEBUG_LEVEL)
// log('** usb object ***\n\n', usb)

/** Get device connected usb devices */
let devices = usb.getDeviceList()

/** Retrieve the panda usb device by id */
const panda = usb.findByIds(VID, PID)

/** Exit if panda not found by id */
if (!panda) {
  throw new Error('Panda usb device not found')
}

// log('panda object:', panda)

/** Store usb device open status */
let pandaDeviceStatus

try {
  log('Attempting to open panda.........\n')
  panda.open()
  pandaDeviceStatus = true

} catch(e) {
  console.error('\n\n** Error caught opening panda ** \n\n', e)
  pandaDeviceStatus = false
}

log('Panda open?', pandaDeviceStatus)

const _handle = panda.interface(0)

// console.info('\n\n**Panda - _handle **\n', _handle)

/** Claim interface 0 on the panda */
log('Attempting to claim _handle (pi0) interface...')
_handle.claim()

/** Check if kernal driver is active, should be false typically. */
// log('_handle.isKernelDriverActive()? **', _handle.isKernelDriverActive())


/** Store the endpoints for easier access */
const panda_in = _handle.endpoints[0] /* Device -> PC */
const panda_out1 = _handle.endpoints[1] /* PC -> Device */
const panda_out2 = _handle.endpoints[2] /* PC -> Device */

// log('panda_in\n', panda_in)
// log('panda_in.direction', panda_in.direction)
// log('panda.controlTransfer? **\n\n', panda.controlTransfer)
// log('usb.LIBUSB_ENDPOINT_IN', usb.LIBUSB_ENDPOINT_IN)


/** Generic callback for testing reading from Panda */
const _callback = (message, error, data) => {
  console.info('\n---------------------------------------------')
  error && console.error('_callback - error', error)
  // log(`${message} - data`, data)
  log(`${message}, data.toString():`, data.toString())
  log(`${message} - Buffer data.length`, data.length)
  log(`${message}, data.toJSON():`, data.toJSON())
  console.info('\n\n')
}

/** Callback for processing the health data retrieved from Panda */
const _getHealth = (error, data) => {
  console.info('\n---------------------------------------------')
  error && console.error('_getHealth error', error)
  const { data: d } = data.toJSON()
  log('_getHealth - d', d)
  const result = {
    "voltage": d[0],
    "current": d[1],
    "started": d[2],
    "controls_allowed": d[3],
    "gas_interceptor_detected": d[4],
    "started_signal_detected": d[5],
    "started_alt": d[6]
  }
  log('Panda Health (May not be interpreted correctly, in progress)\n\n', result)
}

/** Callback for is Grey Model Panda */
const _isGrey = (error, data) => {
  console.info('\n---------------------------------------------')
  error && console.error('_isGrey error', error)
  const { data: d } = data.toJSON()
  log('_isGrey - d', d)
  log('Panda is Grey Model?)', d && d[0] === 1 ? 'TRUE' : 'FALSE')
}



////////////////
// Test Reads //
////////////////


/** Attempt to get panda secret */
panda.controlTransfer(
  0xc0,
  0xd0,
  1,
  0,
  0x10,
  _callback.bind({}, 'Panda Get Secret')
)

/** Attempt to get panda serial */
panda.controlTransfer(
  0xc0,
  0xd0,
  0,
  0,
  0x20,
  _callback.bind({}, 'Panda Get Serial')
)

/** Attempt to get panda health info */
panda.controlTransfer(
  0xc0,
  0xd2,
  0,
  0,
  13,
  _getHealth
)

/** Attempt to check if panda is grey model */
panda.controlTransfer(
  0xc0,
  0xc1,
  0,
  0,
  0x40,
  _isGrey
)

/** Attempt to get panda version */
panda.controlTransfer(
  0xc0,
  0xd6, /* 0xd6 is the type for version info */
  0,
  0,
  0x40,
  _callback.bind({}, 'Panda Version')
)
