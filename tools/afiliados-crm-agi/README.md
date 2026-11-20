# Afiliados CRM con Dynamic Routes y AGI

Entrega standalone, independiente de CallFlow Hooks. Especificación canónica #45; implementación y pruebas #46.
Estado: guía de instalación preparada; scripts pendientes de entrega por OpenCode y aceptación. No instalar nombres de archivo que aún no estén publicados.

## Flujo y mapa
Ruta entrante → IVR → Dynamic Routes → cola o Misc Destination0800.
Las entradas de Dynamic Routes SON el map valor exacto → destino PBX. El AGI devuelve una clave de obra, nunca un contexto/dialplan entregado por CRM.
Al responder Queue ejecuta el segundo AGI; éste captura identidad y despacha un worker de un solo uso para POST setAtencion, sin esperar respuesta remota.

## Configuración Dynamic Routes
| Campo | Valor |
|---|---|
| Name | Afiliados CRM |
| Get DTMF input | habilitado |
| Timeout | 10 segundos, ajustable |
| Input Variable | afiliado_cuil |
| Announcement | grabación de System Recordings: pedir CUIL y finalizar con numeral |
| Source type | AGI |
| AGI script and parameters | crm_get_afiliado.agi.php,[INPUT] |
| AGI result variable | CRM_ROUTE_KEY |
| Result Variable | obra_social, opcional |
| Entradas | OSPACA → Queues/6001, OTRA_OBRA → otro destino |
| Default destination | cola general o IVR de asistencia, según elección del administrador |

Input Variable genera DYNROUTE_afiliado_cuil heredable. [INPUT] lleva el dato capturado al AGI. La captura de esta versión histórica no limita por sí sola a11 dígitos: el AGI valida la longitud; pedir # para finalizar.
Las claves CRM_INVALID_INPUT, CRM_NOT_FOUND y CRM_ERROR pueden tener entradas explícitas; si no coinciden van al Default destination.
Para0800 crear un Misc Destination con el número, enlazarlo aquí y comprobar troncal/ruta saliente. Las entradas pueden compartir destino. Guardar y aplicar cambios PBX.
No configurar un URL directo al CRM si devuelve JSON ni usar la fuente URL histórica que desactiva TLS.

## Rutas y permisos previstos
- /var/lib/asterisk/agi-bin/crm_get_afiliado.agi.php
- /var/lib/asterisk/agi-bin/crm_set_atencion.agi.php
- Auxiliares del worker en /var/lib/asterisk/agi-bin/afiliados-crm/
- Config /etc/asterisk/afiliados-crm.conf, root:asterisk0640
- Scripts/auxiliares root:asterisk0750, no modificables por web/asterisk.
- Jobs temporales /var/spool/asterisk/afiliados-crm, asterisk:asterisk0700, cada job0600.
- PHP5.4+ CLI con cURL y JSON; sin Composer ni Python de runtime.
Comprobar AGI Scripts directory con core show settings. Las instrucciones de copia completas se incorporan con la entrega de #46.

## Hook de atención en Issabel4/Asterisk11
Lookup prepara QAGI en la misma llamada para el segundo AGI. Si hay QAGI/VQ_AGI ajeno no se debe sobreescribir: resolver el conflicto antes de activar integración.
El generador de Queue2.11 consultado pasa QAGI a Queue(), pero debe comprobarse en el dialplan instalado del cliente.
MEMBERINTERFACE y MEMBERNAME requieren setinterfacevar=yes. El queues.conf del repositorio2.11 incluye en este orden: queues_custom.conf, queues_additional.conf, queues_post_custom.conf.
Por eso la ampliación por cola debe ir en **queues_post_custom.conf**, después de la categoría generada, NO en queues_additional.conf y no en queues_custom.conf si la cola aún no existe.

Ejemplo para cola6001, después de verificar ese include:
```ini
[6001](+)
setinterfacevar=yes
```
Aplicar cambios PBX y confirmar que el comportamiento persiste al regenerar.
QAGI es un hook post-answer/pre-bridge sobre el canal del llamante; no es prueba de bridge consumado. No se ejecuta por cada ring y no requiere escuchar AMI.
Agent/9000 identifica al agente; AGENT(9000:fullchannel) da su canal de login en chan_agent11. Ese canal y las asociaciones configuradas permiten obtener el interno real. No enviar9000 como interno ni mapearlo estáticamente a un teléfono si los agentes cambian de puesto. SIP y Local requieren asociaciones verificadas; ante identidad no resuelta no enviar aviso atribuido a otra persona.

## Contrato CRM pendiente
Pedir URL y autenticación de ambos endpoints, parámetros de GET, JSON éxito/no encontrado/errores, campos exactos de POST, respuesta y comportamiento ante duplicados. Usar datos ficticios en ejemplos.
getAfiliadoByCuil debe devolver identificador estable del afiliado y código estable de obra. setAtencion debe admitir afiliado, agenteCRM, interno real y correlación de llamada/evento para que el CRM presente la ficha al usuario correcto.
El CRM se comunica por requests independientes, sin sesión de llamada. Un HTTP timeout puede ocurrir después de que CRM haya procesado el aviso; la idempotencia debe acordarse aunque el MVP no reintente.
Confirmar qué significa agente (id Call Center o id usuarioCRM), si se avisa nuevamente tras transferencias y qué hacer con afiliados no encontrados.

## Preflight de laboratorio
```sh
/usr/bin/php --version
/usr/bin/php -m
asterisk -rx 'core show settings'
asterisk -rx 'queue show 6001'
asterisk -rx 'dialplan show 6001@ext-queues'
asterisk -rx 'core show function AGENT'
```
Usar números de cola reales. Verificar cURL/JSON y QAGI. La función AGENT aplica si existen miembros Agent/ y está cargado chan_agent.
Primero mock, luego VM, luego endpoints reales de prueba. Ninguna validación mock acredita instalación de cliente.

## Fuentes primarias
- https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/dynroute/functions.inc.php
- https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/queues/functions.inc/dialplan.php
- https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/framework/amp_conf/astetc/queues.conf
- https://github.com/asterisk/asterisk/blob/11.25.3/apps/app_queue.c
- https://github.com/asterisk/asterisk/blob/11.25.3/channels/chan_agent.c
