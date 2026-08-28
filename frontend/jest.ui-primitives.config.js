const createJestConfig = require('react-scripts/scripts/utils/createJestConfig');
const config = createJestConfig((path) => require.resolve(`react-scripts/${path}`), process.cwd(), false);
module.exports = { ...config, testMatch: [
  '<rootDir>/src/components/ui/uiPrimitives.test.jsx',
  '<rootDir>/src/components/ui/uiDomain.test.js',
  '<rootDir>/src/components/sharedComponents.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
