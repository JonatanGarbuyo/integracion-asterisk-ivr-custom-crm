# Contrato Atenciones y decisiones

Fuente: `central.md` entregado por el desarrollador de Atenciones el 19/11/2026 y aclaración posterior del usuario: **evaluar las reglas devuelve un valor; Dynamic Routes ejecuta el destino**. Sustituye el prototipo getAfiliadoByCuil/setAtencion y la interpretación anterior de devolver únicamente prestadora.

## Transporte

Base por ambiente: `https://<servidor>/Atenciones`; conservar `/Atenciones`. Ambos endpoints usan `X-Api-Key`. Claves y URL reales se configuran fuera de Git. TLS y hostname verificados, sin redirects; CA privada opcional. HTTP sólo se permite explícitamente para loopback del mock. Conexión máxima 1 segundo y presupuesto HTTP total 3 segundos; cuerpo máximo 16 KiB.

## GET /api/central/preatendedor

Query: `opcion` (1/2), `cuil` (opcional), `llamada` (UNIQUEID original, máximo 40 caracteres). El AGI elimina espacios y guiones del CUIL, pero consulta incluso si está vacío o es inválido: checksum y registro pertenecen al servidor. La opción 3 se configura directamente en el IVR y no consulta.

Respuesta HTTP 200 con todos los campos:

```json
{
  "cuilValido": true,
  "esTitular": true,
  "activo": true,
  "prestadora": "Prestadora de prueba",
  "provincia": "Provincia ficticia",
  "referencias": [],
  "esProveedor": false
}
```

`cuilValido`, `esTitular`, `activo`, `esProveedor`: booleanos. `prestadora`, `provincia`: string o null. `referencias`: lista de strings. No se exige nombre ni id del afiliado. Referencias se usa transitoriamente para resolver si la lista está vacía; sus valores no se exportan.

## Reglas → CRM_ROUTE_KEY

Evaluación en el orden de cada opción:

| Opción | Condición | Decisión lógica |
|---|---|---|
| 1 | CUIL inválido | `INVALID_CUIL` |
| 1 | Proveedor | `END_CALL` |
| 1 | Titular activo | `END_CALL` |
| 1 | Resto | `CALL_CENTER` |
| 2 | CUIL inválido | `INVALID_CUIL` |
| 2 | No es titular activo | `END_CALL` |
| 2 | Referencias no vacías | `PORTAL` |
| 2 | Referencias vacías | `CALL_CENTER` |
| 1/2 | Error de red, timeout, HTTP distinto de 200, JSON/schema inválido | `CALL_CENTER` |

La opción 2 rechaza a un titular dado de baja; el usuario lo confirmó. No añade un filtro por proveedor. Un error técnico nunca se transforma en CUIL inválido. La opción 3 devuelve defensivamente `OPTION_3` sin HTTP; se configura su anuncio y corte directamente en el IVR.

Para producir la única variable de selección `CRM_ROUTE_KEY`:

1. Si la decisión lógica es `INVALID_CUIL`, `END_CALL` o `PORTAL`, devolver esa clave. Tiene prioridad sobre la prestadora.
2. Si la decisión lógica permite atención (`CALL_CENTER`) y hay prestadora no vacía, devolver su nombre literal: por ejemplo `Osde`. Sin prefijo, aliases ni cambios de mayúsculas, espacios o acentos.
3. Si corresponde atender pero no hay prestadora, o falla la consulta, devolver `CALL_CENTER`.

Dynamic Routes mapea `Osde` a la cola de Osde, otros nombres a sus colas, y las claves especiales a anuncios/corte o cola general. Default es cola general para nombres no configurados. El AGI no contiene el mapa ni ejecuta destinos.

`CRM_PRESTADORA` sigue disponible como dato auxiliar literal, o vacío ante CUIL inválido, null o fallo; no es el selector principal porque omitiría las reglas. El IVR tiene dos Dynamic Routes con `crm_get_afiliado.agi.php,1` y `crm_get_afiliado.agi.php,2`, respectivamente. Ambos seleccionan `CRM_ROUTE_KEY` y reutilizan el mismo script.

## POST /api/central/llamada-atendida

Formulario `application/x-www-form-urlencoded`: sólo `llamada` e `interno` URL-encoded. Misma cabecera `X-Api-Key`. `interno` es string de 1–10 dígitos; Atenciones resuelve la operadora mediante “Mi interno”. No se necesita mapa agente/usuario CRM.

HTTP 200 devuelve `{"resultado":"OK"}`, `SIN_VALIDACION` o `SIN_OPERADOR`. Todos continúan igual; HTTP/red/JSON fallidos tampoco cambian la llamada. El segundo AGI se invoca a sí mismo con --send fuera de la llamada, sin archivo worker separado, reintentos ni entrega garantizada. Job privado sólo con llamada/interno, consumido antes del POST. El AGI no espera la respuesta remota.

## Correlación y cola

`CRM_CALL_ID` se captura una vez desde el UNIQUEID del llamante y se hereda mediante `__CRM_CALL_ID`. Se reutiliza en reintentos y canales Local. Nunca se trunca; el hook no toma como reemplazo el UNIQUEID del agente. Si se entra por un canal Local previo a la consulta, el dialplan de entrada debe preservar ese UNIQUEID original antes de crear la nueva pierna.

Se prepara `__QAGI=crm_set_atencion.agi.php` antes de consultar, incluso para la cola de contingencia si GET falla. Hooks QAGI/VQ_AGI ajenos se preservan y se señala `CRM_QAGI_CONFLICT=1`; resolver la composición antes de activar.

Instalación verificada por el usuario: Asterisk 11.25.3, IssabelPBX 2.11.0-48, miembros dinámicos `Local/<interno>@from-queue/n`, sin agentes clásicos. El dialplan pasa QAGI al sexto argumento de Queue. Con `setinterfacevar=yes`, el hook usa `MEMBERINTERFACE` para extraer ese interno. También se aceptan interfaces numéricas SIP/PJSIP; no nombres de canal arbitrarios ni Agent antiguos.

## Privacidad y aceptación

No exportar CUIL, provincia, referencias o JSON remoto a jobs, CDR o diagnósticos. El CUIL de captura se limpia; las únicas salidas de consulta son decisión, prestadora y metadatos técnicos de correlación/hook. Diagnósticos de categorías fijas; sin URL completa, clave ni cuerpo remoto. Trazas AGI/DTMF de Asterisk pueden mostrar la entrada: usar datos ficticios al depurar.

Pruebas automáticas: procesos PHP reales por stdin/stdout AGI y servidor HTTP local; reglas, contrato, errores, timeout, correlación, interfaces, POST asíncrono y ausencia de comandos de control de llamadas. No acreditan instalación PBX ni integración real.

Pendiente de laboratorio: URL/clave de testing, certificado/IP de salida habilitada, audio/URL del Portal, destinos nativos acordados, CUIL ficticios del proveedor, ejecutar menú aislado y confirmar pantalla de la operadora. No se promueve producción.

## Instalación mínima

Sólo dos archivos PHP en agi-bin: crm_get_afiliado.agi.php y crm_set_atencion.agi.php, más /etc/asterisk/afiliados-crm.conf con URL/clave. Ambos son autocontenidos. El modo de envío en segundo plano pertenece al segundo AGI y no lee stdin AGI. No common.php, crm_worker.php, paquete de instalación ni servicio permanente. Mock y pruebas quedan bajo tests/, fuera de la instalación.
