# Vocabulario de CallFlow Hooks

- **Perfil:** configuración de una integración. Tiene identidad técnica estable y un nombre visible editable.
- **Handler:** ejecutable local que recibe/devuelve el contrato JSON y realiza un comportamiento; no administra AGI directamente.
- **Adaptador:** traduce el contrato de un sistema externo. El negocio no se incorpora al núcleo.
- **Contexto de interacción:** datos transitorios y versión de configuración de una llamada, independientes de otras llamadas.
- **Destino aprobado:** destino Asterisk permitido por el perfil; un sistema externo no entrega instrucciones arbitrarias de dialplan.
- **Destino de contingencia:** salida configurada ante fallo, timeout, respuesta inválida o perfil deshabilitado.
- **Gate:** comprobación necesaria para aceptación; su ausencia o fallo no equivale a PASS.
- **Candidato:** commit generado por OpenCode, no aceptado hasta completar los gates de su HEAD.
- **Standards / Spec:** ejes independientes de revisión de reglas del repo y requisitos del ticket/spec.
- **Handoff confiable:** paquete de cambios con procedencia y checksums que el operador publica sin entregar privilegios de publicación al modelo.
- **Checkpoint:** estado operativo fechado que se reconcilia con GitHub; no reemplaza tickets ni decisiones.

Afiliado, obra social, operador, interno y ficha del afiliado pertenecen al primer caso de uso, descrito en `CONTEXT.md`; no son restricciones del addon genérico.
