# Issue tracker: GitHub

Repositorio: `JonatanGarbuyo/integracion-asterisk-ivr-custom-crm`.

GitHub Issues es la fuente de verdad del mapa, de las decisiones, de la especificación y de las entregas. `docs/planning/index.md` es un índice de enlaces; no copiar cuerpos de issues al repositorio como tickets paralelos.

## Publicar y trabajar

1. Buscar por título antes de crear una issue para evitar duplicados.
2. Leer la issue completa y sus comentarios antes de tomar trabajo.
3. Reclamar por asignación al usuario que conduce el trabajo; responsable actual: `JonatanGarbuyo`.
4. Trabajar sólo cuando los bloqueos están cerrados y los requisitos externos disponibles. Un label no elimina una dependencia.
5. Registrar resultados y evidencia en comentarios; actualizar y cerrar sólo el trabajo realmente resuelto.

PRs como superficie de solicitud de trabajo: desactivado. Los PRs se usan para revisar cambios de implementación vinculados a tickets.

## Wayfinding operations

- Mapa: issue `wayfinder:map`, con Destination, Notes, Decisions so far, Not yet specified y Out of scope.
- Tickets de decisión: sub-issues nativas del mapa con `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling` o `wayfinder:task`.
- Bloqueos: relaciones nativas `blocked_by` de GitHub. Los enlaces por título del cuerpo facilitan revisión, pero las relaciones nativas definen la frontera.
- Frontera: hijos abiertos, no asignados, cuyos bloqueos estén cerrados; ordenar por número de issue para elegir el primero.
- Resolver: comentario de resolución y evidencia, cerrar la decisión y agregar sólo un resumen con enlace por título a Decisions so far del mapa.
- La especificación es una issue independiente y sus sub-issues son entregas de implementación, no decisiones de Wayfinder.

## Relaciones nativas

El manifiesto `docs/planning/github-issues.json` registra los números, padres y bloqueos previstos para la migración inicial. El workflow `Sincronizar relaciones de planificación` agrega de forma idempotente sub-issues y dependencias en GitHub cuando cambia el manifiesto o se ejecuta manualmente.

El workflow usa únicamente permisos `contents:read` e `issues:write`; conserva cuerpos, estados y responsables. No reemplaza padres existentes ni elimina relaciones. Después de cambios manuales en GitHub, mantener el manifiesto alineado para evitar reintroducir bloqueos retirados.

Si una sincronización falla, consultar el run en Actions y la relación real antes de continuar. En GitHub pueden usarse directamente las APIs nativas cuando la herramienta disponible las exponga.
