module.exports = {
  rootDir: '.',
  testEnvironment: 'jsdom',
  testMatch: ['<rootDir>/src/**/*.test.{js,jsx}'],
  setupFiles: ['<rootDir>/scripts/jest-polyfills.cjs'],
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],
  transform: { '^.+\\.[jt]sx?$': 'babel-jest' },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': '<rootDir>/scripts/jest-style-mock.cjs',
    '\\.(png|jpg|jpeg|gif|webp|svg)$': '<rootDir>/scripts/jest-file-mock.cjs',
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
  resetMocks: true,
  snapshotFormat: { escapeString: true, printBasicPrototype: true },
  collectCoverageFrom: ['src/**/*.{js,jsx}', '!src/**/*.test.{js,jsx}'],
  coverageThreshold: {
    global: { branches: 100, functions: 100, lines: 100, statements: 100 },
  },
};
