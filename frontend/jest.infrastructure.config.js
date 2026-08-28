const createJestConfig = require('react-scripts/scripts/utils/createJestConfig');
const config = createJestConfig((path) => require.resolve(`react-scripts/${path}`), process.cwd(), false);
module.exports = { ...config, testMatch: [
  '<rootDir>/src/contexts/AuthContext.test.js',
  '<rootDir>/src/lib/api.test.js',
  '<rootDir>/src/lib/apiDomain.test.js',
  '<rootDir>/src/lib/coreInfrastructure.test.js',
  '<rootDir>/src/lib/sanitizeHtml.test.js',
  '<rootDir>/src/lib/stepVisibility.test.js',
  '<rootDir>/src/components/sharedComponents.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
