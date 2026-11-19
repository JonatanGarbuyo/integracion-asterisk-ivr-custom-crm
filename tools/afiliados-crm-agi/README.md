# Dynamic Routes + AGI para Atenciones

**Estado19/11/2026: código pendiente de adaptar y validar.** El alcance confirmado son dos AGI standalone; el addon está pausado.

## Flujo acordado

IVR → Dynamic Routes pide CUIL → primer AGI consulta Atenciones → devuelve prestadora en CRM_ROUTE_KEY → Dynamic Routes aplica su mapa de destinos.
Al responder un miembro de la cola, QAGI ejecuta el segundo AGI, que despacha POST con llamada/interno. Atenciones identifica a la operadora por Mi interno.

TODO el mapa prestadora→cola/destino se configura en Dynamic Routes. Los AGI no contienen mapas ni eligen colas o contextos.
Las reglas sugeridas del documento del servidor por opción/titularidad/actividad/referencias/provincia no forman parte de esta entrega.

## Configuración nativa prevista

- Un único Dynamic Routes puede ser destino de las opciones1/2 del IVR y compartir un mapa.
- Get DTMF input: activado; Announcement: audio para CUIL.
- Source type: AGI.
- Script and parameters: crm_get_afiliado.agi.php,${IVR_DIGIT_PRESSED}; verificar variable del IVR instalado. La opción es obligatoria para estadísticas de API.
- El AGI lee CUIL de dtmfinput, sin pasarlo en argv ni conservarlo para la atención.
- AGI Result Variable: CRM_ROUTE_KEY.
- Match igual al nombre EXACTO de prestadora devuelto por testing → destino elegido en el selector nativo.
- Default: cola Call Center acordada. Prestadora ausente/desconocida, CUIL inválido o fallo de API usan ese destino.
- La opción3 omite GET y conserva su destino PBX directo si se utiliza.

## Contrato real

[ATENCIONES-CONTRACT.md](ATENCIONES-CONTRACT.md) contiene request/response, correlación y límites.
GET /Atenciones/api/central/preatendedor: opcion/cuil/llamada, X-Api-Key, total3s. El adaptador lee únicamente cuilValido/prestadora para producir el resultado.
POST /Atenciones/api/central/llamada-atendida: application/x-www-form-urlencoded, llamada/interno, X-Api-Key; fuera del camino síncrono y sin alterar llamada por fallos.
El mismo UNIQUEID ORIGINAL del llamante (máximo40) se conserva en ambos y en reintentos; no id de agente/Local.
Se elimina el map interno→usuarioCRM. No transmitir afiliado_id, CUIL ni referencias en el aviso.

## Rutas previstas

Scripts existentes: /var/lib/asterisk/agi-bin/crm_get_afiliado.agi.php y crm_set_atencion.agi.php.
Auxiliares: /var/lib/asterisk/agi-bin/afiliados-crm/. Config externa: /etc/asterisk/afiliados-crm.conf (root:asterisk0640), código root:asterisk0750.
PHP5.4+ CLI/cURL/JSON; sin addon, Composer ni listener AMI.
Cola6000: Local/<interno>@from-queue/n y QAGI confirmados; setinterfacevar=yes en [6000](+) de queues_post_custom.conf después de verificar includes. Preservar hooks ajenos, sin editar generado.

## Estado y continuidad

[Spec45](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/45) y [ticket46](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/46), mismo PR47.
Los seis archivos de implementación siguen usando el prototipo de octubre. Faltan su adaptación, tests públicos y guía final de instalación/prueba. #48 sigue needs-info por no-changes sin diagnóstico; no se relanzó.
Esta documentación no acredita compatibilidad, aceptación, merge ni instalación.
