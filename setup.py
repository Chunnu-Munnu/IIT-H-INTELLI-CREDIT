#!/usr/bin/env python3
"""
Intelli-Credit setup script - run once to copy .env.example to .env and set up directories.
"""
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

def main():
    env_example = os.path.join(BASE, '.env.example')
    env_file = os.path.join(BASE, '.env')
    if not os.path.exists(env_file) and os.path.exists(env_example):
        shutil.copy(env_example, env_file)
        print(f"✓ Created {env_file} — edit with your values")
    elif os.path.exists(env_file):
        print(f"✓ .env already exists")
    else:
        print("⚠ .env.example not found — please create .env manually")

    dirs = [
        'data/uploads',
        'data/processed',
        'data/models',
        'backend/data/uploads',
        'backend/data/processed',
        'backend/data/models',
    ]
    for d in dirs:
        path = os.path.join(BASE, 'intelli-credit', d) if not d.startswith('b') else os.path.join(BASE, d)
        # Support both structures
        for prefix in [BASE, os.path.join(BASE, 'intelli-credit', 'backend'), os.path.join(BASE, 'intelli-credit')]:
            target = os.path.join(prefix, d.replace('backend/', ''))
            os.makedirs(target, exist_ok=True)
        break

    # Simpler: just create in current/expected locations
    for d in ['data/uploads', 'data/processed', 'data/models', 'logs']:
        os.makedirs(os.path.join(BASE, '..', d), exist_ok=True)
    print("✓ Data directories created")

    print("\n📋 Next steps:")
    print("  1. Install backend: cd intelli-credit/backend && pip install -r requirements.txt")
    print("  2. Install frontend: cd intelli-credit/frontend && npm install")
    print("  3. Start MongoDB: docker-compose up mongodb -d")
    print("  4. Run backend: cd intelli-credit/backend && uvicorn app.main:app --reload")
    print("  5. Run frontend: cd intelli-credit/frontend && npm run dev")
    print("\nOr use Docker: docker-compose up --build")

if __name__ == '__main__':
    main()
