import os

# backend.database hard-fails at import time if these aren't set. Tests never
# talk to a real Supabase project, but importing backend.auth (and anything
# that imports it) pulls database.py in transitively, so set harmless
# placeholders before any backend module is imported.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
