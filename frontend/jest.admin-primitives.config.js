const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/features/admin/AdminDashboardComponents/AdminCmsSections.test.js',
  '<rootDir>/src/features/admin/AdminDashboardComponents/AdminPrimitives.test.js',
  '<rootDir>/src/features/admin/adminPrimitiveDomain.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
