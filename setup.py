from setuptools import find_packages, setup

setup(
    name="wishlist-api",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.115.0",
        "uvicorn[standard]==0.32.0",
        "sqlalchemy==2.0.36",
        "alembic==1.13.3",
        "psycopg2-binary==2.9.9",
        "redis==5.2.0",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "python-multipart==0.0.12",
        "pydantic==2.9.2",
        "pydantic-settings==2.6.1",
    ],
    python_requires=">=3.10",
)
