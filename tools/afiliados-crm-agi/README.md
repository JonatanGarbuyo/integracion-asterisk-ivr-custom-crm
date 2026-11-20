# Dos AGI para Dynamic Routes y Atenciones

En Issabel se instalan sólo:

- `crm_get_afiliado.agi.php`: consulta CUIL y devuelve el valor de enrutamiento.
- `crm_set_atencion.agi.php`: notifica el interno que atendió, en segundo plano.
- `/etc/asterisk/afiliados-crm.conf`: URL y clave del CRM.

PHP CLI 5.4+ con cURL y JSON. Sin addon, Composer, Python en la PBX, auxiliares PHP ni listener AMI. Actions y OpenCode permanecen suspendidos.

## Descargar e instalar

Como root, descargar directamente del repositorio, sin Git ni paquete:

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

Completar `base_url` (incluye `/Atenciones`) y `api_key` en el `.conf` local. No sobrescribirlo al actualizar. `curl` y `json` deben aparecer en `php -m`; el PHP CLI debe tener `exec` habilitado para despachar el aviso. TLS y hostname se verifican; `ca_file` es opcional si el servidor usa una CA privada.

Los auxiliares `agi-bin/afiliados-crm/common.php` y `crm_worker.php` de la entrega anterior ya no se usan. Los nuevos scripts son independientes y no requieren esa carpeta.

## IVR y Dynamic Routes

Crear dos Dynamic Routes y enlazarlos desde el IVR:

| Opción IVR | AGI script and parameters |
|---|---|
| 1 — Quiero afiliarme | `crm_get_afiliado.agi.php,1` |
| 2 — Soy beneficiario | `crm_get_afiliado.agi.php,2` |

En ambos: activar captura DTMF, seleccionar el audio que pide CUIL, máximo11 dígitos, Input Variable vacío, Source type AGI y **AGI Result Variable `CRM_ROUTE_KEY`**. La variable de captura por defecto es `dtmfinput` y el AGI la limpia después de leerla.

Configurar el mapa nativo en cada Dynamic Route:

| Match | Destino ilustrativo |
|---|---|
| `Osde` | Cola de Osde |
| Otra prestadora, nombre exacto | Su cola |
| `CALL_CENTER` | Cola general |
| `PORTAL` | Anuncio Portal → colgar |
| `END_CALL` | Anuncio de rechazo → colgar |
| `INVALID_CUIL` | Anuncio de rechazo → colgar |
| Default | Cola general |

El AGI aplica primero las reglas: Portal/rechazo tienen prioridad. Si corresponde atender, devuelve la prestadora literal, sin prefijo ni normalización. Si falta prestadora o falla la API, devuelve `CALL_CENTER`. Opción2 rechaza al titular de baja, confirmado. Los scripts no conocen colas ni ejecutan Goto/Queue/Hangup.

Opción3: anuncio del Portal de Proveedores → colgar, directamente desde IVR. Deshabilitar Direct Dial y configurar el timeout sin selección a colgar. Confirmar la URL del Portal antes de grabar el anuncio.

## Aviso al atender la cola

El primer AGI conserva el UNIQUEID original en `__CRM_CALL_ID` y prepara `__QAGI=crm_set_atencion.agi.php`, incluso si GET falla. El dialplan de cola6000 del cliente ya pasa QAGI a Queue. Preserva QAGI/VQ_AGI ajenos; si hay conflicto, marca `CRM_QAGI_CONFLICT=1` y debe componerse el hook antes de activar el piloto.

Confirmar que `queues_post_custom.conf` se incluye después de `queues_additional.conf`. Añadir en `/etc/asterisk/queues_post_custom.conf` para cada cola usada:

```ini
[6000](+)
setinterfacevar=yes
```

Aplicar los cambios desde PBX y recargar la configuración de colas. `MEMBERINTERFACE=Local/1001@from-queue/n` produce interno1001. La operadora carga ese número en “Mi interno” de Atenciones.

El segundo AGI se ejecuta a sí mismo en segundo plano y vuelve a Queue sin esperar HTTP. Usa un archivo temporal privado que contiene únicamente llamada/interno y se consume una sola vez; sin retries ni garantía de entrega. No hay un tercer script, servicio o proceso permanente.

## Pruebas

Pruebas locales de desarrollo, fuera de la PBX: `python3 -m unittest discover -s tests -p test_afiliados_crm_agi.py -v`. Mock opcional: `python3 tests/fixtures/mock_atenciones.py --port 8899`. Para ese mock HTTP exclusivamente local se permite agregar `allow_http_loopback=1` a `[atenciones]`.

En la VM usar un menú aislado, URL/clave de testing y CUIL ficticios. Verificar opciones1/2, cada prestadora→cola, rechazos/Portal, aviso a la operadora y contingencia con la API caída. No activar trazas AGI con CUIL reales.

Contrato completo: [ATENCIONES-CONTRACT.md](ATENCIONES-CONTRACT.md). Las pruebas automatizadas no equivalen a aceptación de la PBX/CRM reales.
