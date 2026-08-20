# Next unit-test suite

This suite is intentionally separate from `backend/tests` and is not collected
by the default `backend/pytest.ini` configuration.

Run it explicitly with:

```bash
pytest -c pytest.next.ini
```

The files are grouped by production class/module and exercise successful,
rejected, boundary, and fallback use cases. Stripe integration is deliberately
excluded until that interface is ready.

