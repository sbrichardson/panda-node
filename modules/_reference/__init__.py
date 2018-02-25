# python library to interface with panda
from __future__ import print_function
import binascii
import struct # https://www.npmjs.com/package/struct
import hashlib
import socket
import usb1 # https://github.com/vpelletier/python-libusb1 --> node.js https://github.com/tessel/node-usb
import os
import time
import traceback

from dfu import PandaDFU
from esptool import ESPROM, CesantaFlasher
from flash_release import flash_release
from update import ensure_st_up_to_date
from serial import PandaSerial

__version__ = '0.0.6'

BASEDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../")

DEBUG = os.getenv("PANDADEBUG") is not None


def build_st(target, mkfile="Makefile"):
  from panda import BASEDIR
  assert(os.system('cd %s && make -f %s clean && make -f %s %s >/dev/null' % (os.path.join(BASEDIR, "board"), mkfile, mkfile, target)) == 0)



# Notes
#
# https://www.rapidtables.com/convert/number/hex-to-decimal.html
#
# - Removed blocks of code and moved to end of file
# - Added comments near hexadecimal (0x) usage for clarity
#
# None ~ undefined
#
# "__init__" is a reserved method in python classes. It is known as a constructor in object oriented concepts.
# This method called when an object is created from the class and it allow the class to initialize the attributes of a class.
#
# b'' usage - Bytes literals are always prefixed with 'b' or 'B'; they produce an instance of the bytes type instead of the str type.
# They may only contain ASCII characters; bytes with a numeric value of 128 or greater must be expressed with escapes.
#
# int() usage - Return an integer object constructed from a number or string x, or return 0 if no arguments are given.
# If x is a number, it can be a plain integer, a long integer, or a floating point number.
#



# ***************************
# *** libusb1 controlRead ***
# ***************************
#
# def controlRead(self, request_type, request, value, index, length, timeout=0):
#
# usage example:
#   def get_version(self):
#     return self._handle.controlRead(Panda.REQUEST_IN, 0xd6, 0, 0, 0x40) # 0xd6 = 214 | 0x40 = 64
#
# -------------------
# Arguments from Example
# -------------------
#
# self = Panda.REQUEST_IN
# request_type = 0xd6 | 214
# value = 0
# index = 0
# length = 0x40 | 64
#
# -------------------
# Notes - libusb http://libusb.sourceforge.net/api-1.0/group__syncio.html#gadb11f7a761bd12fc77a07f4568d56f38
# -------------------
#
# 1. value and index are typically 0
#
# 2. length is usually a multiple of 16, 32, 64 --> 0x10, 0x20, 0x40
#
# 3. self is either Panda.REQUEST_IN or REQUEST_OUT from usb1.ENDPOINT_IN
#
# 4. the only unique arguments are typically:
#  - request_type (libusb: bRequest - the request field for the setup packet)
#  - length (libusb: wLength - Number of bytes to transfer.)
#
#
# -------------------
# node-usb conversion usage
# -------------------
#
# Full/Device usage
# Device.controlTransfer(bmRequestType, bRequest, wValue, wIndex, data_or_length, callback(error, data))
#
# Simple/Endpoint specific usage
# InEndpoint.transfer(length, callback(error, data))
#
#
# Python version:
#
#   def get_version(self):
#     return self._handle.controlRead(Panda.REQUEST_IN, 0xd6, 0, 0, 0x40) # 0xd6 = 214 | 0x40 = 64
#
# Node.js version (within an ES6 class, dev version, in progress, will reduce complexity after testing), see
# https://github.com/RogerHardiman/tenx_usb_missile_launcher/blob/e22415298ed5450a43358e30867f05ce6c141cfc/tenx_driver.js
# for random example of usb lib in node.js
#
#
#
#  _getVersion = (self) => {
#
#    /**
#     * bmRequestType - from libusb enum docs, stored on usb() object
#     *
#     * usb.LIBUSB_TRANSFER_TYPE_CONTROL = 0
#     * usb.LIBUSB_TRANSFER_TYPE_ISOCHRONOUS = 1
#     * usb.LIBUSB_TRANSFER_TYPE_BULK = 2
#     * usb.LIBUSB_TRANSFER_TYPE_INTERRUPT = 3
#     *
#     */
#    const bmRequestType = 3 // (verify 3) see above, enum one of [0, 1, 2, 3]
#    const bRequest = 0xd6
#    const wValue = 0
#    const wIndex = 0
#    const length = 0x40
#
#    const callback = (error, data) => {
#      /** TODO - es6 async/await instead of callback */
#      error && console.info('_getVersion callback, error', error)
#      console.info('_getVersion callback, data', data)
#    }
#
#    return self._handle.controlTransfer(
#      bmRequestType,
#      bRequest,
#      wValue,
#      wIndex,
#      length,
#      callback /** TODO - es6 async/await */
#    )
#  }
#
#
#
#
#
# *** From libusb, controlRead here for usage example
#
def controlRead(
    self, request_type, request, value, index, length, timeout=0):
    """
    Synchronous control read.
    timeout: in milliseconds, how long to wait for data. Set to 0 to
      disable.
    See controlWrite for other parameters description.
    To avoid memory copies, use an object implementing the writeable buffer
    interface (ex: bytearray) for the "data" parameter.
    Returns received data.
    """

    # pylint: disable=undefined-variable
    request_type = (request_type & ~ENDPOINT_DIR_MASK) | ENDPOINT_IN

    # pylint: enable=undefined-variable
    data, data_buffer = create_binary_buffer(length)

    transferred = self._controlTransfer(
        request_type, request, value, index, data, length, timeout,
    )

    return data_buffer[:transferred]

# **********************
# *** Canbus Parsing ***
# **********************

def parse_can_buffer(dat):
  ret = []
  for j in range(0, len(dat), 0x10): # 0x10 = 16
    ddat = dat[j:j+0x10]
    f1, f2 = struct.unpack("II", ddat[0:8])
    extended = 4
    if f1 & extended:
      address = f1 >> 3
    else:
      address = f1 >> 21
    dddat = ddat[8:8+(f2&0xF)]
    if DEBUG:
      print("  R %x: %s" % (address, str(dddat).encode("hex")))
    ret.append((address, f2>>16, dddat, (f2>>4)&0xFF))
  return ret



# *** normal mode ***

class Panda(object):

  SAFETY_NOOUTPUT = 0
  SAFETY_HONDA = 1
  SAFETY_TOYOTA = 2
  SAFETY_TOYOTA_NOLIMITS = 0x1336 # 0x1336 = 4918
  SAFETY_ALLOUTPUT = 0x1337 # 0x1337 = 4919
  SAFETY_ELM327 = 0xE327 # 0xE327 = 58151

  SERIAL_DEBUG = 0
  SERIAL_ESP = 1
  SERIAL_LIN1 = 2
  SERIAL_LIN2 = 3

  GMLAN_CAN2 = 1
  GMLAN_CAN3 = 2

  REQUEST_IN = usb1.ENDPOINT_IN | usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE
  REQUEST_OUT = usb1.ENDPOINT_OUT | usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE

  def __init__(self, serial=None, claim=True):
    self._serial = serial
    self._handle = None
    self.connect(claim)

  def close(self):
    self._handle.close()
    self._handle = None


  def connect(self, claim=True, wait=False):
    if self._handle != None:
      self.close()

    if self._serial == "WIFI":
      self._handle = WifiHandle()
      print("opening WIFI device")
      self.wifi = True
    else:
      context = usb1.USBContext()
      self._handle = None
      self.wifi = False

      while 1:
        try:
          for device in context.getDeviceList(skip_on_error=True):
            #print(device)
            if device.getVendorID() == 0xbbaa and device.getProductID() in [0xddcc, 0xddee]: # 0xbbaa = 48042 | 0xddcc = 56780 | 0xddee = 56814
              try:
                this_serial = device.getSerialNumber()
              except Exception:
                continue
              if self._serial is None or this_serial == self._serial:
                self._serial = this_serial
                print("opening device", self._serial, hex(device.getProductID()))
                self.bootstub = device.getProductID() == 0xddee # 0xddee = 56814
                self.legacy = (device.getbcdDevice() != 0x2300) # 0x2300 = 8960
                self._handle = device.open()
                if claim:
                  self._handle.claimInterface(0)
                  #self._handle.setInterfaceAltSetting(0, 0) #Issue in USB stack
                break
        except Exception as e:
          print("exception", e)
          traceback.print_exc()
        if wait == False or self._handle != None:
          break
    assert(self._handle != None)
    print("connected")


  def call_control_api(self, msg):
    self._handle.controlWrite(Panda.REQUEST_OUT, msg, 0, 0, b'')

  # ******************* health *******************

  def health(self):
    dat = self._handle.controlRead(Panda.REQUEST_IN, 0xd2, 0, 0, 13) # 0xd2 = 210
    a = struct.unpack("IIBBBBB", dat)
    return {"voltage": a[0], "current": a[1],
            "started": a[2], "controls_allowed": a[3],
            "gas_interceptor_detected": a[4],
            "started_signal_detected": a[5],
            "started_alt": a[6]}

  # ******************* control *******************

  def enter_bootloader(self):
    try:
      self._handle.controlWrite(Panda.REQUEST_OUT, 0xd1, 0, 0, b'') # 0xd1 = 209
    except Exception as e:
      print(e)
      pass

  def get_version(self):
    return self._handle.controlRead(Panda.REQUEST_IN, 0xd6, 0, 0, 0x40) # 0xd6 = 214 | 0x40 = 64

  def is_grey(self):
    ret = self._handle.controlRead(Panda.REQUEST_IN, 0xc1, 0, 0, 0x40) # 0xc1 = 193 | 0x40 = 64
    return ret == "\x01"

  def get_serial(self):
    dat = self._handle.controlRead(Panda.REQUEST_IN, 0xd0, 0, 0, 0x20) # 0xd0 = 208 | 0x20 = 32
    hashsig, calc_hash = dat[0x1c:], hashlib.sha1(dat[0:0x1c]).digest()[0:4] # 0x1c = 28
    assert(hashsig == calc_hash)
    return [dat[0:0x10], dat[0x10:0x10+10]] # 0x10 = 16

  def get_secret(self):
    return self._handle.controlRead(Panda.REQUEST_IN, 0xd0, 1, 0, 0x10) # 0xd0 = 208 | 0x10 = 16

  # ******************* configuration *******************

  def set_usb_power(self, on):
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xe6, int(on), 0, b'') # 0xe6 = 230

  def set_esp_power(self, on):
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xd9, int(on), 0, b'') # 0xd9 = 217

  def esp_reset(self, bootmode=0):
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xda, int(bootmode), 0, b'') # 0xda = 218
    time.sleep(0.2)

  def set_safety_mode(self, mode=SAFETY_NOOUTPUT):
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xdc, mode, 0, b'') # 0xdc = 220

  def set_can_forwarding(self, from_bus, to_bus):
    # TODO: This feature may not work correctly with saturated buses
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xdd, from_bus, to_bus, b'') # 0xdd = 221

  def set_gmlan(self, bus=2):
    if bus is None:
      self._handle.controlWrite(Panda.REQUEST_OUT, 0xdb, 0, 0, b'') # 0xdb = 219
    elif bus in [Panda.GMLAN_CAN2, Panda.GMLAN_CAN3]:
      self._handle.controlWrite(Panda.REQUEST_OUT, 0xdb, 1, bus, b'') # 0xdb = 219

  def set_can_loopback(self, enable):
    # set can loopback mode for all buses
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xe5, int(enable), 0, b'') # 0xe5 = 229

  def set_can_speed_kbps(self, bus, speed):
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xde, bus, int(speed*10), b'') # 0xde = 222

  def set_uart_baud(self, uart, rate):
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xe4, uart, rate/300, b'') # 0xe4 = 229

  def set_uart_parity(self, uart, parity):
    # parity, 0=off, 1=even, 2=odd
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xe2, uart, parity, b'') # 0xe2 = 226

  def set_uart_callback(self, uart, install):
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xe3, uart, int(install), b'') # 0xe3 = 227


  # ******************* can *******************

  def can_send_many(self, arr):
    snds = []
    transmit = 1
    extended = 4
    for addr, _, dat, bus in arr:
      assert len(dat) <= 8
      if DEBUG:
        print("  W %x: %s" % (addr, dat.encode("hex")))
      if addr >= 0x800:                                           # 0x800 = 2048
        rir = (addr << 3) | transmit | extended
      else:
        rir = (addr << 21) | transmit
      snd = struct.pack("II", rir, len(dat) | (bus << 4)) + dat
      snd = snd.ljust(0x10, b'\x00')                              # 0x10 = 16
      snds.append(snd)

    while True:
      try:
        #print("DAT: %s"%b''.join(snds).__repr__())
        if self.wifi:
          for s in snds:
            self._handle.bulkWrite(3, s)
        else:
          self._handle.bulkWrite(3, b''.join(snds))
        break
      except (usb1.USBErrorIO, usb1.USBErrorOverflow):
        print("CAN: BAD SEND MANY, RETRYING")

  def can_send(self, addr, dat, bus):
    self.can_send_many([[addr, None, dat, bus]])

  def can_recv(self):
    dat = bytearray()
    while True:
      try:
        dat = self._handle.bulkRead(1, 0x10*256) # 0x10 is 16, (16*256=4096)
        break
      except (usb1.USBErrorIO, usb1.USBErrorOverflow):
        print("CAN: BAD RECV, RETRYING")
    return parse_can_buffer(dat)

  def can_clear(self, bus):
    """Clears all messages from the specified internal CAN ringbuffer as
    though it were drained.

    Args:
      bus (int): can bus number to clear a tx queue, or 0xFFFF (65535) to clear the
        global can rx queue.

    """
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xf1, bus, 0, b'') # 0xf1 = 241

  # ******************* serial *******************

  def serial_read(self, port_number):
    ret = []
    while 1:
      lret = bytes(self._handle.controlRead(Panda.REQUEST_IN, 0xe0, port_number, 0, 0x40)) # 0xe0 = 224 | 64
      if len(lret) == 0:
        break
      ret.append(lret)
    return b''.join(ret)

  def serial_write(self, port_number, ln):
    ret = 0
    for i in range(0, len(ln), 0x20): # 0x20 = 32
      ret += self._handle.bulkWrite(2, struct.pack("B", port_number) + ln[i:i+0x20]) # 0x20 = 32
    return ret

  def serial_clear(self, port_number):
    """Clears all messages (tx and rx) from the specified internal uart
    ringbuffer as though it were drained.

    Args:
      port_number (int): port number of the uart to clear.

    """
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xf2, port_number, 0, b'') # 0xf2 = 242

  # ******************* kline *******************

  # pulse low for wakeup
  def kline_wakeup(self):
    self._handle.controlWrite(Panda.REQUEST_OUT, 0xf0, 0, 0, b'') # 0xf0 = 240

  def kline_drain(self, bus=2):
    # drain buffer
    bret = bytearray()
    while True:
      ret = self._handle.controlRead(Panda.REQUEST_IN, 0xe0, bus, 0, 0x40) # 0xe0 = 224 | 0x40 = 64
      if len(ret) == 0:
        break
      bret += ret
    return bytes(bret)

  def kline_ll_recv(self, cnt, bus=2):
    echo = bytearray()
    while len(echo) != cnt:
      echo += self._handle.controlRead(Panda.REQUEST_OUT, 0xe0, bus, 0, cnt-len(echo))
    return echo

  def kline_send(self, x, bus=2, checksum=True):
    def get_checksum(dat):
      result = 0
      result += sum(map(ord, dat)) if isinstance(b'dat', str) else sum(dat)
      return struct.pack("B", result % 0x100) # 0x100 = 256

    self.kline_drain(bus=bus)
    if checksum:
      x += get_checksum(x)
    for i in range(0, len(x), 0xf):
      ts = x[i:i+0xf]                                   # 0xf = 15
      self._handle.bulkWrite(2, chr(bus).encode()+ts)
      echo = self.kline_ll_recv(len(ts), bus=bus)
      if echo != ts:
        print("**** ECHO ERROR %d ****" % i)
        print(binascii.hexlify(echo))
        print(binascii.hexlify(ts))
    assert echo == ts

  def kline_recv(self, bus=2):
    msg = self.kline_ll_recv(2, bus=bus)
    msg += self.kline_ll_recv(ord(msg[1])-2, bus=bus)
    return msg










# *** Removed Code Temporary for clarity ***

#
#
# class PandaWifiStreaming(object):
# def __init__(self, ip="192.168.0.10", port=1338):
#   self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#   self.sock.setblocking(0)
#   self.ip = ip
#   self.port = port
#   self.kick()
#
# def kick(self):
#   # must be called at least every 5 seconds
#   self.sock.sendto("hello", (self.ip, self.port))
#
# def can_recv(self):
#   ret = []
#   while True:
#     try:
#       dat, addr = self.sock.recvfrom(0x200*0x10)
#       if addr == (self.ip, self.port):
#         ret += parse_can_buffer(dat)
#     except socket.error as e:
#       if e.errno != 35 and e.errno != 11:
#         traceback.print_exc()
#       break
#   return ret
#
# # stupid tunneling of USB over wifi and SPI
# class WifiHandle(object):
# def __init__(self, ip="192.168.0.10", port=1337):
#   self.sock = socket.create_connection((ip, port))
#
# def __recv(self):
#   ret = self.sock.recv(0x44)
#   length = struct.unpack("I", ret[0:4])[0]
#   return ret[4:4+length]
#
# def controlWrite(self, request_type, request, value, index, data, timeout=0):
#   # ignore data in reply, panda doesn't use it
#   return self.controlRead(request_type, request, value, index, 0, timeout)
#
# def controlRead(self, request_type, request, value, index, length, timeout=0):
#   self.sock.send(struct.pack("HHBBHHH", 0, 0, request_type, request, value, index, length))
#   return self.__recv()
#
# def bulkWrite(self, endpoint, data, timeout=0):
#   if len(data) > 0x10:
#     raise ValueError("Data must not be longer than 0x10")
#   self.sock.send(struct.pack("HH", endpoint, len(data))+data)
#   self.__recv()  # to /dev/null
#
# def bulkRead(self, endpoint, length, timeout=0):
#   self.sock.send(struct.pack("HH", endpoint, 0))
#   return self.__recv()
#
# def close(self):
#   self.sock.close()
#
#
#




#
#
#
# def reset(self, enter_bootstub=False, enter_bootloader=False):
#   # reset
#   try:
#     if enter_bootloader:
#       self._handle.controlWrite(Panda.REQUEST_IN, 0xd1, 0, 0, b'')
#     else:
#       if enter_bootstub:
#         self._handle.controlWrite(Panda.REQUEST_IN, 0xd1, 1, 0, b'')
#       else:
#         self._handle.controlWrite(Panda.REQUEST_IN, 0xd8, 0, 0, b'')
#   except Exception:
#     pass
#   if not enter_bootloader:
#     self.close()
#     time.sleep(1.0)
#     success = False
#     # wait up to 15 seconds
#     for i in range(0, 15):
#       try:
#         self.connect()
#         success = True
#         break
#       except Exception:
#         print("reconnecting is taking %d seconds..." % (i+1))
#         try:
#           dfu = PandaDFU(PandaDFU.st_serial_to_dfu_serial(self._serial))
#           dfu.recover()
#         except Exception:
#           pass
#         time.sleep(1.0)
#     if not success:
#       raise Exception("reset failed")
#
#
#
# def flash(self, fn=None, code=None):
#   if not self.bootstub:
#     self.reset(enter_bootstub=True)
#   assert(self.bootstub)
#
#   if fn is None and code is None:
#     if self.legacy:
#       fn = "obj/comma.bin"
#       print("building legacy st code")
#       build_st(fn, "Makefile.legacy")
#     else:
#       fn = "obj/panda.bin"
#       print("building panda st code")
#       build_st(fn)
#     fn = os.path.join(BASEDIR, "board", fn)
#
#   if code is None:
#     with open(fn) as f:
#       code = f.read()
#
#   # get version
#   print("flash: version is "+self.get_version())
#
#   # confirm flasher is present
#   fr = self._handle.controlRead(Panda.REQUEST_IN, 0xb0, 0, 0, 0xc)
#   assert fr[4:8] == "\xde\xad\xd0\x0d"
#
#   # unlock flash
#   print("flash: unlocking")
#   self._handle.controlWrite(Panda.REQUEST_IN, 0xb1, 0, 0, b'')
#
#   # erase sectors 1 and 2
#   print("flash: erasing")
#   self._handle.controlWrite(Panda.REQUEST_IN, 0xb2, 1, 0, b'')
#   self._handle.controlWrite(Panda.REQUEST_IN, 0xb2, 2, 0, b'')
#
#   # flash over EP2
#   STEP = 0x10
#   print("flash: flashing")
#   for i in range(0, len(code), STEP):
#     self._handle.bulkWrite(2, code[i:i+STEP])
#
#   # reset
#   print("flash: resetting")
#   self.reset()
#
# def recover(self):
#   self.reset(enter_bootloader=True)
#   while len(PandaDFU.list()) == 0:
#     print("waiting for DFU...")
#     time.sleep(0.1)
#
#   dfu = PandaDFU(PandaDFU.st_serial_to_dfu_serial(self._serial))
#   dfu.recover()
#
#   # reflash after recover
#   self.connect(True, True)
#   self.flash()
#
# @staticmethod
# def flash_ota_st():
#   ret = os.system("cd %s && make clean && make ota" % (os.path.join(BASEDIR, "board")))
#   time.sleep(1)
#   return ret==0
#
# @staticmethod
# def flash_ota_wifi():
#   ret = os.system("cd %s && make clean && make ota" % (os.path.join(BASEDIR, "boardesp")))
#   time.sleep(1)
#   return ret==0
#
# @staticmethod
# def list():
#   context = usb1.USBContext()
#   ret = []
#   try:
#     for device in context.getDeviceList(skip_on_error=True):
#       if device.getVendorID() == 0xbbaa and device.getProductID() in [0xddcc, 0xddee]:
#         try:
#           ret.append(device.getSerialNumber())
#         except Exception:
#           continue
#   except Exception:
#     pass
#   # TODO: detect if this is real
#   #ret += ["WIFI"]
#   return ret
