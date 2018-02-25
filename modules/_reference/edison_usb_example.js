//https://github.com/jackalchen737/Intel-Edison/blob/524539951cdc1043399e5e0eb9cdcaeeb864f367/USB_Bomb_NodeJS/usb_bomb_js_keyboard.js

// also https://github.com/pathikrit/node-thunder-driver/blob/master/driver.js


//this is a USB Bomb controller example
//API reference: https://github.com/nonolith/node-usb
//find device
var usb = require('usb'),
    term = usb.findByIds(0x1941, 0x8021);

//make sure device exist
if (term == undefined){
     console.log("no such device of vid,pid = 0x1941, 0x8021");
    return;
}

//open device
term.open();
if(term.interfaces[0].isKernelDriverActive())
    term.interfaces[0].detachKernelDriver();

var C_UP = new Buffer([0x01,0,0,0,0,0,0,0]),
    C_DOWN = new Buffer ([0x02,0,0,0,0,0,0,0]),
    C_LEFT = new Buffer ([0x04,0,0,0,0,0,0,0]),
    C_RIGHT = new Buffer ([0x08,0,0,0,0,0,0,0]),
    C_FIRE = new Buffer ([0x10,0,0,0,0,0,0,0]),
    C_NONE = new Buffer ([0,0,0,0,0,0,0,0]);

function sleep(ms) {
    var unixtime_ms = new Date().getTime();
    while(new Date().getTime() < unixtime_ms + ms) {}
}

function ctrlMsgCB(err, data){
    if(err)
        console.log('send ctrl transfer error');
}

process.stdin.resume();
process.stdin.on('data', function(chunk) {
    console.log('chunk: ' + chunk);
    if (chunk == 'w\n'){
        term.controlTransfer(0x21,0x09,0,0,C_UP,ctrlMsgCB); // (33, 9, 0, 0, C_UP, callback)
        sleep(1000);
        term.controlTransfer(0x21,0x09,0,0,C_NONE,ctrlMsgCB);
        console.log("up");
    }
    else if (chunk == 's\n'){
        term.controlTransfer(0x21,0x09,0,0,C_DOWN,ctrlMsgCB);
        sleep(1000);
        term.controlTransfer(0x21,0x09,0,0,C_NONE,ctrlMsgCB);
        console.log("down");
    }
    else if (chunk == 'd\n'){
        term.controlTransfer(0x21,0x09,0,0,C_RIGHT,ctrlMsgCB);
        sleep(1000);
        term.controlTransfer(0x21,0x09,0,0,C_NONE,ctrlMsgCB);
        console.log("right");
    }
    else if (chunk == 'a\n'){
        term.controlTransfer(0x21,0x09,0,0,C_LEFT,ctrlMsgCB);
        sleep(1000);
        term.controlTransfer(0x21,0x09,0,0,C_NONE,ctrlMsgCB);
        console.log("left");
    }
    else if (chunk == 'f\n'){
        term.controlTransfer(0x21,0x09,0,0,C_FIRE,ctrlMsgCB);
        sleep(5000);
        term.controlTransfer(0x21,0x09,0,0,C_NONE,ctrlMsgCB);
        console.log("fire");
    }
    else if (chunk == 'q\n'){
        console.log("quit");
        term.close();
        process.exit();
    }
});
