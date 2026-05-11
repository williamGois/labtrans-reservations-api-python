# ADR-001 - Observability Strategy

## Contexto

A Reservations API aplica regra de negocio critica de conflito de horario e valida JWT localmente. Falhas precisam ser rastreadas sem chamar a Auth API a cada requisicao e sem expor tokens.

## Decisao

- Usar `X-Correlation-ID` como identificador transversal entre front-end, Auth API e Reservations API.
- Emitir logs JSON com contexto operacional e sem dados sensiveis.
- Separar `/health/live` de `/health/ready`.
- Expor metricas Prometheus para HTTP, reservas, conflitos, JWT e banco.
- Ativar tracing OTLP somente quando configurado por ambiente.
- Padronizar erros com `title`, `status`, `detail`, `correlationId` e `timestamp`, preservando `message` para compatibilidade com o front-end.

## Seguranca

Nao logar:

- JWT completo.
- Header `Authorization`.
- `JWT_SECRET`.
- Connection string.
- Labels de metricas com alta cardinalidade.

## Consequencias

O avaliador consegue responder qual requisicao falhou, qual token foi rejeitado por categoria, quantos conflitos ocorreram e se o banco esta pronto.
