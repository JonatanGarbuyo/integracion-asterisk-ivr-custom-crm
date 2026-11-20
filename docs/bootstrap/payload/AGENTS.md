# Contrato de trabajo de CallFlow Hooks

## Antes de actuar

Leer `docs/agents/project-state.md`, `GLOSSARY.md`, el ticket completo y sus comentarios, la spec padre y los ADR relevantes. Contrastar el checkpoint con GitHub. Las issues son canónicas: `docs/agents/issue-tracker.md` y `docs/agents/triage-labels.md`.

## Flujo y roles

- Decisiones pendientes: `wayfinder` -> `to-spec` -> `to-tickets`. Ticket aprobado: continuar en `implement`, sin repetir planificación.
- Usar las skills locales de `.agents/skills/`, leyendo su contenido. Un ticket `ready-for-agent`, sin bloqueadores abiertos, por rama/worktree aislado. No implementar una spec padre.
- ChatGPT prepara decisiones, tickets y aceptación final. OpenCode implementa/corrige y realiza Standards/Spec independientes. Consultar `.opencode/agents/` y `.opencode/commands/` para sus configuraciones actuales.
- Ejecución habitual en GitHub: `/agent-ticket` en issue; `/agent-fix-cycle` en el PR existente. Comprobar antes que no haya un workflow activo del mismo trabajo.
- Los workflows publican mediante guards. Abrir PR draft antes de revisiones adversariales. Reportes en el PR con eje y SHA exacto. Cambiar HEAD invalida ambas revisiones y CI anteriores.
- Aceptar sólo criterios satisfechos, gates completos, Standards PASS, Spec PASS y CI exitoso del HEAD actual. Timeout, `action_required` y reporte ausente son pendientes, no aprobación. Las revisiones GPT auxiliares no sustituyen estos gates.
- El usuario autorizó merges uno por uno, sin conflictos y después de aceptación. Los modelos no hacen merge/deploy ni cambian secretos. Producción permanece fuera de alcance.

## Implementación y fallos

- Tests de comportamiento público en seams acordados: JSON/AGI, formulario PHP, CLI e interfaces externas. Leer `tdd`; evitar tests tautológicos y mocks internos.
- Ante fallo, leer logs, comentarios y artifacts antes de repetir. Recuperar desde un worktree limpio siguiendo `docs/agents/implementation-recovery.md`; reconocer exclusiones y truncación. Si existe PR, continuar desde él.
- Preservar dialplan generado, colas y configuración operativa. Consultar investigación de Asterisk antes de cambiar hooks. Mantener PHP5.4/Python3.6 en el addon; no afirmar validación instalada a partir de mocks.
- CallFlow Hooks es genérico; el negocio de Afiliados CRM pertenece a su extensión. Perfil, handler y adaptador tienen contratos separados.
- Registrar evidencia y reconciliar checkpoint. Reportar por separado implementación, pruebas, revisiones, merge y despliegue.

Detalles de ejecución y publicación: `docs/agents/opencode.md`. Cambios de controles: `docs/agents/workflow-handoff.md`.
