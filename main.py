
import os
import secrets

from datetime import date
from decimal import Decimal, InvalidOperation
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Request,
    status
)

from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from starlette.middleware.sessions import SessionMiddleware

from database import Base, engine, get_db
from models import Transaction, User

from schemas import (
    TransacaoEntrada,
    TransacaoSaida,
    TokenSaida,
    UsuarioEntrada
)

from security import (
    conferir_senha,
    criar_token,
    hash_senha,
    ler_token,
    SECRET_KEY
)


# ===================================================
# 1. CONFIGURAÇÃO DA APLICAÇÃO
# ===================================================

ROOT = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria as tabelas que ainda não existem
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Sistema de Controle Financeiro",
    description="API REST com Python, FastAPI e PostgreSQL",
    version="1.0.0",
    lifespan=lifespan
)


# Configuração da sessão de login do site
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=os.getenv("COOKIE_SECURE") == "true"
)


# Arquivos CSS
app.mount(
    "/static",
    StaticFiles(directory=ROOT / "static"),
    name="static"
)


# Arquivos HTML
templates = Jinja2Templates(
    directory=ROOT / "templates"
)


# Autenticação por token JWT da API
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/token"
)


# ===================================================
# 2. FUNÇÕES AUXILIARES
# ===================================================

def redirecionar(url: str):
    return RedirectResponse(
        url=url,
        status_code=303
    )


def pagina(request: Request, arquivo: str, **contexto):

    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(32)

    return templates.TemplateResponse(
        request,
        arquivo,
        {
            "csrf": request.session["csrf"],
            **contexto
        }
    )


def verificar_csrf(request: Request, token: str):

    armazenado = request.session.get("csrf")

    if not armazenado or not secrets.compare_digest(
        armazenado, token
    ):
        raise HTTPException(
            status_code=403,
            detail="Formulário inválido"
        )


def usuario_web(request: Request, db: Session):

    usuario_id = request.session.get("uid")

    if not isinstance(usuario_id, int):
        return None

    return db.get(User, usuario_id)


def usuario_api(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    usuario_id = ler_token(token)

    usuario = db.get(User, usuario_id)

    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Usuário não encontrado"
        )

    return usuario


def buscar_do_usuario(
    db: Session,
    usuario_id: int,
    transacao_id: int
):

    transacao = db.scalar(
        select(Transaction).where(
            Transaction.id == transacao_id,
            Transaction.usuario_id == usuario_id
        )
    )

    if not transacao:
        raise HTTPException(
            status_code=404,
            detail="Transação não encontrada"
        )

    return transacao


# ===================================================
# 3. CADASTRO DE USUÁRIOS - API
# ===================================================

@app.post("/api/usuarios", status_code=201)
def registrar_api(
    dados: UsuarioEntrada,
    db: Session = Depends(get_db)
):

    email = dados.email.strip().lower()

    if not email or "@" not in email:
        raise HTTPException(
            status_code=422,
            detail="E-mail inválido"
        )

    if not dados.nome.strip():
        raise HTTPException(
            status_code=422,
            detail="Nome obrigatório"
        )

    usuario = User(
        nome=dados.nome.strip(),
        email=email,
        senha_hash=hash_senha(dados.senha)
    )

    db.add(usuario)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="E-mail já cadastrado"
        )

    db.refresh(usuario)

    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email
    }


# ===================================================
# 4. LOGIN - API JWT
# ===================================================

@app.post(
    "/api/token",
    response_model=TokenSaida
)
def entrar_api(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    usuario = db.scalar(
        select(User).where(
            User.email == form.username.strip().lower()
        )
    )

    if not usuario or not conferir_senha(
        form.password,
        usuario.senha_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha incorretos"
        )

    token = criar_token(usuario.id)

    return TokenSaida(
        access_token=token
    )


# ===================================================
# 5. GET - LISTAR TRANSAÇÕES
# ===================================================

@app.get(
    "/api/transacoes",
    response_model=list[TransacaoSaida]
)
def listar_api(
    db: Session = Depends(get_db),
    usuario: User = Depends(usuario_api)
):

    transacoes = db.scalars(
        select(Transaction)
        .where(Transaction.usuario_id == usuario.id)
        .order_by(
            Transaction.data.desc(),
            Transaction.id.desc()
        )
    ).all()

    return transacoes


# ===================================================
# 6. GET - BUSCAR TRANSAÇÃO POR ID
# ===================================================

@app.get(
    "/api/transacoes/{transacao_id}",
    response_model=TransacaoSaida
)
def buscar_api(
    transacao_id: int,
    db: Session = Depends(get_db),
    usuario: User = Depends(usuario_api)
):

    return buscar_do_usuario(
        db,
        usuario.id,
        transacao_id
    )


# ===================================================
# 7. POST - CADASTRAR TRANSAÇÃO
# ===================================================

@app.post(
    "/api/transacoes",
    response_model=TransacaoSaida,
    status_code=201
)
def criar_api(
    dados: TransacaoEntrada,
    db: Session = Depends(get_db),
    usuario: User = Depends(usuario_api)
):

    transacao = Transaction(
        **dados.model_dump(),
        usuario_id=usuario.id
    )

    db.add(transacao)
    db.commit()
    db.refresh(transacao)

    return transacao


# ===================================================
# 8. PUT - ATUALIZAR TRANSAÇÃO
# ===================================================

@app.put(
    "/api/transacoes/{transacao_id}",
    response_model=TransacaoSaida
)
def editar_api(
    transacao_id: int,
    dados: TransacaoEntrada,
    db: Session = Depends(get_db),
    usuario: User = Depends(usuario_api)
):

    transacao = buscar_do_usuario(
        db,
        usuario.id,
        transacao_id
    )

    for campo, valor in dados.model_dump().items():
        setattr(transacao, campo, valor)

    db.commit()
    db.refresh(transacao)

    return transacao


# ===================================================
# 9. DELETE - EXCLUIR TRANSAÇÃO
# ===================================================

@app.delete(
    "/api/transacoes/{transacao_id}",
    status_code=204
)
def excluir_api(
    transacao_id: int,
    db: Session = Depends(get_db),
    usuario: User = Depends(usuario_api)
):

    transacao = buscar_do_usuario(
        db,
        usuario.id,
        transacao_id
    )

    db.delete(transacao)
    db.commit()


# ===================================================
# 10. RESUMO FINANCEIRO
# ===================================================

def resumo_do_usuario(
    db: Session,
    usuario_id: int
):

    resultados = db.execute(
        select(
            Transaction.tipo,
            func.sum(Transaction.valor)
        )
        .where(
            Transaction.usuario_id == usuario_id
        )
        .group_by(Transaction.tipo)
    ).all()

    valores = dict(resultados)

    receitas = valores.get(
        "receita",
        Decimal("0.00")
    )

    despesas = valores.get(
        "despesa",
        Decimal("0.00")
    )

    saldo = receitas - despesas

    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": saldo
    }


@app.get("/api/resumo")
def resumo_api(
    db: Session = Depends(get_db),
    usuario: User = Depends(usuario_api)
):

    return resumo_do_usuario(
        db,
        usuario.id
    )


# ===================================================
# 11. PÁGINA INICIAL
# ===================================================

@app.get("/", include_in_schema=False)
def inicio(request: Request):

    if request.session.get("uid"):
        return redirecionar("/dashboard")

    return redirecionar("/login")


# ===================================================
# 12. CADASTRO DE USUÁRIOS - SITE
# ===================================================

@app.get(
    "/cadastro",
    response_class=HTMLResponse,
    include_in_schema=False
)
def cadastro(request: Request):

    return pagina(
        request,
        "cadastro.html"
    )


@app.post("/cadastro", include_in_schema=False)
def cadastrar_web(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    csrf: str = Form(...),
    db: Session = Depends(get_db)
):

    verificar_csrf(request, csrf)

    try:
        dados = UsuarioEntrada(
            nome=nome,
            email=email,
            senha=senha
        )

        resultado = registrar_api(
            dados,
            db
        )

    except (ValueError, HTTPException):
        return pagina(
            request,
            "cadastro.html",
            erro="Verifique os dados ou o e-mail informado."
        )

    request.session.clear()
    request.session["uid"] = resultado["id"]

    return redirecionar("/dashboard")


# ===================================================
# 13. LOGIN - SITE
# ===================================================

@app.get(
    "/login",
    response_class=HTMLResponse,
    include_in_schema=False
)
def login(request: Request):

    return pagina(
        request,
        "login.html"
    )


@app.post("/login", include_in_schema=False)
def login_web(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    csrf: str = Form(...),
    db: Session = Depends(get_db)
):

    verificar_csrf(request, csrf)

    usuario = db.scalar(
        select(User).where(
            User.email == email.strip().lower()
        )
    )

    if not usuario or not conferir_senha(
        senha,
        usuario.senha_hash
    ):
        return pagina(
            request,
            "login.html",
            erro="E-mail ou senha incorretos."
        )

    request.session.clear()
    request.session["uid"] = usuario.id

    return redirecionar("/dashboard")


# ===================================================
# 14. LOGOUT
# ===================================================

@app.post("/logout", include_in_schema=False)
def logout(
    request: Request,
    csrf: str = Form(...)
):

    verificar_csrf(request, csrf)

    request.session.clear()

    return redirecionar("/login")


# ===================================================
# 15. DASHBOARD FINANCEIRO
# ===================================================

@app.get(
    "/dashboard",
    response_class=HTMLResponse,
    include_in_schema=False
)
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    usuario = usuario_web(
        request,
        db
    )

    if not usuario:
        return redirecionar("/login")

    # Busca transações do usuário
    registros = db.scalars(
        select(Transaction)
        .where(
            Transaction.usuario_id == usuario.id
        )
        .order_by(
            Transaction.data.desc(),
            Transaction.id.desc()
        )
    ).all()

    # Calcula receitas, despesas e saldo
    resumo = resumo_do_usuario(
        db,
        usuario.id
    )

    # Agrupa despesas por categoria
    categorias = db.execute(
        select(
            Transaction.categoria,
            func.sum(Transaction.valor)
        )
        .where(
            Transaction.usuario_id == usuario.id,
            Transaction.tipo == "despesa"
        )
        .group_by(Transaction.categoria)
        .order_by(
            func.sum(Transaction.valor).desc()
        )
    ).all()

    total_despesas = resumo["despesas"]

    grafico = []

    for categoria, valor in categorias:

        percentual = (
            round(
                float(valor / total_despesas * 100),
                1
            )
            if total_despesas
            else 0
        )

        grafico.append({
            "categoria": categoria,
            "valor": valor,
            "percentual": percentual
        })

    return pagina(
        request,
        "dashboard.html",
        usuario=usuario,
        registros=registros,
        resumo=resumo,
        grafico=grafico,
        hoje=date.today().isoformat()
    )


# ===================================================
# 16. CADASTRAR TRANSAÇÃO PELO SITE
# ===================================================

@app.post("/transacoes", include_in_schema=False)
def adicionar_web(
    request: Request,
    descricao: str = Form(...),
    valor: str = Form(...),
    tipo: str = Form(...),
    categoria: str = Form(...),
    data: date = Form(...),
    csrf: str = Form(...),
    db: Session = Depends(get_db)
):

    verificar_csrf(request, csrf)

    usuario = usuario_web(
        request,
        db
    )

    if not usuario:
        return redirecionar("/login")

    try:
        dados = TransacaoEntrada(
            descricao=descricao,
            valor=Decimal(valor.replace(",", ".")),
            tipo=tipo,
            categoria=categoria,
            data=data
        )

    except (ValueError, InvalidOperation):
        raise HTTPException(
            status_code=422,
            detail="Dados da transação inválidos"
        )

    transacao = Transaction(
        **dados.model_dump(),
        usuario_id=usuario.id
    )

    db.add(transacao)
    db.commit()

    return redirecionar("/dashboard")


# ===================================================
# 17. PÁGINA PARA EDITAR TRANSAÇÃO
# ===================================================

@app.get(
    "/transacoes/{transacao_id}/editar",
    response_class=HTMLResponse,
    include_in_schema=False
)
def formulario_editar(
    transacao_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    usuario = usuario_web(
        request,
        db
    )

    if not usuario:
        return redirecionar("/login")

    registro = buscar_do_usuario(
        db,
        usuario.id,
        transacao_id
    )

    return pagina(
        request,
        "editar.html",
        registro=registro
    )


# ===================================================
# 18. SALVAR ALTERAÇÕES PELO SITE
# ===================================================

@app.post(
    "/transacoes/{transacao_id}/editar",
    include_in_schema=False
)
def salvar_edicao(
    transacao_id: int,
    request: Request,
    descricao: str = Form(...),
    valor: str = Form(...),
    tipo: str = Form(...),
    categoria: str = Form(...),
    data: date = Form(...),
    csrf: str = Form(...),
    db: Session = Depends(get_db)
):

    verificar_csrf(request, csrf)

    usuario = usuario_web(
        request,
        db
    )

    if not usuario:
        return redirecionar("/login")

    registro = buscar_do_usuario(
        db,
        usuario.id,
        transacao_id
    )

    try:
        dados = TransacaoEntrada(
            descricao=descricao,
            valor=Decimal(valor.replace(",", ".")),
            tipo=tipo,
            categoria=categoria,
            data=data
        )

    except (ValueError, InvalidOperation):
        raise HTTPException(
            status_code=422,
            detail="Dados inválidos"
        )

    for campo, valor_atual in dados.model_dump().items():
        setattr(
            registro,
            campo,
            valor_atual
        )

    db.commit()

    return redirecionar("/dashboard")


# ===================================================
# 19. EXCLUIR TRANSAÇÃO PELO SITE
# ===================================================

@app.post(
    "/transacoes/{transacao_id}/excluir",
    include_in_schema=False
)
def excluir_web(
    transacao_id: int,
    request: Request,
    csrf: str = Form(...),
    db: Session = Depends(get_db)
):

    verificar_csrf(request, csrf)

    usuario = usuario_web(
        request,
        db
    )

    if not usuario:
        return redirecionar("/login")

    transacao = buscar_do_usuario(
        db,
        usuario.id,
        transacao_id
    )

    db.delete(transacao)
    db.commit()

    return redirecionar("/dashboard")
