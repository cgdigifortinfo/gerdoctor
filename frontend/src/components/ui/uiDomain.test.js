import { statusStyle, tooltipPosition } from './uiDomain';

test('statusStyle maps all tones and unknown values', () => {
  expect(statusStyle('success')).toContain('green');
  expect(statusStyle('warning')).toContain('amber');
  expect(statusStyle('danger')).toContain('red');
  expect(statusStyle('info')).toContain('brand-primary');
  expect(statusStyle('neutral')).toContain('muted');
  expect(statusStyle('unknown')).toBe(statusStyle());
});

test('tooltipPosition clamps top and right placements to the viewport', () => {
  expect(tooltipPosition({ left: 0, right: 0, top: 0, width: 0, height: 0 })).toStrictEqual({ left: 12, top: 12 });
  expect(tooltipPosition({ left: 100, right: 120, top: 80, width: 20, height: 20 }, 'top', 1000, 800)).toStrictEqual({ left: 12, top: 70 });
  expect(tooltipPosition({ left: 900, right: 920, top: 790, width: 20, height: 20 }, 'right', 1000, 800)).toStrictEqual({ left: 700, top: 752 });
  expect(tooltipPosition({ left: 500, right: 520, top: 10, width: 20, height: 20 }, 'right', 1000, 800)).toStrictEqual({ left: 530, top: 48 });
  expect(tooltipPosition({ left: 980, right: 1000, top: 5, width: 20, height: 20 }, 'top', 1000, 800)).toStrictEqual({ left: 700, top: 12 });
  expect(tooltipPosition({ left: 100, right: 120, top: 100, width: 20, height: 20 }, 'top', 200, 800)).toStrictEqual({ left: 12, top: 90 });
  expect(tooltipPosition({ left: 10, right: 30, top: 100, width: 20, height: 20 }, 'right', 200, 800)).toStrictEqual({ left: 12, top: 110 });
  expect(tooltipPosition({ left: 400, right: 420, top: 200, width: 20, height: 20 }, 'top', 1000, 800)).toStrictEqual({ left: 266, top: 190 });
  expect(tooltipPosition({ left: 400, right: 420, top: 200, width: 20, height: 20 }, 'right', 1000, 800)).toStrictEqual({ left: 430, top: 210 });
});
