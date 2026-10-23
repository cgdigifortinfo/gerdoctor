const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/components/ui/uiPrimitives.test.jsx',
  '<rootDir>/src/components/ui/uiDomain.test.js',
  '<rootDir>/src/components/sharedComponents.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
