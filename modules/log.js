var { inspect } = require('util')

const log = (msg, item, showHidden = false) => {
  console.log(`\n **  ${msg}`, inspect(item, {colors: true, depth: null, showHidden}))
}

module.exports = log
