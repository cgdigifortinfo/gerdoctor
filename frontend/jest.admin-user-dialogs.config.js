const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/features/admin/AdminDashboardComponents/UserDialogs.test.js',
  '<rootDir>/src/features/admin/adminUserDialogDomain.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
