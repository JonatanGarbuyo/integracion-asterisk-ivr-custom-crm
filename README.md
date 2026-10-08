# Integración Asterisk IVR ↔ CRM

Identificación de afiliados por CUIL, consulta de obra social, enrutamiento a cola/0800 y aviso stateless del operador que respondió. Soporte objetivo: Issabel 4/Asterisk 16 e Issabel 5/Asterisk 18, pendiente de comprobar en las instalaciones reales.

Estado: especificación y planificación publicadas; implementación de PBX aún no iniciada.

- [Mapa Wayfinder: integración IVR y colas Issabel ↔ CRM](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/1).
- [Especificación: integración IVR y colas Issabel ↔ CRM](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/2).
- [Entregas y dependencias](docs/planning/index.md).
- [Primera llamada completa con CRM simulado](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/11): punto de partida con una PBX de laboratorio y CRM simulado.
- [Investigación técnica](docs/research/mecanismos-asterisk.md).
- [Vocabulario](CONTEXT.md).

La consulta del IVR espera una respuesta acotada. El aviso desde Queue sale fuera del AGI sin esperar al CRM, sin sesión ni persistencia de notificaciones. La configuración operativa se mantiene en .conf custom; DNI y formulario web son ampliaciones opcionales.

Para continuar con las skills, seguir [AGENTS.md](AGENTS.md). Las relaciones de issues se conservan mediante el [workflow de planificación](.github/workflows/sync-planning.yml).
