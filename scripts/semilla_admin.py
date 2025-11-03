"""Seed for initial admin user.

Usage:
    python scripts/seed_admin.py
"""
from __future__ import annotations

import os

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.utils.seguridad import hash_password


def run():
    email = os.getenv("SEED_ADMIN_EMAIL", "admin@demo.local")
    password = os.getenv("SEED_ADMIN_PASS", "Admin123!")
    full_name = os.getenv("SEED_ADMIN_NAME", "Administrador")
    role = "Gerente"

    db: Session = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print("Admin ya existe:", email)
            return
        user = User(email=email, full_name=full_name, role=role, is_active=True, hashed_password=hash_password(password))
        db.add(user)
        db.commit()
        print("Usuario admin creado:", email)
    finally:
        db.close()


if __name__ == "__main__":
    run()

