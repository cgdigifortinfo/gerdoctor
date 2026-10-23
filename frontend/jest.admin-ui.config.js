const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/features/admin/tabs/AdminTabs.test.js',
  '<rootDir>/src/features/admin/AdminDialogs.test.js',
  '<rootDir>/src/features/admin/UserDetailDialog.test.js',
  '<rootDir>/src/features/admin/AdminDashboardComponents/UserDialogs.test.js',
  '<rootDir>/src/features/admin/AdminDashboardComponents/PartnerDialog.test.js',
  '<rootDir>/src/features/admin/AdminDashboardComponents/AdminCmsSections.test.js',
  '<rootDir>/src/features/admin/AdminDashboardComponents/AdminPrimitives.test.js',
  '<rootDir>/src/features/admin/hooks/adminStateHooks.test.js',
  '<rootDir>/src/features/admin/hooks/adminCommands.test.js'
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
