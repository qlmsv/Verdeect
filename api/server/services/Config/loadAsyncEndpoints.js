const { isUserProvided } = require('~/server/utils');
const { config } = require('./EndpointService');

const { googleKey } = config;

/**
 * Load async endpoints and return a configuration object
 * @param {Express.Request} req - The request object
 * @returns {{ google: object|boolean }} An object containing the google configuration
 */
async function loadAsyncEndpoints() {
  let googleUserProvides;
  let serviceKey;
  
  try {
    serviceKey = require('~/data/auth.json');
  } catch (e) {
    // Handle error if needed
  }

  if (isUserProvided(googleKey)) {
    googleUserProvides = true;
  }

  const google = serviceKey || googleKey ? { userProvide: googleUserProvides } : false;

  return { google };
}

module.exports = loadAsyncEndpoints;
