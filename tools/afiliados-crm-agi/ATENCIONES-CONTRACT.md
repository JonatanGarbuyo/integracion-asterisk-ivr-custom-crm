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
referencias son vigentes, únicas y ordenadas por el servidor; este adaptador no las usa para derivar.
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

## Alcance de enrutamiento confirmado por el usuario19/11
El AGI sólo consulta Atenciones y expone el valor de prestadora. TODO el mapa origen→destino reside en Dynamic Routes. El AGI no contiene colas, contextos Asterisk, mapas de prestadoras ni reglas comerciales por opción, titularidad, actividad, referencias o provincia.
Las reglas sugeridas en central.md NO se implementan en esta entrega. La opción del menú se envía porque la API la exige para estadísticas; no modifica la lógica del AGI.

Resultado: CRM_ROUTE_KEY es el string de prestadora tal como lo devuelve el servidor, manteniendo mayúsculas, espacios y acentos; sin alias o normalización oculta. El protocolo AGI debe escapar el valor de forma segura, sin ejecutar contenido.
Si cuilValido=false, prestadora=null/vacía, hay JSON/tipo inválido en campos usados o falla la API: CRM_ROUTE_KEY vacío y Dynamic Routes usa Default.
La API devuelve siete campos; el adaptador sólo usa cuilValido (bool) y prestadora (string|null). No exige id/nombre ni evalúa esTitular, activo, provincia, referencias o esProveedor para derivar.

## Configuración propuesta de Dynamic Routes
Las opciones del IVR que consultan CUIL pueden apuntar al MISMO destino Dynamic Routes y compartir un único mapa.
En el módulo IVR2.11 consultado, la selección normal guarda __IVR_DIGIT_PRESSED. Verificar que la instalación la informa correctamente antes de usarla.
- Get DTMF input: activado; Announcement: audio solicitando CUIL.
- Input Variable: vacío, para no crear copia heredable del CUIL.
- Source type: AGI.
- AGI script and parameters: crm_get_afiliado.agi.php,${IVR_DIGIT_PRESSED}.
- El primer argumento es opcion (1/2). El AGI lee el CUIL desde la variable de captura dtmfinput, verificada en dialplan y configurable. Después la limpia. No pasar CUIL en argv.
- AGI Result Variable: CRM_ROUTE_KEY.
- Result Variable adicional: opcional/vacío.
- Entradas y Default administrados por el usuario en Dynamic Routes.

Ejemplo con nombres ficticios (usar los nombres EXACTOS que devuelva testing):
| Match | Destination |
|---|---|
| Prestadora A | Queues →6000 |
| Prestadora B | Queues →6001 |
| Default | Cola del Call Center acordada |

Una prestadora sin entrada también usa Default. No hay cortes automáticos ni desvío al Portal por los datos de respuesta. Cualquier destino externo se configura como destino PBX en el módulo, por decisión del usuario.
Si IVR_DIGIT_PRESSED no está disponible, parametrizar la opción explícitamente en la configuración del IVR/ruta; no inventar una opción estadística. La opción3 conserva un destino directo sin GET, si se mantiene ese menú.

## Queue e interno del cliente
Evidencia instalada: Asterisk11.25.3, IssabelPBX2.11.0-48, cola6000, miembros dinámicos Local/<interno>@from-queue/n. Cada operador tiene interno propio; no agentes clásicos configurados.
El dialplan6000 pasa QAGI a Queue y define QUEUENUM. Capturar MEMBERINTERFACE en el hook, extraer sólo el patrón Local numérico confirmado (máx10 dígitos), no nombres visibles ni una regex universal de canales. Soporte SIP/PJSIP se valida por separado si se usa.
setinterfacevar=yes en [6000](+) de queues_post_custom.conf después de confirmar su include posterior a queues_additional.conf; preservar hooks ajenos QAGI/VQ_AGI. No editar dialplan generado.
QAGI se ejecuta después de responder y antes del bridge, sobre el llamante. No sustituir por handlers pre-dial b/B; no se necesita AMI permanente.

## Datos personales
El adaptador descarta los campos no utilizados, incluidas referencias. No persistir array/siglas, JSON remoto, provincia o CUIL en jobs, CDR, logs ni variables heredables de atención. prestadora sólo se expone como CRM_ROUTE_KEY para que Dynamic Routes aplique su mapa; no se copia al job del aviso. El job del POST contiene únicamente llamada/interno.
No loguear URL GET completa ni X-Api-Key ni cuerpos del servidor. Diagnósticos acotados por categoría HTTP/timeout/schema, sin datos del beneficiario.
Las trazas AGI/DTMF del propio Asterisk pueden exponer datos si se activan: pruebas con datos ficticios y revisión de logging; no prometer que el script controla los logs del servidor HTTP o de toda la PBX.

## Pruebas de aceptación
CLI/protocolo AGI y HTTP loopback como seams públicos, PHP real. Verificar prestadora con espacios/acentos/case conservados y escaping seguro; mismo resultado para opciones1/2 cuando prestadora es igual; ausencia de reglas por titularidad/actividad/referencias/provincia/proveedor; prestadora nula/vacía/CUIL inválido/HTTP no200/schema inválido/timeout3s → resultado vacío y Default del módulo.
Verificar X-Api-Key, formulario POST con sólo llamada/interno, límites40/10, misma llamada tras reintentos/Local/fallo GET, tres resultados200/fallos POST sin bloquear y ausencia de CUIL/referencias en stdout de diagnóstico/argv/logs/jobs. Opción3 sin GET. No tests de una tabla de destinos dentro del AGI, porque no existe.
Testing PBX real: configurar dos prestadoras→dos colas en Dynamic Routes; operadora carga Mi interno, atiende y recibe pantalla; apagar Atenciones y comprobar ingreso a Default/Call Center.
No equivale a aceptación instalada ni a revisión aprobada de PR47.

## Pendientes externos
- URL real de testing y clave por canal seguro; producción cuando corresponda.
- IP de origen efectiva de la central y prueba HTTPS/certificado.
- Nombres exactos de prestadoras de testing y destinos acordados para configurar el mapa nativo; destino directo opción3 si se conserva el menú.
- Casos de prueba ficticios proporcionados por Atenciones.

## Aclaración de alcance del usuario19/11/2026
La API aporta datos y la central usa Dynamic Routes para mapear prestadora→destino. Este alcance reemplaza la interpretación anterior de reglas sugeridas, cortes y Portal. El segundo AGI únicamente informa llamada/interno; Atenciones resuelve la operadora. No hay cambio de código por esta corrección documental.
