# Dos AGI para Dynamic Routes y Atenciones

Instalar sólo los dos PHP en `/var/lib/asterisk/agi-bin/` y un `.conf` local. Objetivo del cliente: PHP CLI **5.4.16**, Issabel4 y Asterisk11.25.3. Los scripts usan sintaxis/API PHP5.4+ con cURL/JSON; sin addon, paquete, Composer, Python en la PBX ni listener AMI. CI y OpenCode permanecen desactivados.

Atenciones responde `{"destino":"CALL_CENTER"}`. El AGI copia `destino` a `CRM_ROUTE_KEY`, sin reglas de afiliación ni lista fija de claves. Una clave nueva se configura en Dynamic Routes sin modificar el script. No se calcula prestadora, titularidad, actividad, referencias o proveedor.

## Descargar e instalar

Como root, desde el repositorio y sin Git:

```sh
mkdir -p /tmp/afiliados-crm-agi
cd /tmp/afiliados-crm-agi
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/feat/afiliados-crm-agi/tools/afiliados-crm-agi/crm_get_afiliado.agi.php -o crm_get_afiliado.agi.php
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/feat/afiliados-crm-agi/tools/afiliados-crm-agi/crm_set_atencion.agi.php -o crm_set_atencion.agi.php
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/feat/afiliados-crm-agi/tools/afiliados-crm-agi/config.example.conf -o config.example.conf
php -m
php -l crm_get_afiliado.agi.php
php -l crm_set_atencion.agi.php
install -o root -g asterisk -m 0750 crm_get_afiliado.agi.php crm_set_atencion.agi.php /var/lib/asterisk/agi-bin/
install -d -o asterisk -g asterisk -m 0700 /var/spool/asterisk/afiliados-crm
if [ ! -e /etc/asterisk/afiliados-crm.conf ]; then
  install -o root -g asterisk -m 0640 config.example.conf /etc/asterisk/afiliados-crm.conf
fi
```

Editar `/etc/asterisk/afiliados-crm.conf`, también si ya existe de una prueba anterior:

```ini
[atenciones]
base_url = "https://testing.ospaca.com/Atenciones"
api_key = "CLAVE_DE_TESTING"
```

La base de producción es `https://sistema.ospaca.com/Atenciones`; para el laboratorio usar testing y su clave correspondiente. No guardar claves reales en Git. `curl` y `json` deben aparecer en `php -m`; `exec` debe estar habilitado para despachar el aviso. TLS/hostname siempre verificados; `ca_file` opcional si se acuerda una CA privada.

La corrección de confirmación se verifica localmente con PHP8.4. El usuario ya validó sintaxis de la versión anterior en PHP5.4.16 y GET real desde la central. **La corrección actual todavía necesita su prueba en la PBX.** No es necesario actualizar PHP para seguir la guía; comprobar en la central los dos `php -l` anteriores y las extensiones cURL/JSON. El aviso asíncrono requiere `exec` habilitado en PHP CLI.

## Actualizar sólo el AGI de consulta

Como root, esta cadena se detiene si falla la descarga, el lint o el backup. Conserva el .conf y el segundo AGI:

```sh
curl -fL --connect-timeout 5 --max-time 30 \
  'https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/feat/afiliados-crm-agi/tools/afiliados-crm-agi/crm_get_afiliado.agi.php' \
  -o /tmp/crm_get_afiliado.agi.php &&
php -l /tmp/crm_get_afiliado.agi.php &&
cp -a /var/lib/asterisk/agi-bin/crm_get_afiliado.agi.php \
  "/root/crm_get_afiliado.agi.php.$(date +%Y%m%d-%H%M%S).bak" &&
install -o root -g asterisk -m 0750 /tmp/crm_get_afiliado.agi.php \
  /var/lib/asterisk/agi-bin/crm_get_afiliado.agi.php.new &&
mv -f /var/lib/asterisk/agi-bin/crm_get_afiliado.agi.php.new \
  /var/lib/asterisk/agi-bin/crm_get_afiliado.agi.php
```

El reemplazo final es por rename en el mismo directorio. El nuevo script se usa en la siguiente ejecución AGI; no requiere reiniciar Asterisk ni regenerar el dialplan. Para configurar otro límite, agregar `max_confirmation_attempts = 3` dentro de la sección `[identification]` existente. No sustituir el .conf: contiene la clave y el ca_file configurados localmente.

Prueba: ingresar CUIL, esperar la pregunta y marcar3. Debe repetir sólo la pregunta. Marcar1 consulta ese mismo CUIL; marcar2 solicita uno nuevo. Tres preguntas sin elección válida, con defaults, terminan en INPUT_FAILED. Esta corrección no modifica el DTMF del teléfono/troncal ni la lectura del número; la pérdida de tonos reportada desde móvil sigue pendiente de diagnóstico.

## Ingreso, confirmación y audios

El primer AGI solicita el CUIL, lo reproduce dígito por dígito con las grabaciones propias y pregunta: «Presione 1 para confirmar o 2 para volver a ingresar». Sólo después de 1 consulta Atenciones. No usa SAY DIGITS ni audios numéricos del sistema.

Copiar las grabaciones a `/var/lib/asterisk/sounds/custom/atenciones/`:

| Archivo | Texto |
|---|---|
| `ingrese-cuil.wav` | «A continuación, ingrese su número de CUIL.» |
| `usted-ingreso.wav` | «Usted ingresó:» |
| `confirme-cuil.wav` | «Presione 1 para confirmar o 2 para volver a ingresar.» |
| `digito-0.wav` a `digito-9.wav` | Un dígito por archivo: cero, uno, dos, tres, cuatro, cinco, seis, siete, ocho y nueve. |

Son13 archivos. La tabla muestra WAV PCM16bits, mono,8000Hz como formato recomendado ([format_wav de Asterisk11](https://github.com/asterisk/asterisk/blob/11/formats/format_wav.c)). **MP3 mono8kHz también puede usarse si `format_mp3.so` está disponible y cargado**: ese módulo de Asterisk11 registra la extensión mp3 e indica que8000Hz mono es óptimo ([fuente oficial](https://github.com/asterisk/asterisk/blob/11/addons/format_mp3.c)). No alcanza con que esté instalado MP3Player/app_mp3.

Comprobar en la PBX, sin cambiar su configuración:

```sh
asterisk -rx 'module show like format_mp3.so'
asterisk -rx 'core show file formats'
```

Si aparece el módulo cargado y mp3 como formato soportado, se pueden copiar `ingrese-cuil.mp3`, `usted-ingreso.mp3`, `confirme-cuil.mp3` y `digito-0.mp3`…`digito-9.mp3` en la misma carpeta. **No cambia el .conf ni el AGI**: Asterisk recibe el nombre sin extensión y busca un formato que pueda leer. El archivo físico sí conserva su extensión; no renombrar un MP3 a WAV.

Si no está disponible el lector MP3, convertir en el equipo de trabajo antes de copiar a la PBX. Ejemplo con FFmpeg instalado en ese equipo:

```sh
ffmpeg -i ingrese-cuil.mp3 -ac 1 -ar 8000 -c:a pcm_s16le ingrese-cuil.wav
```

Repetir para las13 grabaciones. No hace falta instalar FFmpeg ni modificar módulos en la central. El nombre visible de una grabación en System Recordings no necesariamente coincide con su archivo físico: usar los nombres indicados en esta carpeta.

```sh
install -d -o asterisk -g asterisk -m 0755 /var/lib/asterisk/sounds/custom/atenciones
```

Copiar allí los audios del formato elegido mediante SFTP/SCP, con lectura para asterisk (por ejemplo `root:asterisk`, modo0644). No reemplazar los audios del sistema. Las rutas se pueden cambiar en el `.conf`, relativas a `/var/lib/asterisk/sounds/` y **sin extensión**:

```ini
[identification]
max_attempts = 3
max_confirmation_attempts = 3
input_timeout = 5
confirmation_timeout = 5
request_audio = "custom/atenciones/ingrese-cuil"
entered_audio = "custom/atenciones/usted-ingreso"
confirm_audio = "custom/atenciones/confirme-cuil"
digit_audio_prefix = "custom/atenciones/digito-"
```

Agregar esta sección también al actualizar una instalación existente; los valores mostrados son los predeterminados. Intentos y tiempos aceptan enteros positivos1..999; tiempos en segundos. `max_attempts` limita los ingresos de CUIL, incluido el primero. `max_confirmation_attempts` limita las preguntas de confirmación por cada CUIL, incluida la primera; su valor predeterminado es3 aunque se omita en un .conf existente. Los contadores se reinician al ejecutar el AGI y el de confirmación también con cada CUIL nuevo.

La captura termina automáticamente a los11 dígitos; no hace falta `#`. `#` permite finalizar antes: si se confirma un CUIL corto, la API decide su validez y puede devolver INVALID_CUIL. No se valida padrón ni dígito verificador en la central. Silencio o timeout durante una entrada incompleta y `*` consumen un intento de ingreso y vuelven a solicitar el CUIL. Al confirmar: **1** acepta; **2** consume el ingreso actual y solicita un CUIL nuevo si quedan ingresos; otra tecla o silencio conserva el CUIL y repite únicamente la pregunta de confirmación, sin repetir la lectura del número ni consumir otro ingreso. Si se agota el límite de confirmación, devuelve INPUT_FAILED sin pedir otro CUIL ni consultar la API. El timeout de entrada es de inactividad entre dígitos; el de confirmación empieza al terminar su audio. Al agotar intentos devuelve INPUT_FAILED, sin consultar la API.

Un archivo faltante/no reproducible, configuración inválida o error de protocolo deja ERROR; si el canal se corta, se detiene sin consultar. Los comandos usados y sus respuestas se contrastaron con [res_agi.c de Asterisk11](https://github.com/asterisk/asterisk/blob/11/res/res_agi.c). Una falla de audio puede terminar la sesión AGI desde Asterisk; ERROR se inicializa antes de reproducir.

## Configuración de Dynamic Routes

Crear dos rutas, con la captura propia del módulo **desactivada**:

| Campo | Ruta de opción1 | Ruta de opción2 |
|---|---|---|
| Name | Atenciones - Afiliaciones | Atenciones - Beneficiarios |
| Get DTMF input | Desactivado | Desactivado |
| Input Variable / Result Variable | Vacíos | Vacíos |
| Announcement | None | None |
| Source type | AGI | AGI |
| AGI script and parameters | `crm_get_afiliado.agi.php,1` | `crm_get_afiliado.agi.php,2` |
| AGI result variable | `CRM_ROUTE_KEY` | `CRM_ROUTE_KEY` |
| Default destination | El destino elegido para ERROR | El destino elegido para ERROR |

Sin `${...}` en AGI result variable. El AGI captura los dígitos; no usa `dtmfinput` ni recibe CUIL como argumento. El Timeout de la pantalla Dynamic Routes no controla esta captura; usar el `.conf`. El presupuesto HTTP sigue siendo3 segundos, independiente del ingreso/confirmación.

En AMBAS rutas configurar:

| Match | Destination |
|---|---|
| `CALL_CENTER` | Queues → CallCenter6000 |
| `PORTAL` | Announcement → Portal de beneficiarios, seguido del destino acordado |
| `END_CALL` | Announcement → Mensaje de rechazo → Terminate Call/Hangup |
| `INVALID_CUIL` | Announcement → Mensaje CUIL inválido → Terminate Call/Hangup |
| `INPUT_FAILED` | Anuncio/destino que el administrador elija al agotar intentos |
| `ERROR` | Anuncio/destino que el administrador elija ante falla técnica |
| Default destination | El mismo destino elegido para ERROR |

No se envía automáticamente al CallCenter ante un fallo. INPUT_FAILED es un fallo del ingreso/confirmación; INVALID_CUIL es una decisión recibida del servidor. HTTP no200, timeout, JSON inválido, destino ausente/vacío o tipo inválido devuelven ERROR. Si el script no arranca o se recibe una clave nueva sin Match, se usa Default nativo. La clave nueva válida se devuelve intacta, sin una whitelist en el AGI.

Enlazar opción1 del IVR a la primera ruta y opción2 a la segunda. Opción3 va directamente al anuncio del Portal de Proveedores, sin AGI. Confirmar el audio/URL del Portal de beneficiarios, distinto del Portal de Proveedores. Guardar y aplicar cambios desde PBX.

## Aviso al atender

El primer AGI conserva `__CRM_CALL_ID` con el UNIQUEID original y prepara `__QAGI=crm_set_atencion.agi.php`, incluso si GET falla. El dialplan de cola6000 proporcionado por el usuario ya pasa QAGI a Queue. No hay que agregar el segundo AGI como destino ni ejecutarlo al entrar a la cola.

Para disponer de `MEMBERINTERFACE`, agregar a `/etc/asterisk/queues_post_custom.conf`, después de verificar que su include está después de `queues_additional.conf`:

```ini
[6000](+)
setinterfacevar=yes
```

Recargar configuración de colas, por ejemplo `asterisk -rx 'module reload app_queue.so'`, y aplicar cambios desde PBX. Un miembro `Local/1001@from-queue/n` produce interno1001; la operadora carga ese número en Atenciones, en “Mi interno”. QAGI usa el canal llamante; no necesita reemplazar el id con el del miembro.

El segundo AGI se invoca a sí mismo en segundo plano. El POST lleva sólo llamada/interno, sin CUIL ni datos del afiliado; los tres resultados200 y los fallos no afectan la conversación. Conserva un temporal privado de un uso, sin retries/garantía de entrega. Si existe QAGI/VQ_AGI ajeno, se preserva y se señala CRM_QAGI_CONFLICT=1: componer esa integración antes del piloto.

## Verificación local y laboratorio

Suite local de desarrollo: `python3 -m unittest discover -s tests -p test_afiliados_crm_agi.py -v`. Mock externo opcional: `python3 tests/fixtures/mock_atenciones.py --port 8899`; devuelve respuestas enlatadas del nuevo contrato, sin padrón. Sólo para ese mock local puede configurarse `allow_http_loopback=1` y base `http://127.0.0.1:8899/Atenciones`.

En la PBX usar menú aislado, clave y CUIL de testing. Comprobar las4 claves del servidor, INPUT_FAILED, ERROR, Default, confirmación/reingreso, aviso al responder y caída de API. La conectividad/TLS/IP admitida se verifica desde la central; no se probaron endpoints reales desde el entorno de desarrollo. No registrar URL GET completa ni activar trazas AGI/DTMF con CUIL reales.

Campos de Dynamic Routes comprobados contra el [código público de IssabelPBX](https://github.com/IssabelFoundation/issabelPBX/blob/master/dynroute/functions.inc.php). Contrato: [ATENCIONES-CONTRACT.md](ATENCIONES-CONTRACT.md).
