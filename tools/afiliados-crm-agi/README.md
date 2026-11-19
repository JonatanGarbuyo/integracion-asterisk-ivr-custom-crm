# Dynamic Routes + AGI para Atenciones

**Estado19/11/2026: adaptación pendiente.** Los PHP de esta rama corresponden al contrato provisional de octubre y todavía NO implementan los endpoints reales. No están aceptados para instalar. El addon permanece pausado.

Contrato vigente: [ATENCIONES-CONTRACT.md](ATENCIONES-CONTRACT.md), recibido del desarrollador de Atenciones. Plan canónico: [spec45](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/45) y [ticket46](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/46); misma entrega en [PR47](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/pull/47).

## Flujo previsto

IVR1/2 → Dynamic Routes (CUIL) → GET /api/central/preatendedor → clave abstracta → destino PBX.
Cuando responde un miembro de la cola: QAGI → worker → POST /api/central/llamada-atendida.

Ambos requests usan X-Api-Key y el mismo UNIQUEID original del llamante. POST es formulario con sólo llamada/interno. Atenciones resuelve la operadora por Mi interno; el map interno→usuarioCRM queda eliminado del diseño.
Opción3 omite GET y requiere destino PBX acordado.

## Estado de las fuentes existentes

- crm_get_afiliado.agi.php y common.php: adaptar URL/auth, opción del menú, schema JSON y reglas; timeout total3s.
- crm_set_atencion.agi.php y crm_worker.php: quitar datos de afiliado y map CRM, enviar formulario con llamada/interno, conservar id original.
- config.example.conf: reemplazar endpoints/token provisional y asociaciones de usuarios por configuración del contrato real.
- mock_crm_server.py: adaptar todos los casos y errores al schema confirmado.
- Falta tests/test_afiliados_crm_agi.py y la validación de PHP5.4/PBX reales.
- Ningún cambio de código se declara realizado por actualizar estos documentos.

## Configuración objetivo

Dos Dynamic Routes, opción fija1 o2 como argumento del mismo AGI; captura mediante Read/dtmfinput verificada en dialplan. Evitar CUIL en argv y copias heredables; detalles en el contrato.
AGI Result Variable: CRM_ROUTE_KEY.
CALL_CENTER → cola6000; INVALID_CUIL → anuncio y colgar; END_CALL → colgar; PORTAL → anuncio web por confirmar; Default → Call Center.
Esta tabla refleja la propuesta recibida y se confirma antes de activarla. No inferir destino0800 para Portal.

## Rutas previstas

- Scripts: /var/lib/asterisk/agi-bin/crm_get_afiliado.agi.php y crm_set_atencion.agi.php.
- Auxiliares: /var/lib/asterisk/agi-bin/afiliados-crm/.
- Config externa: /etc/asterisk/afiliados-crm.conf; root:asterisk0640.
- Código: root:asterisk0750; job temporal privado con sólo llamada/interno.
- Runtime: PHP5.4+ CLI, cURL/JSON; sin Composer, addon ni listener AMI.

Cola6000 usa Local/<interno>@from-queue/n y QAGI, confirmado en cliente.
setinterfacevar=yes en [6000](+) de queues_post_custom.conf, verificando que se incluye después de queues_additional.conf. Preservar QAGI/VQ_AGI ajenos. No editar generado.
Los comandos finales de instalación y prueba se completan con el código corregido y aceptado.

## Pendientes de prueba real

URL testing y clave por canal seguro; IP de origen efectiva y certificado HTTPS; CUIL ficticios de cada caso; operadora con Mi interno en Atenciones; confirmar reglas, destino opción3 y URL/finalización del Portal.
La prueba de caída del servidor debe mantener ingreso al Call Center. Un fallo de aviso nunca detiene la llamada.

## Continuidad de ejecución

#48 sigue needs-info por ejecución no-changes sin explicación; no hay una corrección OpenCode activa ni se relanza por recibir este documento. Hace falta completar la entrega y sus revisiones/CI; no se acepta un gate ausente o de un HEAD anterior.
