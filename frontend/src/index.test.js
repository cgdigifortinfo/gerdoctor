import React from 'react';

const mockRender = jest.fn();
const mockCreateRoot = jest.fn();

jest.mock('react-dom/client', () => ({ createRoot: (...args) => mockCreateRoot(...args) }));
jest.mock('@/App', () => () => <main>Application</main>);

test('browser bootstrap mounts the application into the root element', () => {
  mockCreateRoot.mockReturnValue({ render: mockRender });
  document.body.innerHTML = '<div id="root"></div>';
  jest.isolateModules(() => require('./index'));
  expect(mockCreateRoot).toHaveBeenCalledWith(document.getElementById('root'));
  expect(mockRender).toHaveBeenCalledTimes(1);
});
