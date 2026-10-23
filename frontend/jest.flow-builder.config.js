const config = require('./jest.config.cjs');

module.exports = {
  ...config,
  testMatch: ['<rootDir>/src/components/StepsFlowBuilder.test.js'],
  testRegex: undefined,
  modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
};
