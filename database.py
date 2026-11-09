
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Carrega as configurações do arquivo .env
load_dotenv()

# Obtém a URL de conexão
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Configure DATABASE_URL no arquivo .env")

# Cria o mecanismo de conexão
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# Cria a fábrica de sessões do banco
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)

# Classe base para as tabelas
class Base(DeclarativeBase):
    pass


# Fornece uma sessão para as rotas
def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
