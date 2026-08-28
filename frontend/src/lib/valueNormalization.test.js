import { asArray, asObject, asString } from './valueNormalization';

test('normalizes scalar and container values without leaking mutable defaults', () => {
  expect(asString(undefined)).toBe('');
  expect(asString(null)).toBe('');
  expect(asString(false)).toBe('false');
  expect(asString(42)).toBe('42');
  const list = [1]; expect(asArray(list)).toBe(list);
  expect(asArray(null)).toEqual([]);
  expect(Object.isFrozen(asArray('invalid'))).toBe(true);
  const object = { id: 1 }; expect(asObject(object)).toBe(object);
  expect(asObject(null)).toEqual({});
  expect(asObject([])).toEqual({});
  expect(asObject('invalid')).toEqual({});
});
