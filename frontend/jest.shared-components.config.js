const createJestConfig = require('react-scripts/scripts/utils/createJestConfig');
const config = createJestConfig((path) => require.resolve(`react-scripts/${path}`), process.cwd(), false);
module.exports = { ...config, testMatch: [
  '<rootDir>/src/components/sharedComponents.test.js',
  '<rootDir>/src/components/routingLayoutComplete.test.js',
  '<rootDir>/src/components/DashboardAccess.test.js',
  '<rootDir>/src/components/routeDomain.test.js',
  '<rootDir>/src/components/paginationDomain.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
