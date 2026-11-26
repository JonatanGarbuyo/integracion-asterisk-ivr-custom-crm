# Mecanismos de Asterisk para IVR y CRM

Investigación documental iniciada el 2026-10-07. El inventario recibido el 2026-10-08 confirma Issabel 4/Asterisk 11.25.3; el dialplan efectivo sigue pendiente. Esto resuelve mecanismos generales, no compatibilidad instalada ni autorización para desplegar.

## Observaciones documentadas

### Consulta antes de enrutar

AGI ejecuta un proceso local que intercambia comandos por stdin/stdout y puede leer DTMF/controlar el canal. FastAGI conecta a un servidor por TCP mediante `agi://host[:port]/recurso`. No equivale a HTTP: el programa/servicio implementa la consulta HTTP al CRM. `AGISTATUS` refleja ejecución de AGI (`SUCCESS`, `FAILURE`, `NOTFOUND`, `HANGUP`), no que se haya encontrado un afiliado; el resultado de negocio debe transmitirse aparte. [S1]

### Momento de aviso y canal

| Mecanismo | Momento y alcance documentados | Implicación para esta integración |
|---|---|---|
| AGI del IVR | Ejecuta lógica sobre el canal antes de continuar el dialplan. [S1] | Adecuado para obtener obra social y devolver una decisión de ruta. |
| Parámetro `AGI` de `Queue()` | Script en el canal del llamante cuando se conecta a un miembro. [S2] | Es un hook diferente del AGI inicial; no ejecuta sobre el interno. |
| Parámetro `gosub` de `Queue()` | La guía específica lo define después de que responde el miembro, antes de unir las partes, sobre el canal del miembro; termina con `Return()`. [S3] | Puede preparar el aviso, pero no certifica por sí solo una conversación ya establecida. |
| AMI `AgentCalled` | Se emite al notificar/ofrecer la llamada a un miembro. [S4] | No usar para afirmar quién atendió; puede haber ofertas sin respuesta o simultáneas. |
| AMI `AgentConnect` | Se emite cuando el miembro respondió y se conecta mediante bridge al llamante de la cola. [S5] | Candidato principal para registrar la atención y disparar la ficha. |

La descripción breve de Queue usa «connected» para gosub; la guía de pre-bridge precisa la secuencia. No equiparar un hook post-answer con confirmación del bridge. Las opciones `b`/`B` de Queue son **pre-dial**, por lo que tampoco identifican una atención efectiva. [S2, S3]

### Versiones y sintaxis

Queue 20 conserva posiciones `AGI,macro,gosub,rule,position`; Queue 21 tiene `AGI,gosub,rule,position`. La documentación 23 advierte expresamente que la eliminación de Macro en 21 cambió el orden de argumentos. No copiar ejemplos con comas entre versiones. [S2, S6, S7]

El esquema consultado de `AgentConnect`/`AgentCalled` declara `Since: 12.0.0`; AMI v2 empieza en Asterisk 12. Esto no demuestra ausencia de eventos históricos: no extrapolar nombres/campos modernos a instalaciones anteriores. [S4, S5, S8]

### Correlación e interno

AgentConnect expone `Uniqueid`, `Linkedid`, `DestUniqueid`, `DestLinkedid`, `Queue`, `MemberName`, `Interface` y `DestChannel`. `Interface` es la tecnología/localización del miembro, `MemberName` su nombre; `Linkedid` y `DestLinkedid` señalan el Uniqueid del canal más antiguo asociado a cada lado. Ninguno identifica al afiliado o al usuario del CRM automáticamente. [S5]

Los canales Local tienen dos mitades y pueden desaparecer por optimización; AMI describe `LocalBridge`, eventos de optimización y cambios de bridge. [S8] La optimización puede destruir variables del canal Local; `/n` la desactiva. [S9] Las variables con `__` se heredan a descendientes; `_` sólo a una generación. [S10]

### Entrega de eventos

AMI es un bus asíncrono que envía eventos a clientes conectados; permisos/filtros condicionan recepción. No se documenta aquí un contrato de ACK, cursor persistente y reproducción tras desconexión: **inferencia de diseño**, no tratarlo como una cola durable. [S8]

`queue_log` registra llamadas de cola y contiene `CONNECT(holdtime|bridgedchanneluniqueid|ringtime)` más identificador de llamante, cola y miembro. Puede servir para reconciliar eventos perdidos si está habilitado y conservado. No es por sí mismo una API de pantalla del CRM. [S11]

## Recomendaciones candidatas; aún no decisiones finales

- AGI local pequeño o FastAGI para consulta con timeout total, resultados de negocio explícitos y ruta de contingencia. FastAGI cambia dónde vive el servicio, no elimina la espera necesaria para elegir ruta.
- Guardar un `interaction_id` opaco asociado a identificador PBX, Uniqueid/Linkedid del ingreso y afiliado. Propagarlo mediante `__` cuando haga falta; conservar también la asociación en el adaptador. No usar DNI ni CallerID como clave de llamada.
- Avisar desde consumidor AMI ante AgentConnect. Mapear Interface/MemberName a interno y usuario CRM mediante configuración comprobada; con Local, desvíos o follow-me, resolver además el endpoint realmente conectado. No extraer el interno con una regex universal de DestChannel.
- Persistir cada evento recibido antes del POST al CRM, reintentar y deduplicar por atención —incluyendo miembro/leg—. Un outbox protege lo recibido, no recupera eventos ocurridos mientras AMI estaba desconectado. Si se exige recuperación, evaluar queue_log y/o captura durable local; no enviar fichas tardías de llamadas terminadas.
- Un gosub breve que entregue trabajo a un servicio local es alternativa si la integración de Issabel lo permite. Evitar esperar una llamada HTTP larga antes del bridge; un `UserEvent` enviado a AMI conserva la dependencia de conexión y no aporta durabilidad por sí solo.

## Evidencia pendiente en ticket 02

Versión exacta, módulos/hook disponibles, dialplan generado y puntos persistentes de extensión en Issabel; miembros reales (SIP/PJSIP/Local), desvíos y transferencias; permisos AMI; trazas anonimizadas del evento y sus lados; queue_log y rotación. Nada de esto se comprobó en producción.

## Fuentes primarias

- [S1 — AGI, Asterisk 20](https://docs.asterisk.org/Asterisk_20_Documentation/API_Documentation/Dialplan_Applications/AGI/)
- [S2 — Queue, Asterisk 20](https://docs.asterisk.org/Asterisk_20_Documentation/API_Documentation/Dialplan_Applications/Queue/)
- [S3 — Pre-Bridge Handlers](https://docs.asterisk.org/Configuration/Dialplan/Subroutines/Pre-Bridge-Handlers/)
- [S4 — AgentCalled, Asterisk 20](https://docs.asterisk.org/Asterisk_20_Documentation/API_Documentation/AMI_Events/AgentCalled/)
- [S5 — AgentConnect, Asterisk 20](https://docs.asterisk.org/Asterisk_20_Documentation/API_Documentation/AMI_Events/AgentConnect/)
- [S6 — Queue, Asterisk 21](https://docs.asterisk.org/Asterisk_21_Documentation/API_Documentation/Dialplan_Applications/Queue/)
- [S7 — Queue, Asterisk 23: aviso de cambio de orden](https://docs.asterisk.org/Asterisk_23_Documentation/API_Documentation/Dialplan_Applications/Queue/)
- [S8 — AMI v2 Specification](https://docs.asterisk.org/Configuration/Interfaces/Asterisk-Manager-Interface-AMI/AMI-v2-Specification/)
- [S9 — Local Channel Optimization](https://docs.asterisk.org/Configuration/Channel-Drivers/Local-Channel/Local-Channel-Optimization/)
- [S10 — Variable Inheritance](https://docs.asterisk.org/Configuration/Dialplan/Variables/Channel-Variables/Variable-Inheritance/)
- [S11 — Queue Logs](https://docs.asterisk.org/Operation/Logging/Queue-Logs/)

## Ampliación: soporte objetivo Asterisk 16/18 e integración Issabel

Antecedente basado en las versiones inicialmente estimadas. Asterisk 16 queda como investigación histórica; la matriz actual exige 11.25.3 y 18.

Se leyeron las ramas oficiales `16` y `18` mediante el lector GitHub. `app_queue.c` de ambas prepara `MEMBERINTERFACE`/`MEMBERNAME` cuando `setinterfacevar` está activo, ejecuta el gosub sobre el miembro y el AGI sobre `qe->chan` (llamante), antes del bridge. Por tanto un AGI de Queue es viable sin consumidor AMI; conviene que el aviso remoto no prolongue esa fase. Se verificaron además los parámetros `membergosub` en ambos ejemplos `queues.conf.sample`.

Se leyó `queues/functions.inc/dialplan.php` del repositorio oficial IssabelPBX: genera `QAGI` desde `VQ_AGI`, `QGOSUB` desde `VQ_GOSUB` y los pasa a `ext_queue`. Es evidencia del código público actual, no verificación de los paquetes instalados en Issabel 4 ni en la imagen Issabel 5 mencionada.

Fuentes adicionales:

- https://github.com/asterisk/asterisk/blob/16/apps/app_queue.c
- https://github.com/asterisk/asterisk/blob/18/apps/app_queue.c
- https://github.com/asterisk/asterisk/blob/16/configs/samples/queues.conf.sample
- https://github.com/asterisk/asterisk/blob/18/configs/samples/queues.conf.sample
- https://github.com/IssabelFoundation/issabelPBX/blob/master/queues/functions.inc/dialplan.php

## Inventario real y primera entrega genérica (2026-10-08)

El cliente informó Issabel 4.0.0-1, CentOS 7.9, Asterisk 11.25.3, IssabelPBX 2.11.0-48, issabel-framework 4.0.0-10 y issabel-callcenter 4.0.0-5. El inventario completo está en #4. PHP, Python, dialplan generado, miembros de cola y permisos siguen por verificar.

Se leyó `apps/app_queue.c` del tag exacto **11.25.3**: antes del bridge ejecuta `pbx_exec(qe->chan, application, agiexec)` para la aplicación AGI si se configuró el argumento correspondiente. Por tanto el mecanismo de Queue AGI existe también en esta versión. La primera entrega no instala el hook de cola: #23 deberá verificar variables de miembro, coexistencia con hooks y generación efectiva en los paquetes del cliente.

También se leyó la fuente de IssabelPBX de 2017 (`5d3ea9073d78aa2476fddf4b267faa8839417e4c`) para comprobar la API legacy `customappsreg_customdests_get/add/delete/edit`, `needreload()` y el generador `$ext->add`. El addon usa ese registro de destinos y su propio callback `_get_config`; no modifica `extensions_additional.conf`. La fuente histórica respalda el diseño de API, pero no identifica por sí sola el contenido exacto del RPM 2.11.0-48.

Fuentes primarias:

- https://github.com/asterisk/asterisk/blob/11.25.3/apps/app_queue.c#L5979-L5989
- https://github.com/IssabelFoundation/issabelPBX/blob/5d3ea9073d78aa2476fddf4b267faa8839417e4c/customappsreg/functions.inc.php
- https://github.com/IssabelFoundation/issabelPBX/blob/5d3ea9073d78aa2476fddf4b267faa8839417e4c/framework/amp_conf/htdocs/admin/libraries/extensions.class.php
- https://github.com/IssabelFoundation/issabelPBX/blob/master/miscapps/functions.inc.php
