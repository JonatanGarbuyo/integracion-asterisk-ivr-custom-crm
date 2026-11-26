# Handoff de controles

Los modelos escriben cambios locales sin token GitHub ni privilegio de workflow-write. Cambios de `.github/workflows/**`, controles o configuración de agentes se publican mediante un operador confiable, separados del worker de producto.

El paquete debe incluir paths relativos origen/destino, base/HEAD y SHA256 de cada contenido, archivos de workflow afectados y estado de completitud. Rechazar rutas fuera de la entrega, symlinks, secretos y material truncado. La procedencia debe enlazar ticket, run y commit de OpenCode; una mención o label no demuestra aprobación.

El operador verifica el paquete y publica exactamente sus bytes en PR draft. No completa implementación faltante. Después se ejecutan Standards/Spec desde configuración aprobada y CI sobre el HEAD publicado. Ningún handoff, review legado o check local sustituye esos gates.

Bootstrap #40: `docs/bootstrap/` contiene planificación/skills copiadas y código generado por OpenCode en rutas permitidas. La importación final aplica el manifiesto aprobado sin modificar el código del modelo. Si el paquete es incompleto, vuelve al implementador.
