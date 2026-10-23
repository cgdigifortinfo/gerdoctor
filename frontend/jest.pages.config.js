const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/App.test.js', '<rootDir>/src/pages/AdminDashboard.test.js', '<rootDir>/src/pages/Auth.test.js',
  '<rootDir>/src/pages/Landing.test.js', '<rootDir>/src/pages/PartnerDashboard.test.js',
  '<rootDir>/src/pages/PartnerDashboard.components.test.js', '<rootDir>/src/pages/UserDashboard.test.js',
  '<rootDir>/src/pages/partnerPublicPages.test.js', '<rootDir>/src/features/partnerBilling/stripeAction.test.js',
  '<rootDir>/src/features/partnerProfile/logo.test.js'
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
