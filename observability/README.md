# Observability Stack

Stack local opcional para avaliar metricas e traces dos servicos LabTrans.

## Requisitos

- Auth API em `http://localhost:5001`
- Reservations API em `http://localhost:8000`
- Docker Desktop

## Subir

```powershell
cd observability
docker compose -f docker-compose.observability.yml up -d
```

## Acessos

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)
- OTLP gRPC: `http://localhost:4317`
- OTLP HTTP: `http://localhost:4318`

## Prometheus

O Prometheus coleta:

- `host.docker.internal:5001/metrics`
- `host.docker.internal:8000/metrics`

## Tracing

Para enviar traces ao collector local, defina nos dois back-ends:

```env
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

O collector configurado aqui usa exporter `debug`, suficiente para validar emissao local sem depender de Jaeger/Tempo.
