# Contrato provisional del CRM

Este contrato sirve para desarrollar sin acceso al proveedor. Adaptar `issabel_crm/flow.py` y `http_worker.py` al contrato real cuando exista; mantener la misma decisión de negocio y sus pruebas externas. El simulador usa identificadores ficticios, no representa una integración validada con un CRM comercial.

## Consulta

`GET /affiliates?cuil=20123456786`, con `Accept: application/json` y opcionalmente `Authorization: Bearer <lookup_token>`.

```json
{"affiliate_id":"af-demo-1","obra_social":"OS_A"}
```

- `200`: objeto con identificador estable y una obra inequívoca. Ambos son strings de 1–128 caracteres (`A–Z`, `a–z`, `0–9`, `_ . : @ -`). Adaptar esta restricción si el proveedor tiene identificadores distintos.
- `404`: afiliado no encontrado.
- `obra_social` como lista: cobertura ambigua; no seleccionar arbitrariamente una obra.
- Error HTTP, transporte, timeout, JSON inválido o respuesta superior a 64 KiB: resultado técnico separado y atención general.
- Obra sin mapa: resultado `unmapped_obra`, atención general. Si el afiliado está reconocido, su ID se conserva y el operador general puede recibir la ficha; lo mismo sucede con obras ambiguas válidas. Fallas técnicas o identidad inválida no conservan un afiliado anterior.
- El CRM nunca devuelve un contexto, una cola ni un número para ejecutar: sólo un código resuelto contra destinos aprobados localmente.
- El presupuesto `lookup_timeout` abarca arranque del trabajador, DNS, conexión, TLS, recepción y parseo. Un supervisor mata y recoge el proceso al vencer el presupuesto. No se siguen redirects ni proxies del entorno.

## Aviso de atención

`POST /answered`, JSON, opcionalmente `Authorization: Bearer <notify_token>` y `Idempotency-Key: <event_id>`.

```json
{
  "schema_version": 1,
  "event_type": "queue_member_answered",
  "interaction_id": "14d7d5ca-f3c3-4a97-b5d5-6dfc9a3cf8c8",
  "event_id": "9c23eaf0-763b-4555-88e1-cd84413f1e08",
  "pbx_id": "pbx-lab",
  "uniqueid": "1700000000.1",
  "linkedid": "1700000000.1",
  "affiliate_id": "af-demo-1",
  "crm_user_id": "crm-user-a",
  "member_interface": "PJSIP/1001",
  "member_name": "Operador A",
  "extension": "1001",
  "queue": "601",
  "answered_at": "2026-10-08T01:00:00+00:00"
}
```

`extension` sólo se incluye cuando figura explícitamente en el mapa comprobado. No se deriva de `Local`, `Agent`, nombres ni dispositivos desviados. La clave del mapa es `MEMBERINTERFACE`, nunca una regex universal. Una huella por interacción detecta cambios del mapa durante la espera; se omite el aviso dudoso, en vez de dirigirlo a un usuario reasignado.

Una invocación del hook crea un nuevo `event_id`; una nueva atención también. Un reintento externo de un mismo payload debería conservar su `event_id`, pero este addon no implementa reintentos. El receptor debe tolerar duplicados. El payload omite CUIL y no depende de una sesión ni de una llamada previa al adaptador.

El hook corre sobre el llamante después de responder el miembro y antes del bridge. Representa respuesta, no una confirmación de audio. No se instala un hook pre-dial ni un listener AMI.

El AGI lanza un proceso con stdout/stderr hacia `/dev/null`, sin heredar sus pipes, y le entrega el payload por un write no bloqueante de tamaño acotado. El emisor hace un solo intento supervisado por `notify_timeout`, registra resultado en syslog y termina. Locks de slots vacíos limitan la concurrencia entre procesos; no contienen payloads ni forman una outbox. Saturación, ausencia de mapa, config inválida y fallo local omiten el aviso conservando la llamada. El límite de trabajo local no es una garantía de latencia de tiempo real bajo cualquier carga del sistema; medirlo en la PBX antes del piloto.

El CRM es responsable de presentar la ficha en el usuario receptor. Un `2xx` demuestra recepción HTTP, no apertura de pantalla. El dashboard del simulador permite observar esa asociación de forma ficticia.

## Credenciales y registro

Activar `secrets_file` en `issabel_crm.conf` y editar `/etc/asterisk/issabel_crm_secrets.conf` (`root:asterisk`, `0640`). Tokens separados para GET y POST, sin credenciales en URL ni en argumentos de procesos. No versionar el archivo real.

Los diagnósticos del addon contienen componente, resultado, identificador de interacción y destino aprobado de consulta; no incluyen CUIL, tokens, cuerpos del CRM ni excepciones originales. AGI debug de Asterisk, captura de red o access logs del CRM pueden mostrar datos: usar sólo fixtures en el laboratorio y acordar la retención operativa al desplegar.
