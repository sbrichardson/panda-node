const usb = require('usb')
const log = require('./modules/log')

// Constants, Panda USB VendorID & ProductID
const VID = '0xbbaa'
const PID = '0xddcc'
const USB_DEBUG_LEVEL = 4

// Set debug level for usb library
usb.setDebugLevel(USB_DEBUG_LEVEL)

// Get device connected usb devices
let devices = usb.getDeviceList()

// Retrieve the panda usb device by id
const panda = usb.findByIds(VID, PID)

// Exit if panda not found by id
if (!panda) {
  throw new Error('Panda usb device not found')
}

log('panda object:', panda)

// Store usb device open status
let pandaDeviceStatus

try {
  console.info('\n\nattempting to open panda.........\n\n')
  panda.open()
  pandaDeviceStatus = true

} catch(e) {
  console.error('\n\nerror caught opening panda\n\n', e)
  pandaDeviceStatus = false
}

console.info('\n\n ** panda open? **', pandaDeviceStatus)

const pi0 = panda.interface(0)

console.info('\n\npanda - pi0:\n\n', pi0)

// Claim interface 0 on the panda
console.info('\n\nattempting to claim pi0 interface.........\n\n')
pi0.claim()

// Check if kernal driver is active, should be false typically.
console.info('\n\n** pi0.isKernelDriverActive()? **', pi0.isKernelDriverActive())


console.info('\n\n** Endpoints **\n\n')

// Store the endpoints for easier access
const panda_in = pi0.endpoints[0] // Device -> PC
const panda_out1 = pi0.endpoints[1] // PC -> Device
const panda_out2 = pi0.endpoints[2] // PC -> Device

log('panda_in', panda_in)
log('panda_in.direction', panda_in.direction)

// Setup event handlers for in (Device -> PC) data
panda_in.on('data', data => {
  log('panda_in data event, data:', data.toString('binary'), true)
})

panda_in.on('error', error => {
  log('***ERROR*** panda_in error event, error:', error)
})

panda_in.on('end', end => {
  log('panda_in end event, end:', end)
})

// Start retrieving data from panda
panda_in.startPoll()




// panda_in.transfer(64, function(error, data) {
//   error && console.error('** error in transfer **', error)
//   log('Transfer data size: 64 **', data.toString())
// })

// log('panda_in.device', panda_in.device)

// log('panda_out1', panda_out1)
// log('panda_out2', panda_out2)




// console.info('\n\n** Interfaces **\n\n')

// panda_out1.
