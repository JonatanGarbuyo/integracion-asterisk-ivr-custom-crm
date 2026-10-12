# Recuperación de implementación

Este procedimiento requiere evidencia del controlador; no reconstruir código desde logs. Si el artifact contiene sólo resultado, declarar que la fuente no es recuperable.

1. Verificar resultado original, terminación acotada del worker, base/HEAD/branch, conteos y flags de truncación/exclusión. Un check fallido no se convierte en timeout.
2. Si existe PR, conservarlo como punto de continuidad. Si hay handoff de workflow, verificar procedencia y destinos antes de publicar.
3. Crear worktree limpio en la base registrada. Comprobar y aplicar el patch incluido; crear sólo archivos elegibles con contenidos/checksums completos. No aplicar material truncado como si fuera íntegro.
4. Ejecutar gates y registrar material ausente. OpenCode completa o corrige lo que falte. La recuperación no acredita aceptación.
5. Publicar mediante guards, renovar Standards/Spec y CI del HEAD actual; el operador decide aceptación.

La evidencia preserva cambios comprometidos y no comprometidos y archivos fuente elegibles, con límites finitos y exclusiones explícitas. Excluir secretos, `.env`, keys, symlinks, logs, datos operativos y transcripciones de modelos. Si no se confirma la terminación del proceso, no leer un snapshot en escritura: registrar unavailable.
