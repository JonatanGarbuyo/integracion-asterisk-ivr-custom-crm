# Dos AGI para Dynamic Routes y Atenciones

Instalar sólo los dos PHP en `/var/lib/asterisk/agi-bin/` y un `.conf` local. PHP CLI5.4+ con cURL/JSON; sin addon, paquete, Composer, Python en la PBX ni listener AMI. CI y OpenCode permanecen desactivados.

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

## Configuración de Dynamic Routes

Crear dos rutas. El usuario configura audios, IVR, anuncios y colas.

| Campo | Ruta de opción1 | Ruta de opción2 |
|---|---|---|
| Name | Atenciones - Afiliaciones | Atenciones - Beneficiarios |
| Get DTMF input | Activado | Activado |
| Timeout | 5 segundos para ingresar dígitos | 5 segundos para ingresar dígitos |
| Input Variable | Vacío | Vacío |
| Result Variable | Vacío | Vacío |
| Announcement | Audio que solicita CUIL | Audio que solicita CUIL |
| Source type | AGI | AGI |
| AGI script and parameters | `crm_get_afiliado.agi.php,1` | `crm_get_afiliado.agi.php,2` |
| AGI result variable | `CRM_ROUTE_KEY` | `CRM_ROUTE_KEY` |
| Default destination | Queues → CallCenter6000 | Queues → CallCenter6000 |

Sin `${...}` en AGI result variable. La captura nativa usa `dtmfinput`; el AGI la lee y limpia. Input Variable vacío evita una copia heredada del CUIL. No pasar CUIL en parámetros del script.

La implementación pública consultada no ofrece campo de máximo de dígitos: `Read()` termina con `#` o timeout. El audio puede pedir finalizar con `#`; si la versión instalada sí ofrece máximo de dígitos, el usuario puede ajustar esa captura. La validez del CUIL la decide exclusivamente Atenciones. El Timeout de esta pantalla es para DTMF; el timeout HTTP de3 segundos está dentro del AGI.

En AMBAS rutas configurar exactamente:

| Match | Destination |
|---|---|
| `CALL_CENTER` | Queues → CallCenter6000 |
| `PORTAL` | Announcement → Portal de beneficiarios, seguido del destino acordado |
| `END_CALL` | Announcement → Mensaje de rechazo → Terminate Call/Hangup |
| `INVALID_CUIL` | Announcement → Mensaje CUIL inválido → Terminate Call/Hangup |
| Default destination | Queues → CallCenter6000 |

No hace falta una entrada ERROR. HTTP no200, timeout, JSON inválido, destino ausente/vacío o tipo inválido devuelven CALL_CENTER. Una clave nueva válida se conserva: si todavía no tiene Match, el Default nativo la envía a CallCenter. No dejar Default en Hangup.

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

En la PBX usar menú aislado, clave y CUIL de testing. Comprobar4 claves, Default, aviso al responder y caída de API. La conectividad/TLS/IP admitida se verifica desde la central; no se probaron endpoints reales desde el entorno de desarrollo. No registrar URL GET completa ni activar trazas AGI/DTMF con CUIL reales.

Campos de Dynamic Routes comprobados contra el [código público de IssabelPBX](https://github.com/IssabelFoundation/issabelPBX/blob/master/dynroute/functions.inc.php). Contrato: [ATENCIONES-CONTRACT.md](ATENCIONES-CONTRACT.md).
