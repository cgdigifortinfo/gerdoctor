const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/contexts/AuthContext.test.js',
  '<rootDir>/src/lib/api.test.js',
  '<rootDir>/src/lib/apiDomain.test.js',
  '<rootDir>/src/lib/coreInfrastructure.test.js',
  '<rootDir>/src/lib/sanitizeHtml.test.js',
  '<rootDir>/src/lib/sanitizeHtml.node.test.js',
  '<rootDir>/src/lib/stepVisibility.test.js',
  '<rootDir>/src/components/sharedComponents.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
