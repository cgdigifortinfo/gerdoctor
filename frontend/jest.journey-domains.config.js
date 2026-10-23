module.exports = {
  rootDir: '.',
  testEnvironment: 'node',
  testMatch: [
    '<rootDir>/src/features/userJourney/domain.test.js',
    '<rootDir>/src/features/partnerDashboard/domain.test.js',
  ],
  transform: { '^.+\\.[jt]sx?$': 'babel-jest' },
  modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
};
