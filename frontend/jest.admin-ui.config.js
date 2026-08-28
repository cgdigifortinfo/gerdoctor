const createJestConfig = require('react-scripts/scripts/utils/createJestConfig');
const config = createJestConfig((path) => require.resolve(`react-scripts/${path}`), process.cwd(), false);
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
