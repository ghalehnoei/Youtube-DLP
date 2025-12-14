"""
Test script to check if .env file is being read correctly.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

print("=" * 60)
print("Testing .env file reading")
print("=" * 60)
print(f"Project root: {project_root}")
print(f"Looking for .env at: {env_file}")
print(f".env file exists: {env_file.exists()}")
print()

if env_file.exists():
    print(f"File size: {env_file.stat().st_size} bytes")
    print()
    
    # Load .env file
    load_dotenv(env_file, override=True)
    print("Loaded .env file")
    print()
    
    # Check Supabase variables
    print("Checking environment variables:")
    print("-" * 60)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    supabase_key = os.getenv("SUPABASE_KEY")
    database_url = os.getenv("DATABASE_URL")
    
    print(f"SUPABASE_URL: {supabase_url if supabase_url else 'NOT SET'}")
    if supabase_anon_key:
        masked_key = supabase_anon_key[:20] + "..." if len(supabase_anon_key) > 20 else supabase_anon_key
        print(f"SUPABASE_ANON_KEY: {masked_key}")
    else:
        print(f"SUPABASE_ANON_KEY: NOT SET")
    
    if supabase_key:
        masked_key = supabase_key[:20] + "..." if len(supabase_key) > 20 else supabase_key
        print(f"SUPABASE_KEY: {masked_key}")
    else:
        print(f"SUPABASE_KEY: NOT SET")
    
    print(f"DATABASE_URL: {database_url if database_url else 'NOT SET'}")
    print()
    
    # Check if Supabase is configured
    if supabase_url and (supabase_anon_key or supabase_key):
        print("✅ Supabase is configured!")
        print(f"   URL: {supabase_url}")
    else:
        print("❌ Supabase is NOT configured")
        print("   Make sure SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_KEY) are set in .env")
    
    print()
    print("All environment variables:")
    print("-" * 60)
    env_vars = {k: v for k, v in os.environ.items() if k.startswith(('SUPABASE_', 'DB_', 'DATABASE_'))}
    for key, value in sorted(env_vars.items()):
        if 'KEY' in key or 'PASSWORD' in key:
            masked = value[:20] + "..." if len(value) > 20 else value
            print(f"{key}: {masked}")
        else:
            print(f"{key}: {value}")
else:
    print("❌ .env file NOT FOUND!")
    print()
    print("To create it:")
    print("1. Copy env.example to .env:")
    print("   Copy-Item env.example .env")
    print()
    print("2. Edit .env and add your Supabase credentials:")
    print("   SUPABASE_URL=https://xxx.supabase.co")
    print("   SUPABASE_ANON_KEY=your_key_here")

print()
print("=" * 60)

