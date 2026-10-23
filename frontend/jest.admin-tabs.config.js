const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/features/admin/tabs/AdminTabs.test.js',
  '<rootDir>/src/features/admin/adminTabViewModels.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
