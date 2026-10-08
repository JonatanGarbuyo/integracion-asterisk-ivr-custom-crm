# Nombres de CallFlow Hooks

**CallFlow Hooks** es el nombre elegido para la feature. **Afiliados CRM** es el perfil implementado: identificar por CUIL, resolver un destino y notificar al CRM cuando responde un miembro de cola.

El nombre permite sumar otros casos de uso. Esta entrega conserva dos puntos de entrada concretos; todavía no implementa un registro de handlers ni una API de plugins genéricos. Un futuro hook de IVR puede reutilizar la infraestructura sin convertir los conceptos de afiliado y obra social en conceptos universales.

## Variables del canal

Las variables propias siguen `CALLFLOW_<ÁMBITO>_<SIGNIFICADO>`. Los ámbitos distinguen la interacción, la PBX, la identidad de Asterisk, el afiliado, los datos del CRM, el enrutamiento y la cola. Los nombres completos se usan tanto en el dialplan como en los AGI.

| Variable | Representa |
|---|---|
| `CALLFLOW_CALL_INTERACTION_ID` | UUID generado al entrar al perfil; correlaciona la consulta y los avisos de esa interacción. |
| `CALLFLOW_PBX_INSTANCE_ID` | Identificador configurado de la instancia PBX de origen. |
| `CALLFLOW_ASTERISK_CHANNEL_UNIQUEID` | Uniqueid del canal que ingresó al AGI de identificación. |
| `CALLFLOW_ASTERISK_LINKEDID` | Linkedid leído al ingresar al perfil; correlación aportada por Asterisk. |
| `CALLFLOW_AFFILIATE_CUIL` | CUIL ingresado y validado para la consulta. |
| `CALLFLOW_CRM_AFFILIATE_ID` | Identificador estable del afiliado devuelto por el CRM. |
| `CALLFLOW_CRM_OBRA_SOCIAL_CODE` | Código de obra social reconocido y con destino configurado. Vacío si no se resolvió una cobertura única con mapa. |
| `CALLFLOW_ROUTING_STATUS` | Resultado de la identificación/enrutamiento; por ejemplo `found`, `invalid_cuil` o `unmapped_obra`. |
| `CALLFLOW_ROUTING_DESTINATION_TYPE` | Tipo del destino aprobado: `queue` o `external`. |
| `CALLFLOW_ROUTING_DESTINATION_NUMBER` | Número de cola o 0800 seleccionado. |
| `CALLFLOW_QUEUE_NAME` | Nombre de la cola a la que se entregó la llamada; en este perfil coincide con su número. |
| `CALLFLOW_QUEUE_MEMBER_CRM_MAP_HASH` | SHA-256 del mapa miembro → usuario CRM leído al identificar; detecta cambios antes de notificar. |
| `CALLFLOW_QUEUE_PREVIOUS_ANSWER_AGI` | AGI previo de respuesta de cola que se debe encadenar. |

El prefijo `__` de `Set(__CALLFLOW_...)` expresa herencia del canal en Asterisk; no forma parte del nombre lógico leído por el AGI. Los identificadores, datos del afiliado, hash del mapa y contexto de cola se escriben con herencia. El resultado y destino de enrutamiento se consumen en el canal llamante. Ninguno es una variable global de datos por llamada.

`MEMBERINTERFACE`, `MEMBERNAME`, `VQ_AGI`, `QAGI`, `DIALSTATUS` y `CHANNEL(linkedid)` conservan sus nombres: pertenecen a Asterisk/Issabel. El mapa de operadores se consulta con el valor exacto de `MEMBERINTERFACE`; no se supone que ese valor sea un interno físico.

El aviso HTTP genera un `event_id` nuevo para cada respuesta de miembro. No existe una variable persistente de canal para ese identificador: el emisor recibe un payload autosuficiente.

## Migración de nombres

| Nombre anterior | Nombre actual |
|---|---|
| `CRM_INTERACTION_ID` | `CALLFLOW_CALL_INTERACTION_ID` |
| `CRM_PBX_ID` | `CALLFLOW_PBX_INSTANCE_ID` |
| `CRM_UNIQUEID` | `CALLFLOW_ASTERISK_CHANNEL_UNIQUEID` |
| `CRM_LINKEDID` | `CALLFLOW_ASTERISK_LINKEDID` |
| `CRM_CUIL` | `CALLFLOW_AFFILIATE_CUIL` |
| `CRM_AFFILIATE_ID` | `CALLFLOW_CRM_AFFILIATE_ID` |
| `CRM_OBRA` | `CALLFLOW_CRM_OBRA_SOCIAL_CODE` |
| `CRM_RESULT` | `CALLFLOW_ROUTING_STATUS` |
| `CRM_DEST_TYPE` | `CALLFLOW_ROUTING_DESTINATION_TYPE` |
| `CRM_DEST` | `CALLFLOW_ROUTING_DESTINATION_NUMBER` |
| `CRM_QUEUE` | `CALLFLOW_QUEUE_NAME` |
| `CRM_AGENT_MAP_REV` | `CALLFLOW_QUEUE_MEMBER_CRM_MAP_HASH` |
| `CRM_PREVIOUS_QAGI` | `CALLFLOW_QUEUE_PREVIOUS_ANSWER_AGI` |

La versión 0.1.1 actualiza conjuntamente AGI y dialplan generado. No lee alias de las variables anteriores. Antes de actualizar una instalación de laboratorio 0.1.0, dejar finalizar las llamadas que ingresaron al perfil, instalar la nueva versión, ejecutar `tools/addon.py apply` y recargar el dialplan según la guía de laboratorio. Revisar cualquier dialplan custom propio que lea nombres anteriores.

## Código y configuración

Las funciones de entrada describen la acción: `route_affiliate_call` y `notify_crm_of_queue_member_answer`. Las variables locales distinguen `call_channel_variables`, `affiliate_record`, `crm_operator_mapping`, `destination_number` y `previous_queue_answer_agi`. El hash derivado de configuración se llama `queue_member_crm_map_hash`.

`CALLFLOW_HOOKS_CONFIG_FILE` permite indicar el archivo de configuración. La precedencia es ruta explícita al lector, esta variable, el alias anterior `ISSABEL_CRM_CONFIG` y finalmente `/etc/asterisk/issabel_crm.conf`.

En esta entrega permanecen estables el paquete técnico `issabel-crm`, el módulo Python `issabel_crm`, los nombres de AGI, el destino `issabel-crm-entry,s,1`, las rutas instaladas y las claves del `.conf`. No se requiere recrear el Custom Destination. El contrato HTTP conserva `affiliate_id`, `obra_social`, `interaction_id`, `event_id`, `crm_user_id` y el resto de campos documentados en [Contrato provisional del CRM](testing/contrato-crm.md).
