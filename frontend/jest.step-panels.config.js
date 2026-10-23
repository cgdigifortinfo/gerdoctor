const config = require('./jest.config.cjs');
module.exports = { ...config, testMatch: [
  '<rootDir>/src/features/admin/stepEditor/StepEditorPanels.test.js',
  '<rootDir>/src/features/admin/stepEditor/ConditionsPanel.test.js',
  '<rootDir>/src/features/steps/FlowSimulatorPanel.test.js',
], testRegex: undefined, modulePathIgnorePatterns: ['<rootDir>/.stryker-tmp/'] };
