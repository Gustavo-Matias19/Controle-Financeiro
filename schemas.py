
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator
)


class TransacaoEntrada(BaseModel):

    descricao: str = Field(
        min_length=1,
        max_length=150
    )

    valor: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )

    tipo: Literal["receita", "despesa"]

    categoria: str = Field(
        min_length=1,
        max_length=60
    )

    data: date = Field(default_factory=date.today)

    @field_validator("descricao", "categoria")
    @classmethod
    def nao_vazio(cls, v: str) -> str:
        v = v.strip()

        if not v:
            raise ValueError("Não pode ficar em branco")

        return v


class TransacaoSaida(TransacaoEntrada):

    id: int

    model_config = ConfigDict(from_attributes=True)


class UsuarioEntrada(BaseModel):

    nome: str = Field(min_length=1, max_length=100)

    email: str = Field(min_length=3, max_length=255)

    senha: str = Field(min_length=8, max_length=128)


class TokenSaida(BaseModel):

    access_token: str

    token_type: str = "bearer"
