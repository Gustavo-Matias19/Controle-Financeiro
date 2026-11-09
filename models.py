
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    CheckConstraint
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from database import Base


class User(Base):

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    senha_hash: Mapped[str] = mapped_column(
        String(300),
        nullable=False
    )

    transacoes: Mapped[list["Transaction"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan"
    )


class Transaction(Base):

    __tablename__ = "transacoes"

    __table_args__ = (
        CheckConstraint("valor > 0", name="valor_positivo"),
        CheckConstraint(
            "tipo IN ('receita', 'despesa')",
            name="tipo_valido"
        )
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"),
        index=True,
        nullable=False
    )

    descricao: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    valor: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    tipo: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    categoria: Mapped[str] = mapped_column(
        String(60),
        nullable=False
    )

    data: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        nullable=False
    )

    usuario: Mapped["User"] = relationship(
        back_populates="transacoes"
    )
