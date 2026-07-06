"""Quick smoke test for 10 extension features APIs."""
from app import create_app

app = create_app()
client = app.test_client()

paths = [
    '/api/features/summary',
    '/api/features/season',
    '/api/features/daily-shop',
    '/api/features/mission-shop',
    '/api/features/routes',
    '/api/features/airline',
    '/api/economy/payslip',
    '/payslip',
]
errors = []
for path in paths:
    r = client.get(path)
    ok = r.status_code == 200
    print(f"  {'OK' if ok else 'FAIL'}: GET {path} → {r.status_code}")
    if not ok:
        errors.append(path)

if errors:
    print(f"\nFailed: {errors}")
    raise SystemExit(1)
print("\nAll feature API checks passed!")