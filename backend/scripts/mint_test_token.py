"""Print a JWT for the E2E run (backend started with the same SUPABASE_JWT_SECRET, memory DB, fake LLM).

    python scripts/mint_test_token.py <secret>

Only for local/CI testing. A real deployment never sets NEXT_PUBLIC_E2E_ACCESS_TOKEN.
"""

import sys
import time

import jwt

secret = sys.argv[1]
claims = {"sub": "e2e-user", "email": "e2e@test.dev", "aud": "authenticated", "exp": int(time.time()) + 6 * 3600}
print(jwt.encode(claims, secret, algorithm="HS256"))
