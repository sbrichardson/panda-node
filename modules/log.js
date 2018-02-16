var { inspect } = require('util')


const log = (msg, item, showHidden = false) => {
  console.log(`\n\n${msg}\n\n`, inspect(item, {colors: true, depth: null, showHidden}))
  // console.log(`\n\n${msg}\n\n`, item)
}

module.exports = log
