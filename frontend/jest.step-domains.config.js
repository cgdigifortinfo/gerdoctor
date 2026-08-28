const createJestConfig = require('react-scripts/scripts/utils/createJestConfig');
const config = createJestConfig((path) => require.resolve(`react-scripts/${path}`), process.cwd(), false);
module.exports = { ...config, testMatch: [
  '<rootDir>/src/lib/stepVisibility.test.js',
  '<rootDir>/src/features/admin/adminControllerDomain.test.js',
  '<rootDir>/src/features/admin/stepEditorDomain.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
