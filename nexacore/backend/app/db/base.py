"""
Declarative base. Import all models here so Alembic autogenerate can see them.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
