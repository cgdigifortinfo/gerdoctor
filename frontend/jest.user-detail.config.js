const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/features/admin/UserDetailDialog.test.js',
  '<rootDir>/src/features/admin/userDetailViewModels.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
