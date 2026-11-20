# Dynamic Routes + AGI para Atenciones

Integración standalone mediante Dynamic Routes y dos AGI, PHP CLI 5.4+ con cURL y JSON. Sin dependencia del plugin propio, Composer, Python en producción ni listener AMI.

`crm_get_afiliado.agi.php` consulta el servidor y calcula valores. **No ejecuta Goto, Queue, Playback ni Hangup**. Dynamic Routes relaciona cada valor con un destino nativo. `crm_set_atencion.agi.php` avisa en segundo plano qué interno respondió usando el mismo id del llamante.

Contrato y reglas completas: [ATENCIONES-CONTRACT.md](ATENCIONES-CONTRACT.md).

## Descargar el paquete standalone

El paquete contiene únicamente los dos AGI, sus auxiliares, configuración de ejemplo, mock y esta guía. No contiene workflows, addon ni credenciales. Se descarga directamente del repositorio, sin Git:

```sh
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/feat/afiliados-crm-agi/tools/afiliados-crm-agi/dist/afiliados-crm-agi.tgz -o /tmp/afiliados-crm-agi.tgz
tar --no-same-owner -xzf /tmp/afiliados-crm-agi.tgz -C /tmp
cd /tmp/afiliados-crm-agi
sha256sum -c SHA256SUMS
```

Continuar con la instalación de abajo desde la carpeta extraída. `SOURCE.txt` identifica la revisión del código incluida. La URL usa la rama de entrega del PR47; puede fijarse a su commit para repetir una instalación exacta.

Actions y OpenCode están suspendidos por decisión del usuario. La preparación y las verificaciones de esta entrega son locales. No se requiere CI para instalar o ejecutar estos scripts.

## Instalar en Issabel

Desde esta carpeta, como root:

```sh
php -v
php -m
install -d -o root -g asterisk -m 0750 /var/lib/asterisk/agi-bin/afiliados-crm
install -o root -g asterisk -m 0750 crm_get_afiliado.agi.php crm_set_atencion.agi.php /var/lib/asterisk/agi-bin/
install -o root -g asterisk -m 0640 afiliados-crm/common.php afiliados-crm/crm_worker.php /var/lib/asterisk/agi-bin/afiliados-crm/
install -d -o asterisk -g asterisk -m 0700 /var/spool/asterisk/afiliados-crm
# Sólo la primera instalación: conservar este archivo en futuras actualizaciones.
if [ ! -e /etc/asterisk/afiliados-crm.conf ]; then
  install -o root -g asterisk -m 0640 config.example.conf /etc/asterisk/afiliados-crm.conf
fi
```

Completar `[atenciones] base_url` y `api_key` en `/etc/asterisk/afiliados-crm.conf`. La base incluye `/Atenciones`. Mantener TLS verificado; configurar `ca_file` si se acuerda una CA privada. `curl` y `json` deben aparecer en `php -m`. El worker usa el mismo PHP CLI que ejecuta el AGI y necesita `exec` habilitado. No se instala Python 3 para estos scripts.

## Configurar Dynamic Routes

Crear dos Dynamic Routes de prueba en la configuración PBX. Ambos usan el mismo script y una sola variable de resultado:

| Opción del IVR | Dynamic Route | AGI script and parameters |
|---|---|---|
| 1 — Quiero afiliarme | Afiliaciones | `crm_get_afiliado.agi.php,1` |
| 2 — Soy beneficiario | Beneficiarios | `crm_get_afiliado.agi.php,2` |

Configurar en ambos:

| Campo nativo | Valor |
|---|---|
| Get DTMF input | Sí |
| Announcement | Audio del sistema que solicita CUIL |
| Maximum digits | 11 |
| Input Variable | Vacío (evitar otra copia del CUIL) |
| Source type | AGI |
| AGI Result Variable | `CRM_ROUTE_KEY` |
| Result Variable adicional | Vacío, salvo que se necesite expresamente |
| Default Destination | Cola del Call Center |

El argumento literal identifica la opción elegida y se envía a la API para estadísticas. No se duplican los scripts. Como alternativa, el AGI conserva compatibilidad con `IVR_DIGIT_PRESSED` cuando el argumento está vacío, pero las dos rutas con argumentos explícitos no dependen de esa variable. Opción 3: anuncio del Portal de Proveedores seguido de Terminate Call, sin GET. En el IVR deshabilitar Direct Dial y configurar el destino de timeout sin selección a Terminate Call.

El AGI lee CUIL de `dtmfinput` y lo limpia. Si la versión instalada usa otra variable de captura, ajustar `[runtime] cuil_variable` después de comprobar el dialplan. No pasar el CUIL como parámetro del AGI.

Ejemplo de mapa **en Dynamic Routes** (colas y audios ilustrativos):

| Match | Destination |
|---|---|
| `Osde` | Queues → cola de Osde |
| `Prestadora B` | Queues → cola de Prestadora B |
| `CALL_CENTER` | Queues → 6000 (general) |
| `PORTAL` | Announcement → Mensaje Portal → Terminate Call |
| `INVALID_CUIL` | Announcement → No es posible atender → Terminate Call |
| `END_CALL` | Announcement → No es posible atender → Terminate Call |
| Default | Queues → 6000 |

El AGI primero evalúa las reglas del documento. Si corresponde atender y existe prestadora, `CRM_ROUTE_KEY` contiene su nombre EXACTO, por ejemplo `Osde`, sin prefijo ni normalización. Si corresponde rechazo o Portal, conserva `END_CALL`, `INVALID_CUIL` o `PORTAL` aunque el servidor informe prestadora. Si no hay prestadora o falla la API, devuelve `CALL_CENTER`.

En opción 2, un titular dado de baja devuelve `END_CALL`, confirmado por el usuario. Agregar en cada Dynamic Route los nombres reales de prestadoras como Match y seleccionar sus colas; cada ruta conserva su mapa nativo. Nombres sin Match usan Default (cola general).

El selector principal siempre es `CRM_ROUTE_KEY`: combina política y prestadora en un único valor. `CRM_PRESTADORA` permanece sólo como dato auxiliar; seleccionarla directamente omitiría los filtros. No hay números de cola, mapas de destinos ni normalizadores dentro del AGI. Configurar audios y URL del Portal con el responsable antes de grabarlos.

## Notificar quién atendió

El AGI de consulta preserva `__CRM_CALL_ID` y prepara `__QAGI=crm_set_atencion.agi.php`, incluso si GET falla. El dialplan de cola 6000 del cliente ya pasa QAGI al argumento AGI de Queue; no editar `extensions_additional.conf`.

Después de confirmar que `queues_post_custom.conf` se incluye **después** de `queues_additional.conf`, añadir en `/etc/asterisk/queues_post_custom.conf` para cada cola que se vaya a usar:

```ini
[6000](+)
setinterfacevar=yes

[6001](+)
setinterfacevar=yes
```

```sh
asterisk -rx 'module reload app_queue.so'
asterisk -rx 'queue show 6000'
asterisk -rx 'dialplan show 6000@ext-queues'
```

Aplicar también cambios pendientes desde PBX. Los miembros `Local/1001@from-queue/n` producen `interno=1001`. La operadora carga ese número en “Mi interno” de Atenciones. No hay tabla agente→usuario CRM.

QAGI corre al atender, antes del puente, sobre el canal llamante. Despacha un worker con formulario `llamada=<original>&interno=<numero>` y termina sin esperar HTTP. Los resultados OK/SIN_VALIDACION/SIN_OPERADOR y los errores remotos no alteran la conversación. Es best effort: sin reintentos ni garantía de entrega. Un proceso interrumpido antes de consumir puede dejar un job privado; no se reprocesa automáticamente.

Si existe QAGI o VQ_AGI ajeno, se conserva y se marca `CRM_QAGI_CONFLICT=1`: revisar y componer explícitamente el hook antes de habilitar el piloto. No se sobrescriben integraciones existentes. Si el ingreso ya crea canales Local antes de consultar, capturar `__CRM_CALL_ID=${UNIQUEID}` en el canal original antes de crearlos.

## Mock y prueba aislada

El mock necesita Python 3.6+ sólo en una máquina de laboratorio. No usa datos reales ni imprime URLs con CUIL.

```sh
python3 mock_crm_server.py --port 8899
```

Para mock local, configurar base `http://127.0.0.1:8899/Atenciones`, `api_key="testing-only-key"`, `allow_http_loopback=1`. Desde otra máquina usar HTTPS verificado mediante un proxy de laboratorio: el AGI no habilita HTTP remoto.

| CUIL ficticio | Caso |
|---|---|
| 20000000001 | Titular activo, sin referencias, Prestadora A |
| 20000000028 | Titular activo, referencia ficticia, Prestadora B |
| 20000000036 | Titular de baja |
| 20000000044 | Familiar |
| 30000000007 | Proveedor |
| 20000000052 | No está en padrón |
| 123 | Inválido |

Usar menú de prueba separado de la línea real (por ejemplo llamada de prueba 7777 según instalación). Probar opciones 1/2, mismos CUIL con decisiones distintas, mapa hacia destinos nativos y aviso al interno 1001/1002. Para simular fallos: `--get-status 503`, `--get-delay 4`, `--post-delay 4`, o detener el mock. GET fallido debe devolver CALL_CENTER; POST lento no retiene el AGI. El mock registra consultas sólo en memoria y no sustituye el testing con el proveedor.

No habilitar debug AGI con CUIL reales: las trazas de Asterisk pueden revelar dígitos aunque el script no los registre.

## Pruebas de desarrollo

Con PHP CLI+cURL+JSON y Python 3.8+ y OpenSSL CLI en el entorno de desarrollo:

```sh
python3 -m unittest discover -s tests -p test_afiliados_crm_agi.py -v
```

Ejecutar desde la raíz del repositorio. La suite no se omite silenciosamente si faltan PHP/cURL. Prueba procesos AGI y HTTP reales, no funciones internas simuladas. La instalación Asterisk 11, el certificado del proveedor y la pantalla de la operadora requieren validación en la PBX de laboratorio; no se declaran aceptados por pasar estos tests.

El CI de GitHub sólo automatiza las pruebas de los scripts; no es una dependencia de ejecución ni de la instalación manual en Issabel. No construye ni instala un plugin.
