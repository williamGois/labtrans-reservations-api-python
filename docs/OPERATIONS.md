# Reservations API Operations

## Health

```powershell
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

- `/health/live` valida somente que o processo responde.
- `/health/ready` valida banco e variaveis obrigatorias (`DATABASE_URL`, `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE`).
- Secrets nunca sao retornados.

## Metrics

```powershell
curl http://localhost:8000/metrics
```

Metricas principais:

- `http_requests_total`
- `http_request_duration_seconds`
- `http_requests_in_progress`
- `reservations_created_total`
- `reservations_updated_total`
- `reservations_deleted_total`
- `reservations_conflict_total`
- `reservations_bulk_deleted_total`
- `reservations_jwt_validation_failure_total`
- `reservations_jwt_missing_total`
- `reservations_jwt_expired_total`
- `reservations_database_errors_total`

Labels evitam alta cardinalidade. Nao ha labels com `email`, `userId`, `reservationId`, token ou `correlationId`.

## Logs

Logs em JSON no console com:

- `serviceName`
- `environment`
- `correlationId`
- `method`
- `path`
- `route`
- `statusCode`
- `elapsedMs`
- `userId`, quando extraido do JWT

JWT completo, header `Authorization` e `JWT_SECRET` nao sao logados.

## Correlation ID

Envie:

```text
X-Correlation-ID: suporte-123
```

A API devolve o mesmo valor. Se o header nao vier, a API gera um identificador.

## Diagnostico

### 401

1. Confirme se o header `Authorization: Bearer <token>` existe.
2. Confirme `JWT_SECRET`, `JWT_ISSUER` e `JWT_AUDIENCE` iguais aos da Auth API.
3. Consulte `reservations_jwt_validation_failure_total`.
4. Filtre logs por `correlationId`.

### 409 conflito de horario

1. Confira `location_id`, `room_id`, `start_datetime` e `end_datetime`.
2. A regra e `nova.start < existente.end AND nova.end > existente.start`.
3. Consulte `reservations_conflict_total`.
4. Use o `conflictingReservationId` retornado no erro.

### Banco indisponivel

1. Execute `/health/ready`.
2. Confirme se o PostgreSQL de reservas esta ativo.
3. Confira `DATABASE_URL`.
4. Consulte `reservations_database_errors_total`.

## Smoke test operacional

Com as duas APIs rodando:

```powershell
python scripts/operational_smoke_test.py
```

Variaveis opcionais:

```env
AUTH_API_URL=http://localhost:5001
RESERVATIONS_API_URL=http://localhost:8000
```

## Observability stack local

Configuracao opcional em `observability/`:

```powershell
cd observability
docker compose -f docker-compose.observability.yml up -d
```

Prometheus: `http://localhost:9090`
Grafana: `http://localhost:3000`

## OpenTelemetry

Tracing e opcional:

```env
OTEL_SERVICE_NAME=labtrans-reservations-api-python
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```
