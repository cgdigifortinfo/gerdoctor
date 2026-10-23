const config = require('./jest.config.cjs');

module.exports = {
  ...config,
  testMatch: [
    '<rootDir>/src/lib/stepVisibility.test.js',
    '<rootDir>/src/features/steps/FlowSimulatorPanel.test.js',
    '<rootDir>/src/features/admin/adminControllerDomain.test.js',
    '<rootDir>/src/features/admin/stepEditorDomain.test.js',
    '<rootDir>/src/features/admin/stepEditor/StepEditorPanels.test.js',
    '<rootDir>/src/features/admin/stepEditor/ConditionsPanel.test.js',
    '<rootDir>/src/features/admin/hooks/adminCommands.test.js',
    '<rootDir>/src/features/admin/useAdminDashboardController.test.js'
  ],
  testRegex: undefined,
  modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'],
};
