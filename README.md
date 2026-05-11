# Reservations API Python

Microsservico FastAPI responsavel por locais, salas, reservas, validacao local do JWT emitido pela Auth API e regra de conflito de horarios.

## Tecnologias

- Python 3.12
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Pydantic
- PyJWT
- pytest, pytest-cov, ruff, black e bandit

## Variaveis

Configure no ambiente ou copie `.env.example`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5434/reservations_db
JWT_SECRET=change-me-in-development-min-32-bytes
JWT_ISSUER=labtrans-auth-api
JWT_AUDIENCE=labtrans-reservas
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`JWT_SECRET`, `JWT_ISSUER` e `JWT_AUDIENCE` precisam ser iguais aos usados pela Auth API. O secret acima e apenas placeholder.

## Instalar

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Migrations e Seed

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m app.seed
```

O seed cria 3 locais e 4 salas.

## Rodar

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

URLs:

- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`

## Testes e Qualidade

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
.\.venv\Scripts\python.exe -m ruff check app tests alembic
.\.venv\Scripts\python.exe -m black --check app tests alembic
.\.venv\Scripts\python.exe -m bandit -r app
```

Cenarios cobertos:

- Health check.
- Token ausente, invalido, expirado, issuer errado, audience errada e secret errado retornam `401`.
- Listagem de locais, salas e reservas com token valido.
- Criacao, busca, edicao, exclusao e bulk delete.
- Campos obrigatorios de reserva.
- Fim menor ou igual ao inicio retorna erro.
- Cafe com quantidade nula ou zero retorna erro.
- Cafe falso permite quantidade nula.
- Regra de conflito completa, incluindo bordas 09:00-10:00 e 11:00-12:00.
- Edicao ignora a propria reserva e falha quando conflita com outra.
- Recursos inexistentes retornam `404`.

## Endpoints

- `GET /health`
- `GET /api/locations`
- `POST /api/locations`
- `GET /api/rooms`
- `GET /api/rooms?location_id=1`
- `POST /api/rooms`
- `GET /api/reservations`
- `GET /api/reservations/{id}`
- `POST /api/reservations`
- `PUT /api/reservations/{id}`
- `DELETE /api/reservations/{id}`
- `POST /api/reservations/bulk-delete`

Todas as rotas `/api/*` exigem:

```text
Authorization: Bearer <token>
```

## Regra de Conflito

```text
nova.start_datetime < existente.end_datetime
AND nova.end_datetime > existente.start_datetime
AND mesmo room_id
AND mesmo location_id
```

Na edicao, o ID atual e excluido da busca de conflito.
