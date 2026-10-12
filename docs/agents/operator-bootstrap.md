# Excepción operativa de #41

Autorizada por el usuario el 12/10/2026, en respuesta a la propuesta registrada en #41. El operador prepara este único bootstrap; OpenCode conserva las revisiones y la implementación posterior. El PR permanece draft antes de los reviewers. Aceptación: ambos informes PASS y CI del HEAD actual, sin conflictos. No cierra #41 ni habilita #38 o producción.

## Alcance verificable de este PR

- El prompt permite generar controles como **handoff inerte** exclusivamente en staging aprobado; los guards y permisos continúan protegiendo controles vivos y plugins.
- Tras validar/comprometer cada candidato, antes de gates, exportar el diff binario y fuentes desde objetos Git inmutables, con base/HEAD/árbol, SHA256, modos y límites explícitos. Árbol sucio, terminación no confirmada, paths protegidos/operativos, symlinks o límites excedidos impiden fuente completa. No exportar archivos que un worker siga escribiendo ni ignorados de laboratorio.
- Conservar únicamente el último mensaje final validado de cada reviewer, con eje/modelo/HEAD. Guardar informes de ambos intentos, incluidos FAIL; subir la carpeta completa de evidencia. Nunca exportar stream/transcripciones, entorno o configuraciones con claves.
- Revisar este PR draft mediante dos procesos independientes OpenCode desde los perfiles declarativos preparados para `.opencode`, fijados al snapshot `cd0db4c4038c942e3f4653e7166936412e22d593`. El harness impone permisos de sólo lectura y los modelos gratuitos ya aprobados. Informes con marcador de HEAD exacto en el PR; CI checkout del mismo HEAD.

La CLI se conserva en 1.18.30, workers en 600 segundos y 24 pasos. Los modelos no reciben token GitHub ni permisos de publicación/merge/deploy. El uploader recibe únicamente archivos creados por los controles confiables, fuera del worktree del worker.

## Recuperar un candidato comprometido

`candidate-<sha>/manifest.json` declara `status=complete`, `base_sha`, `head_sha`, `tree_sha`, SHA256 de patch/fuentes y exclusiones/límites. Verificar estos valores y checksums del artifact; partir de un worktree limpio en `base_sha`; ejecutar `git apply --index --binary candidate.patch`; verificar que `git write-tree` coincida con `tree_sha`. Un status incompleto/unavailable no acredita recuperación íntegra. La prueba pública reproduce este recorrido en repos Git reales.

Captura manual: `python3 tools/agent_evidence.py snapshot --workspace <repo> --base <base-sha> --head <head-sha> --output <directorio-nuevo-fuera-del-repo> --worker-terminated`. El flag sólo es válido cuando el controlador confirmó que el worker terminó; la automatización lo usa después de que retornó y se validaron sus cambios.

Pendiente para OpenCode/#41/#40: cambios no comprometidos tras timeout, recuperación automatizada integral y publicación/reanudación del PR antes de gates. El legado todavía publica su PR después de ambas revisiones; esta entrega conserva evidencia aunque falle. Ninguna prueba offline o captura constituye aprobación ni validación instalada de la PBX.
