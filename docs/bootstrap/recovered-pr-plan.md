# Retomar el PR recuperado #43

Frontera canónica: [ticket #44](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/44), derivado de #40. #41 y su PR #43 quedan pausados hasta aceptar este handoff. El usuario autorizó continuar el desbloqueo el 13/10/2026.

OpenCode entrega en docs/bootstrap/generated/recovered-pr/ y tests/test_bootstrap_recovered_pr.py, sin editar controles vivos ni el código fallido de #41. Leer el ticket completo/comentarios y skills implement/tdd/code-review de payload. Mantener los modelos, CLI y límites aprobados.

La autorización especial se limita a la procedencia de #43 registrada en #44: validar el HEAD inicial/árbol y su linaje antes de cada continuación; preservar el mismo PR y publicar cada candidato validado antes de gates. Mantener protección de actor/repos/base/paths y lease de HEAD/base. No aceptar PR arbitrarios del owner ni afirmar que borrar el filtro de autor sea suficiente.

La ruta de revisión del handoff final se publica como bootstrap/recovered-pr-controls contra main, draft, con marcador callflow-recovered-pr-bootstrap:44. Los helpers/workflow deben evaluar el alcance de #44/#40, usando perfiles aprobados y marcadores del SHA real. #42 no aprueba una nueva entrega.

El operador publica sólo bytes verificados del handoff y realiza aceptación final con Spec/Standards PASS y CI del HEAD actual. No modifica código, suplanta bot, hace merge con gates pendientes, release ni deploy. Antes de cualquier ejecución comprobar que no exista trabajo activo.

Tras aceptar #44, /agent-fix-cycle sobre #43 retomará #41 desde su código recuperado. #40/#38 siguen después. No rehacer la fuente de #41 desde logs ni lanzar otra implementación de ese ticket desde la base sin candidato.
