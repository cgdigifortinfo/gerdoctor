const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/lib/stepVisibility.test.js',
  '<rootDir>/src/features/admin/adminControllerDomain.test.js',
  '<rootDir>/src/features/admin/stepEditorDomain.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
