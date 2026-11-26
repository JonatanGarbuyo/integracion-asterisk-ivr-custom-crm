# Ejecución y aceptación

Leer AGENTS, checkpoint, glosario, ticket completo/comentarios, spec padre, ADRs y configuración actual antes de actuar. Las skills residen en `.agents/skills/`; agentes y comandos en `.opencode/`. Los modelos gratuitos aprobados se declaran en esos archivos, no se copian al checkpoint.

## Ticket

1. Confirmar issue abierta `ready-for-agent`, autorización y bloqueadores cerrados. Consultar runs activos antes de `/agent-ticket`.
2. Implementar en rama/worktree aislado con TDD en seams acordados. Modelo sin token GitHub, datos de producción ni configuración operativa del cliente.
3. Los guards publican candidato y PR draft antes de revisiones. Un check fallido deja PR/evidencia, no una falsa aceptación.
4. Ejecutar gates y Standards/Spec independientes. Publicar informes separados asociados al HEAD exacto. CI debe completar exitosamente sobre ese mismo HEAD.
5. El operador revisa criterios/diff/evidencia. Sólo entonces acepta y mergea una entrega. Despliegue y producción son estados separados.

## Corrección

Si existe PR, `/agent-fix-cycle` continúa ese HEAD con sus comentarios/gates. Después de publicar correcciones, ambos reviewers y CI deben renovarse. No usar aprobación de un SHA anterior. Los estados `action_required`, timeout, check fallido o informe ausente siguen pendientes.

Ante fallo, inspeccionar primero logs, comentarios y artifacts. Usar `implementation-recovery.md`; si no hay fuente recuperable, reconocerlo. No relanzar a ciegas ni sustituir OpenCode por GPT.

## Configuración y publicación

Conservar CLI y límites aprobados durante #40; no añadir fallback pago ni credenciales al entorno de checks/modelos. El controlador toma configuración de agentes/comandos aprobada y valida modelos/roles/permisos. Configs de un candidato no amplían permisos ni se autoaprueban.

Cambios de workflows/controles necesitan `workflow-handoff.md`: OpenCode los escribe; guards conservan evidencia; el operador publica bytes verificados sin entregar workflow-write al modelo. El paquete publicado permanece draft hasta reviews y CI del HEAD real.

Pruebas del addon mantienen PHP5.4, Python3.6/3.9/3.12 y RPM. La automatización se prueba en su CLI/Git/API pública con dobles externos, sin proveedor real ni secretos. Una conexión real de modelos o publicación se registra separadamente de pruebas offline.
