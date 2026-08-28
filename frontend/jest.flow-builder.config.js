const createJestConfig = require('react-scripts/scripts/utils/createJestConfig');

const config = createJestConfig(
  (relativePath) => require.resolve(`react-scripts/${relativePath}`),
  process.cwd(),
  false,
);

module.exports = {
  ...config,
  testMatch: ['<rootDir>/src/components/StepsFlowBuilder.test.js'],
  testRegex: undefined,
  modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
};
