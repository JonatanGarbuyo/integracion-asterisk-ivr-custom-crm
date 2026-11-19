# Atenciones: contrato de integración con la central

Fuente: documento central.md entregado por el desarrollador de Atenciones y compartido por el usuario el 19/11/2026. Especificación canónica del proyecto: issue45. Sustituye el contrato provisional getAfiliadoByCuil/setAtencion de octubre. Este documento no declara implementados los cambios en los AGI del PR47.

## Conexión
Base por ambiente: https://<servidor>/Atenciones. Conservar el prefijo /Atenciones al construir las rutas.
Ambos endpoints requieren header X-Api-Key. URL y clave de testing/producción se suministran por canal aparte y son distintas.
HTTPS con verificación de certificado y hostname; no desactivar TLS. Producción habilita la IP de origen de la central, que debe confirmarse según la IP de salida/NAT/VPN observada por Atenciones.

## Identificador de llamada
llamada es el UNIQUEID ORIGINAL del canal del llamante que ingresó por la línea, longitud máxima40. Capturarlo una vez, heredarlo y reutilizarlo en GET, reintentos de CUIL y POST. Nunca reemplazarlo por el UNIQUEID de un agente, una pierna Local o un worker, ni truncarlo/generar otro id para hacer coincidir el límite.
El CRM conserva la última consulta de un id si se reintenta CUIL. El hook de Queue opera sobre el canal llamante; debe tomar el id preservado, sin fallback silencioso a otro canal.

## GET /api/central/preatendedor
Query:
- opcion: obligatorio, opción del menú1 o2. Se registra para estadísticas, no modifica el JSON de respuesta.
- cuil: opcional; el servidor elimina espacios y guiones y valida11 dígitos + dígito verificador. Ausente o inválido devuelve cuilValido=false, no404.
- llamada: obligatorio, id original, máximo40.

Consultar en opciones1/2 aunque el CUIL sea inválido o vacío: la validación final y su registro pertenecen a la API. Normalizar espacios/guiones sin imponer reglas comerciales locales.
Opción3 no necesita GET; su destino se configura directamente en PBX y queda por confirmar.

Respuesta200, todos los campos presentes:
~~~json
{
  "cuilValido": true,
  "esTitular": true,
  "activo": true,
  "prestadora": "<prestadora>",
  "provincia": "<provincia>",
  "referencias": ["A", "DBT"],
  "esProveedor": false
}
~~~
Tipos: cuilValido/esTitular/activo/esProveedor booleanos; prestadora/provincia string o null; referencias lista de strings. Valores de salud anteriores son ejemplos del documento, nunca fixtures/logs con datos reales.
cuilValido=false implica restantes datos vacíos (false/null/[]).
esTitular distingue titular de familiar; activo sólo true para titular sin baja.
Prestadora/provincia/referencias pueden corresponder a titular o familiar, incluso de baja; null/[] si no está en padrón.
referencias son vigentes, únicas y ordenadas por el servidor. La central sólo evalúa si la lista está vacía.
No hay id del afiliado, nombre ni CUIL en la respuesta: no exigirlos.

Fallos:400 parámetros,401 clave ausente/incorrecta,403 IP no habilitada,503 servidor sin clave, otros5xx. Cuerpos401/403/503 pueden estar vacíos.
Presupuesto TOTAL GET máximo3 segundos. Sin respuesta, HTTP distinto de200, JSON ilegible o schema inválido (incluido cuilValido ausente/tipo incorrecto) → CALL_CENTER. No interpretar errores técnicos como CUIL inválido ni como afiliado inexistente.

## POST /api/central/llamada-atendida
Header X-Api-Key y Content-Type: application/x-www-form-urlencoded.
Cuerpo de formulario con exactamente los datos del contrato:
~~~text
llamada=<UNIQUEID original>&interno=<interno>
~~~
URL-encode de ambos valores. No enviar JSON, Bearer, agenteCRM, afiliado_id, CUIL ni referencias. El API también admite query string, pero usar cuerpo para la implementación.
interno es string de sólo dígitos, máximo10; es el configurado por la operadora en Atenciones, sección Mi interno. Atenciones resuelve a la operadora: se elimina el map interno→usuarioCRM.

Respuesta200: {"resultado":"OK"}, {"resultado":"SIN_VALIDACION"} o {"resultado":"SIN_OPERADOR"}.
En los tres casos continúa la llamada. SIN_VALIDACION significa sin GET previo con ese id; SIN_OPERADOR, sin operadora asociada al interno.
Fallos HTTP/red/JSON se ignoran para el curso de la conversación. El AGI despacha POST fuera del camino síncrono de atención, con timeout finito. Sin retries automáticos mientras no se acuerde idempotencia. No prometer entrega garantizada.

Instalar/preparar el hook de respuesta también cuando GET falle y la llamada vaya a la cola de contingencia, conservando el id original. Un eventual POST SIN_VALIDACION es válido. No exigir un afiliado_id, agenteCRM o CUIL para despachar.

## Reglas PROPUESTAS por el documento del Call Center
Aún deben confirmarse para la configuración operativa; los mocks pueden verificar fielmente esta tabla. No inferir reglas adicionales por prestadora/provincia.

Orden de evaluación opción1 (quiere afiliarse):
1. cuilValido=false → INVALID_CUIL.
2. esProveedor=true → END_CALL.
3. esTitular=true Y activo=true → END_CALL.
4. Resto → CALL_CENTER.

Orden opción2 (ya beneficiario):
1. cuilValido=false → INVALID_CUIL.
2. esTitular=false O activo=false → END_CALL.
3. referencias no vacía → PORTAL.
4. referencias vacía → CALL_CENTER.

El chequeo de esProveedor de opción1 NO se agrega a opción2.
Una falla técnica precede a estas reglas y siempre devuelve CALL_CENTER, incluso si el CUIL capturado parecía inválido.

## Configuración propuesta de Dynamic Routes
Mantener dos destinos Dynamic Routes que compartan el mismo AGI:
- IVR opción1 → Afiliarse; argumento de opción fijo1.
- IVR opción2 → Beneficiarios; argumento fijo2.
- Opción3 → destino PBX a confirmar, sin GET.

Get DTMF input activado, Announcement de System Recordings, tiempo de captura independiente del timeout HTTP.
Propuesta para evitar CUIL en argv de AGI: Source AGI, script crm_get_afiliado.agi.php,1 (o ,2); leer la variable local dtmfinput que crea Dynamic Routes2.11 y limpiarla tras consumirla. Input Variable vacío para no crear una copia heredable del CUIL. Confirmar el nombre en dialplan instalado; permitir configuración explícita de ese nombre.
AGI Result Variable: CRM_ROUTE_KEY; guardar únicamente el id opaco de llamada y clave abstracta de destino, no la respuesta.
Entradas:
| Valor | Destino PBX |
|---|---|
| CALL_CENTER | cola6000, o la acordada |
| INVALID_CUIL | anuncio CUIL inválido y colgar |
| END_CALL | colgar |
| PORTAL | anuncio con URL del Portal, destino final por confirmar |
| Default | cola Call Center |

Portal se describe como una locución que informa su URL. No asumir transferencia a0800 ni una llamada HTTP a dicha URL. Confirmar URL y finalización del anuncio antes de grabar/configurar.
Estos nombres de claves son del adaptador propuesto, no campos ni destinos devueltos por Atenciones.

## Queue e interno del cliente
Evidencia instalada: Asterisk11.25.3, IssabelPBX2.11.0-48, cola6000, miembros dinámicos Local/<interno>@from-queue/n. Cada operador tiene interno propio; no agentes clásicos configurados.
El dialplan6000 pasa QAGI a Queue y define QUEUENUM. Capturar MEMBERINTERFACE en el hook, extraer sólo el patrón Local numérico confirmado (máx10 dígitos), no nombres visibles ni una regex universal de canales. Soporte SIP/PJSIP se valida por separado si se usa.
setinterfacevar=yes en [6000](+) de queues_post_custom.conf después de confirmar su include posterior a queues_additional.conf; preservar hooks ajenos QAGI/VQ_AGI. No editar dialplan generado.
QAGI se ejecuta después de responder y antes del bridge, sobre el llamante. No sustituir por handlers pre-dial b/B; no se necesita AMI permanente.

## Datos personales
referencias sólo vive en memoria durante la decisión. No persistir array/siglas, JSON remoto, prestadora/provincia o CUIL en jobs, CDR, logs ni variables heredables de atención. El job del POST contiene únicamente llamada/interno.
No loguear URL GET completa ni X-Api-Key ni cuerpos del servidor. Diagnósticos acotados por categoría HTTP/timeout/schema, sin datos del beneficiario.
Las trazas AGI/DTMF del propio Asterisk pueden exponer datos si se activan: pruebas con datos ficticios y revisión de logging; no prometer que el script controla los logs del servidor HTTP o de toda la PBX.

## Pruebas de aceptación
CLI/protocolo AGI y HTTP loopback como seams públicos, PHP real. Cubrir todas las ramas en orden de las opciones1/2; opción3 sin GET; CUIL inválido/vacío y normalización; schema completo/booleanos estrictos; timeout3s/HTTP no200/JSON inválido → CALL_CENTER; GET no404 para ausencia de afiliado; misma llamada tras reintentos y cambios de canal; POST formulario/X-Api-Key sin CUIL/refs/agente; tres resultados200 y fallos sin bloquear; correlación en fallback; interno Local real; ausencia de datos sensibles en stdout/argv/logs/jobs.
Testing manual en menú de prueba, sin línea real: operadora carga Mi interno, atiende y recibe pantalla; apagar Atenciones y comprobar ingreso a Call Center.
No equivale a aceptación instalada ni a revisión aprobada de PR47.

## Pendientes externos
- URL real de testing y clave por canal seguro; producción cuando corresponda.
- IP de origen efectiva de la central y prueba HTTPS/certificado.
- Confirmación operativa de reglas sugeridas, destino opción3 y URL/finalización del anuncio Portal.
- Casos de prueba ficticios proporcionados por Atenciones.
