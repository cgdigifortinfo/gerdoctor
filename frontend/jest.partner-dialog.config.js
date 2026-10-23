const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/features/admin/AdminDashboardComponents/PartnerDialog.test.js',
  '<rootDir>/src/features/admin/partnerDialogDomain.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
