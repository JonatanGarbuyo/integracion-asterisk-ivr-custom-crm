# Handler JSON v1

El núcleo ejecuta un proceso local por entrada al perfil. Entrega un objeto JSON UTF-8 por stdin, cierra stdin y espera un objeto por stdout. stderr no entra al protocolo ni al registro de llamada. El handler no recibe comandos AGI. No hay shell, sesión persistente ni base de llamadas.

```json
{
  "contract_version": 1,
  "event": "ivr_entry",
  "profile_identifier": "welcome",
  "configuration_version": "sha256-del-archivo-conf",
  "call": {"unique_id": "1700000000.1", "channel_name": "SIP/caller-0001"},
  "input": {"source": "callerid", "value": "555123"},
  "context": {},
  "handler_settings": {"greeting": "Buen día", "style": "normal", "api_token": ""}
}
```

`configuration_version` identifica los bytes del .conf capturados al comenzar el AGI. El proceso recibe una copia de sus settings, aunque se guarde otra configuración mientras se ejecuta. `input.source` admite `none`, `dtmf`, `callerid`, `channel`. `input.value` puede estar vacío; las validaciones comerciales pertenecen al handler. `unique_id` proviene de Asterisk y no contiene identificación del usuario del CRM.

```json
{"contract_version":1,"action":"continue","context_patch":{"greeting":"Buen día","input_value":"555123"}}
```

`continue` elige `next_destination` del perfil; no admite `destination`. `route` requiere un `destination` idéntico a uno de los destinos aprobados del perfil (en esta entrega: siguiente o contingencia). El handler no puede introducir expresiones de dialplan, destinos arbitrarios ni cambios de cola. La salida admite únicamente `contract_version`, `action`, `context_patch` y, para route, `destination`. La versión es un entero 1; el contexto es un objeto JSON, sin NaN/Infinity. Máximo de salida: 16 KiB. Una versión, acción, contexto o destino inválidos producen contingencia.

El presupuesto `execution_budget_ms` abarca la espera del proceso, entre 50 y 5000 ms. El núcleo termina y recoge el grupo del proceso al finalizar o agotar el plazo. Las dependencias remotas de un handler deben respetar ese presupuesto. Esto no es un aislamiento para ejecutar código no confiable. El handler tiene los permisos del servicio PBX.

El núcleo coloca en el canal:

| Variable | Propósito |
|---|---|
| `__CALLFLOW_PROFILE_IDENTIFIER` | Perfil que marcó la llamada; heredable. |
| `__CALLFLOW_CONFIGURATION_VERSION` | Snapshot de configuración de esa ejecución; heredable. |
| `__CALLFLOW_CONTEXT_JSON` | Contexto devuelto por la extensión; heredable. |
| `CALLFLOW_NEXT_DESTINATION` | Destino que ejecuta el wrapper del perfil. |
| `CALLFLOW_HANDLER_STATUS` | `completed`, `fallback`, `disabled` o `configuration_error`. |

Los dos guiones bajos son la convención de herencia de Asterisk. No se guardan credenciales en variables ni en registros del núcleo. Los handlers deben excluir secretos del contexto que devuelven. La contingencia queda establecida en el wrapper antes del AGI, incluso si falta el intérprete. Deshabilitar un perfil mantiene su destino y dirige las llamadas a la contingencia configurada.

Esta versión implementa entrada desde IVR. El contrato de evento de respuesta de cola y los adaptadores comerciales corresponden a sus tickets posteriores; no se anuncian como implementados.
