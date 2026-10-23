module.exports = {
  rootDir: '.',
  testEnvironment: 'node',
  testMatch: ['<rootDir>/src/features/admin/stepDialogDomain.test.js'],
  transform: {
    '^.+\\.[jt]sx?$': 'babel-jest',
  },
  modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
};
