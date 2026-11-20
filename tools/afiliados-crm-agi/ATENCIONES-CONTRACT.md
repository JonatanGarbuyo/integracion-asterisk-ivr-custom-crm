# Atenciones — contrato recibido el20/11/2026

Fuente: documento central.md del proveedor, confirmado e implementado en testing. **Atenciones decide; Dynamic Routes ejecuta el destino.** Sustituye completamente la respuesta anterior con siete campos de afiliado y toda regla local por titularidad, baja, referencias, proveedor o prestadora.

## Conexión

- Testing: `https://testing.ospaca.com/Atenciones`.
- Producción: `https://sistema.ospaca.com/Atenciones`.
- Ambos endpoints: header `X-Api-Key`; claves por canal aparte y fuera de Git.
- Proveedor informa IP admitidas192.168.200.10 y192.168.201.10. Conectividad/origen efectivo/TLS deben comprobarse desde la central.
- Peer y hostname TLS verificados. CA privada opcional; sin redirects. Timeout de conexión1s, HTTP total3s y cuerpo máximo16KiB.

## GET /api/central/preatendedor

Query: `opcion` (un dígito), `cuil` (opcional, normalizar espacios/guiones) y `llamada` (UNIQUEID original≤40). La API valida CUIL, incluso cuando falta o es inválido. El mismo CUIL puede tener decisiones distintas por opción. El IVR manda opción3 directamente a su anuncio; el AGI genérico admite cualquier dígito si se lo invoca y deja la decisión al servidor.

HTTP200:

```json
{"destino":"CALL_CENTER"}
```

Claves iniciales: CALL_CENTER, PORTAL, END_CALL, INVALID_CUIL. El AGI no contiene esa lista como validación ni interpreta negocio: acepta un destino string no vacío, hasta512 bytes y sin caracteres de control, conserva su valor y lo escribe en `CRM_ROUTE_KEY`.

Una clave futura válida se devuelve intacta; Dynamic Routes decide si tiene Match o usa Default. No se devuelven prestadoras ni datos del afiliado. Las variables antiguas de afiliación se limpian por compatibilidad, sin rellenarlas.

Decisión posterior del usuario: fallo HTTP/red/timeout, JSON ilegible/no objeto, destino ausente/vacío/null/no string o técnicamente inválido → ERROR. Esto sustituye la recomendación CALL_CENTER del documento del proveedor; el endpoint no cambia. El operador define ERROR y Default en Dynamic Routes; no hay derivación automática a CallCenter. Una clave nueva sin Match usa Default.

## Captura confirmada, autorizada después del contrato

Dynamic Routes tiene Get DTMF input desactivado. El primer AGI solicita CUIL, captura hasta11 dígitos (o finaliza con #), reproduce «Usted ingresó» y cada dígito mediante audios propios0..9, y solicita1 para confirmar o2 para reingresar. Sólo1 dispara el GET. Sin validación local del padrón ni checksum; un valor corto confirmado puede recibir INVALID_CUIL del servidor.

Tres intentos totales configurables (incluye el primero), timeout de inactividad de entrada5s y confirmación5s, configurables como segundos enteros positivos. Un ingreso incompleto por timeout, ingreso vacío, *, reingreso o confirmación inválida/ausente consume intento. Agotamiento→INPUT_FAILED, sin GET. Error de audio/configuración/protocolo→ERROR; corte del canal detiene la consulta. HTTP sigue con presupuesto3s. Script no ejecutable/ausente→Default nativo.

El CUIL no se exporta a variables de canal ni se pasa por argv. Audios en custom/atenciones bajo sounds; request_audio/entered_audio/confirm_audio/digit_audio_prefix en .conf. No voces del sistema ni SAY DIGITS.

Errores remotos:400 parámetros,401 clave,403 IP,503 falta clave del servidor y otros5xx. No interpretarlos como decisiones de afiliación.

## POST /api/central/llamada-atendida

`X-Api-Key`, `Content-Type: application/x-www-form-urlencoded`. Sólo `llamada` (mismo id original≤40) e `interno` (string1–10 dígitos). Atenciones resuelve operadora mediante “Mi interno”.

HTTP200: `{"resultado":"OK"}`, SIN_VALIDACION o SIN_OPERADOR. No cambia la conversación por ningún resultado, HTTP fallido o JSON inválido. El aviso sale fuera del camino síncrono de Queue, mediante el modo --send del mismo segundo AGI. Temporal privado sólo llamada/interno, consumido una vez antes del POST; sin retries ni entrega garantizada.

## Correlación y cola

`__CRM_CALL_ID` se toma una vez del UNIQUEID del llamante y se reutiliza en GET/reintentos/POST. No truncar ni sustituir por id del miembro/Local/worker. Si ya hay canales Local antes de consultar, el dialplan de entrada debe preservar el id del llamante antes de crearlos.

QAGI se prepara antes de GET, también para contingencia. El dialplan real de cola6000 usa QAGI como sexto argumento de Queue. QAGI ejecuta sobre el llamante al responder, no es un hook pre-dial. `setinterfacevar=yes` habilita MEMBERINTERFACE; Local/1001@from-queue/n produce1001. Se preservan hooks QAGI/VQ_AGI ajenos y se marca conflicto para componerlos explícitamente.

## Entrega, privacidad y pruebas

Dos AGI autocontenidos más un .conf local. Sin paquete, common.php, tercer worker, addon, Composer, AMI permanente o Python en la PBX. Mock/test bajo tests/, fuera de instalación.

No registrar CUIL/URL completa/clave/cuerpo remoto en logs o CDR; no guardar datos del afiliado en jobs. Diagnósticos de categorías fijas. Las trazas AGI/DTMF de Asterisk pueden exponer entrada si se habilitan: sólo datos ficticios al depurar.

Pruebas locales por stdin/stdout AGI y HTTP real simulado: captura/confirmación/reingreso con audios propios, intentos y tiempos configurables, INPUT_FAILED/ERROR,4 claves iniciales y futuras, ausencia de reglas de negocio, errores/tipos/timeout/TLS, correlación, interno, dos archivos suficientes y POST no bloqueante. Sin Actions/OpenCode por decisión del usuario. No equivalen a aceptación en PBX/CRM real.

Usuario configura audios, IVR y colas. Queda su prueba de menú aislado contra testing y aviso de la operadora; URL/audio del Portal de beneficiarios la confirma CallCenter. No hubo instalación, merge o deploy desde este entorno.
