# Bootstrap de #40

## Frontera activa: #41

**Pausado tras run 38265908134:** Spec y Standards FAIL; el artifact sólo contiene estados, sin fuente ni hallazgos. No relanzar. La auditoría y propuesta de una excepción operativa mínima están en #41 y requieren autorización explícita antes de cambiar controles. El contrato de roles actual sigue vigente.

El intento amplio de #40 (run 38263830613) falló en checks y el legado conservó sólo `result.json`; no hay fuente recuperable ni PR. #40 queda pausado. Primero se implementa #41: conservación de candidatos, recuperación desde worktree limpio y ruta de revisión del PR de controles durante bootstrap. Leer su ticket y comentarios completos; su alcance específico limita este plan general. Escribir esa entrega en `docs/bootstrap/recovery-foundation` y sus pruebas públicas en `tests/test_recovery_foundation.py`. No reconstruir el candidato perdido desde logs ni reimplementar todo el orquestador en esta entrega.

Los checksums del handoff se producen con una herramienta determinista escrita por OpenCode que ejecuta el operador confiable. No pedir al modelo hashes inventados ni permitir que el operador complete código. Los reviews/CI del HEAD final siguen siendo obligatorios. Después de aceptar #41 se retoma #40 y, al completar ese flujo, #38.

El usuario autorizó completar el flujo el 12/10/2026: ChatGPT planifica y acepta; OpenCode implementa/corrige y ejecuta Standards/Spec; los controles publican. La aceptación exige gates completos, ambas revisiones PASS y CI exitoso del HEAD actual antes de cada merge. El producto #38 permanece pausado.

El controlador de main `db138b2c3bd14c61313d3a1dd0beb17a2306089d` permite editar `docs/`, `tools/` y `tests/`, pero protege los controles vivos y rechaza `.opencode`. Este directorio permite generar un handoff sin ampliar esos permisos ni entregar el token GitHub al modelo.

## Entrada del implementador

Leer #40 y comentarios, #31, `payload/AGENTS.md`, `payload/GLOSSARY.md`, `payload/docs/agents/project-state.md`, `payload/docs/agents/opencode.md`, el ADR de roles y las skills de `payload/.agents/skills/`. Las fuentes de `reference/` son copias sin modificar de los controles ya aprobados; no son la implementación nueva.

## Entrega de OpenCode

1. Escribir el orquestador, gates y workflows nuevos bajo `docs/bootstrap/generated/`, con sus pruebas públicas bajo `tests/test_bootstrap_*.py`. Mantener íntegro el addon de v0.2.8. No editar los controles vivos ni el formulario #38.
2. Probar los seams aprobados en #40: eventos CLI/JSON, Git real en repos temporales y API GitHub/ejecutable OpenCode como fronteras externas. Verificar candidato -> PR draft -> fallo/revisiones -> corrección del mismo PR, reportes del HEAD exacto y recuperación con límites/exclusiones. No llamadas a proveedores ni credenciales reales en tests.
3. Incluir un manifiesto `docs/bootstrap/handoff.json` con versión, destino de cada archivo generado/de payload, checksum SHA256 de cada contenido y archivos de workflow afectados. Todos los paths son relativos; no symlinks ni datos secretos. El paquete completo debe funcionar al copiar sus bytes a los destinos finales, sin reconstrucción del operador.
4. El handoff incluye una ejecución de revisión de PR antes del merge inicial: Standards/Spec desde configuración aprobada, informes separados en el PR y CI del mismo SHA. El código nuevo debe conservar la ruta de bootstrap aplicación/control mientras el addon aún viva fuera de main.
5. Documentar el comando de prueba del paquete en staging y cómo publicar/ejecutar los gates del HEAD final. Mantener timeout/terminación y guards; no publicar como PASS un reporte ausente, incompleto o de otro SHA.

## Publicación confiable

El flujo legado puede emitir un PR de staging después de sus propios gates. Esos checks/reviews son evidencia auxiliar del bootstrap, no la aceptación final del nuevo flujo. El operador verifica el handoff y publica sólo los bytes generados por OpenCode y la documentación de planificación autorizada, contra main en un PR draft. Antes de aceptar, el nuevo ciclo debe publicar sus dos revisiones del HEAD real y completar CI. Después se mergea una entrega y se retoma #38 con el flujo actualizado.

El operador no completa código faltante ni transforma archivos de implementación. Si el paquete es parcial o falla, registrar evidencia y continuar con OpenCode. No sustituirlo con agentes GPT del workspace. No promover producción ni modificar secretos.

## Skills importadas

`wayfinder`, `to-spec`, `to-tickets`, `implement`, `tdd` y `code-review` se copian sin cambios del snapshot `9a5e0c75717a6e4707e9964aa550ffbd9a091f52` de `JonatanGarbuyo/user-service-platform`, incluyendo referencias TDD. No hay TypeScript en este proyecto: `better-typescript` se incorpora cuando corresponda a una entrega TypeScript, no como dependencia del runtime PHP/Python.
