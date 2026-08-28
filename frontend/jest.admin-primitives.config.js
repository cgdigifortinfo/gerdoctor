const createJestConfig = require('react-scripts/scripts/utils/createJestConfig');
const config = createJestConfig((path) => require.resolve(`react-scripts/${path}`), process.cwd(), false);
module.exports = { ...config, testMatch: [
  '<rootDir>/src/features/admin/AdminDashboardComponents/AdminCmsSections.test.js',
  '<rootDir>/src/features/admin/AdminDashboardComponents/AdminPrimitives.test.js',
  '<rootDir>/src/features/admin/adminPrimitiveDomain.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
