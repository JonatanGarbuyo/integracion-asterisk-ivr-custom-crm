# Dynamic Routes + AGI para Atenciones

Dos AGI independientes del addon (que permanece pausado), PHP CLI 5.4+ con cURL y JSON. Sin Composer, Python en producción ni listener AMI.

`crm_get_afiliado.agi.php` consulta el servidor y calcula valores. **No ejecuta Goto, Queue, Playback ni Hangup**. Dynamic Routes relaciona cada valor con un destino nativo. `crm_set_atencion.agi.php` avisa en segundo plano qué interno respondió usando el mismo id del llamante.

Contrato y reglas completas: [ATENCIONES-CONTRACT.md](ATENCIONES-CONTRACT.md).

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

Crear una ruta de prueba en la configuración PBX. Las opciones 1 y 2 del IVR pueden compartirla:

| Campo nativo | Valor |
|---|---|
| Get DTMF input | Sí |
| Announcement | Audio del sistema que solicita CUIL |
| Maximum digits | 11 |
| Input Variable | Vacío (evitar otra copia del CUIL) |
| Source type | AGI |
| AGI script and parameters | `crm_get_afiliado.agi.php,${IVR_DIGIT_PRESSED}` |
| AGI Result Variable | `CRM_ROUTE_KEY` |
| Result Variable adicional | Vacío, salvo que se necesite expresamente |
| Default Destination | Cola del Call Center |

La variable del dígito seleccionado está presente en el IVR 2.11 consultado; confirmar en el dialplan instalado. Si el argumento llega vacío, el AGI lee `IVR_DIGIT_PRESSED`. Para una prueba fuera del IVR, usar argumento literal `1` o `2`. No inventar esa opción: la API la registra para estadísticas. Opción 3: apuntar directamente a su destino nativo sin GET.

El AGI lee CUIL de `dtmfinput` y lo limpia. Si la versión instalada usa otra variable de captura, ajustar `[runtime] cuil_variable` después de comprobar el dialplan. No pasar el CUIL como parámetro del AGI.

Ejemplo de mapa **en Dynamic Routes** (colas y audios ilustrativos):

| Match | Destination |
|---|---|
| `CALL_CENTER` | Queues → 6000 |
| `PORTAL` | Announcement → Mensaje Portal → destino acordado |
| `INVALID_CUIL` | Announcement → CUIL inválido → Terminate Call |
| `END_CALL` | Announcement opcional → Terminate Call |
| Default | Queues → 6000 |

El AGI evalúa las reglas del documento para devolver estas claves; no conoce números de cola, audios ni contextos. Cambiar un destino requiere modificar el mapa nativo, no el script. Configurar audios y URL del Portal con el responsable antes de grabarlos.

**Alternativa por prestadora:** cambiar AGI Result Variable a `CRM_PRESTADORA` y usar nombres EXACTOS del servidor como Match (`Prestadora A` → cola 6000, `Prestadora B` → cola 6001). Ese selector utiliza prestadora en lugar de la decisión de negocio. Default sigue siendo Call Center para nombres sin mapa, datos ausentes y fallos. No se exportan referencias ni provincia para enrutar.

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
