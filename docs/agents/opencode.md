# OpenCode en GitHub Actions

Automatización autorizada en [#31](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/31), adaptada del flujo de `user-service-platform`. La herramienta genera cambios de laboratorio; las issues siguen delimitando alcance y autorización. Esta entrega no autoriza merge del PR #30 ni ejecutar tickets de negocio bloqueados.

## Activación

1. Integrar el PR de automatización en **main**. GitHub sólo reconoce `issue_comment` y `workflow_dispatch` cuando el workflow está en la rama por defecto. No basta con descargar el addon en Issabel.
2. Configurar **Actions secret** `OPENCODE_ZEN_API_KEY` en Settings → Secrets and variables → Actions → Secrets. No guardarlo como variable pública ni en archivos. El usuario informó que ya configuró la clave; sólo el diagnóstico comprueba que es válida.
3. En Settings → Actions → General → Workflow permissions, habilitar **Allow GitHub Actions to create and approve pull requests**. El flujo sólo crea PRs borrador; no aprueba ni mergea. No requiere PAT ni instalar una GitHub App de OpenCode.
4. Ejecutar Actions → **CallFlow agent** → Run workflow: rama del workflow **main**, operation **probe**, base **feat/callflow-generic-profile**. Esta operación consulta ambos modelos y verifica que no cambiaron archivos. No implementa tickets ni abre PRs.

El código del addon está en `feat/callflow-generic-profile` mientras el PR #30 siga abierto; main contiene planificación. Tras aprobar e integrar esa entrega, usar base main. La base del código es un input independiente de la rama que contiene los controles confiables.

## Uso

- Issue abierta, autorizada, con `ready-for-agent` y sin bloqueos abiertos: comentar exactamente `/agent-ticket`. Se puede elegir ticket/base desde Run workflow.
- PR borrador creado por ese flujo: comentar exactamente `/agent-fix-cycle`. No acepta forks ni PRs arbitrarios; vuelve a comprobar el ticket de origen.
- El flujo serializa ejecuciones, limita cada worker y las rondas de corrección, y detiene publicación ante errores, decisiones pendientes o cambios no permitidos.
- No cerrar #21 sólo para desbloquear #22: su aceptación de laboratorio sigue pendiente. Agregar una etiqueta no sustituye autorización ni cierra dependencias.

Los comandos sólo se aceptan de usuarios con permisos de escritura. No se ejecutan al recibir comentarios ordinarios, abrir issues o actualizar PRs. La orquestación conserva GitHub como canal de publicación; el modelo recibe contexto de issue/especificación y trabaja en un árbol separado sin token GitHub en su entorno.

## Modelos y pruebas

| Rol | Modelo fijado |
|---|---|
| Implementación y Spec | `opencode/muse-spark-1.3-contributor-free` |
| Standards | `opencode/mimo-v2.6-flash-free` |

OpenCode CLI se fija en **1.18.30**. El modelo para tareas auxiliares también es gratuito. No hay selección automática de proveedores, fallback pago ni sesiones compartidas. La disponibilidad de modelos gratuitos puede cambiar; si falla un modelo el flujo se detiene. Las revisiones aceptan marcadores PASS sólo para el commit exacto y con árbol sin cambios.

Antes de publicar se exige suite completa de procesos JSON/AGI y formulario con PHP5.4/Python3.12, sintaxis PHP, RPM, matriz Python3.6/3.9/3.12 en Docker y formularios/estado PBX con PHP8.2 como usuario no root. Se conservan las pruebas existentes; no se admite una rama con cero tests. Las dependencias de sistema se instalan en el runner, nunca en la PBX.

PRs creados con GITHUB_TOKEN no disparan automáticamente otros workflows. Los checks obligatorios se ejecutan dentro de este run antes de publicar y su enlace se registra en el PR. Los checks independientes del addon requieren una ejecución humana o posterior evento autorizado; no se anuncia que ya corrieron. La ejecución offline **CallFlow automation checks** valida controles y contrato CLI sin claves ni llamadas a modelos.

## Límites y diagnóstico

Los workers no pueden publicar cambios a workflows, controles de automatización, políticas de agentes ni archivos de secretos. Ese trabajo requiere un PR separado revisado. Se rechazan configuraciones/plugins OpenCode propias del árbol de trabajo para evitar cambiar los modelos fijados. No es un aislamiento contra código deliberadamente hostil: se trabaja en repositorio, actores y tickets aprobados, en runners efímeros.

No enviar credenciales, `.env`, datos reales de afiliados ni configuración operativa del cliente. Los modelos Contributor/gratuitos pueden usar prompts para mejorar modelos; aquí reciben sólo código y mocks de laboratorio. El runner recibe la clave del proveedor necesaria para invocarlo y el token GitHub limitado de orquestación; no recibe secretos de producción.

Actions conserva resultado, fases, commit, modelos y enlace al PR en metadata. No se publican transcripciones de modelos ni configuración con claves. Si falta la clave, falla un modelo/check o la revisión requiere decisión, corregir la causa antes de repetir. Fallo de publicación de PR suele requerir revisar el permiso de creación de PRs. El resultado simulado/offline no demuestra conexión real con Zen ni instalación en Issabel.

## Fuentes

- [Flujo de referencia](https://github.com/JonatanGarbuyo/user-service-platform/blob/main/.github/workflows/agent-ticket.yml).
- [CLI y variables](https://opencode.ai/docs/cli/).
- [Configuración](https://opencode.ai/docs/config/).
- [Modelos Zen](https://opencode.ai/docs/zen/).
- [Eventos y GITHUB_TOKEN](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow).
