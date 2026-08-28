module.exports = {
  rootDir: '.',
  testEnvironment: 'node',
  testMatch: [
    '<rootDir>/src/features/userJourney/domain.test.js',
    '<rootDir>/src/features/partnerDashboard/domain.test.js',
  ],
  transform: { '^.+\\.[jt]sx?$': '<rootDir>/node_modules/react-scripts/config/jest/babelTransform.js' },
  modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
};
