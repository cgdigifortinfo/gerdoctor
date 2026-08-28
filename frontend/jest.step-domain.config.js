module.exports = {
  rootDir: '.',
  testEnvironment: 'node',
  testMatch: ['<rootDir>/src/features/admin/stepDialogDomain.test.js'],
  transform: {
    '^.+\\.[jt]sx?$': '<rootDir>/node_modules/react-scripts/config/jest/babelTransform.js',
  },
  modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
};
