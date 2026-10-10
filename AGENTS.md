# Trabajo en este repositorio

## Agent skills

### Issue tracker

Antes de planificar, reclamar o resolver trabajo, leer `docs/agents/issue-tracker.md`. GitHub Issues contiene los mapas Wayfinder, la especificación y los tickets canónicos; el índice está en `docs/planning/index.md`.

### Triage labels

Antes de cambiar estados de trabajo, leer `docs/agents/triage-labels.md`. `ready-for-agent` requiere además bloqueos cerrados y accesos externos disponibles; `optional` necesita que el usuario seleccione esa mejora.

### Domain docs

Antes de cambiar vocabulario o alcance, leer `CONTEXT.md` y `docs/agents/domain.md`. Usar un contexto único para atención de afiliados.

## Implementación

- Leer la especificación y el ticket elegido; trabajar una entrega verificable por rama y PR.
- Consultar `docs/research/mecanismos-asterisk.md` al cambiar los hooks de Asterisk o identificar miembros de cola; validar las versiones realmente instaladas.
- Mantener CUIL y datos del afiliado en variables por llamada. La consulta espera con límite; el aviso al CRM sale fuera del AGI sin esperar respuesta remota.
- La configuración operativa reside en `.conf` custom. Preservar el dialplan generado y las funciones existentes de las colas.
- Completar cambios y validación de laboratorio antes de preparar un piloto. Una publicación documental o un ticket listo no certifican la PBX de producción.
- Conservar las propuestas de política como propuestas hasta que el usuario las acuerde; registrar los bloqueos externos en la issue.
- Al finalizar una entrega, informar conducta observada, validación y límites en la issue y el PR.

## Workers externos

- Seguir [OpenCode en Actions](docs/agents/opencode.md). Sólo implementar la issue abierta autorizada, con `ready-for-agent` y sus dependencias cerradas.
- No cambiar los controles de automatización, workflows, política de agentes ni modelos desde un worker. No leer/transmitir credenciales ni datos reales del cliente; usar mocks de laboratorio.
- No hacer commit, push, merge, release ni deploy desde el modelo. La orquestación publica sólo el commit que aprobó checks y ambas revisiones. Informar decisiones pendientes en vez de ampliar alcance.
