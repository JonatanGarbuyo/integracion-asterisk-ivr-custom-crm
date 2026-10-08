# Instalación de laboratorio

Esta entrega se verifica contra procesos reales y fronteras simuladas. Las dos PBX instaladas, audio, regeneración de configuración, miembros de cola y permisos/SELinux efectivos quedan en [la entrega de laboratorio](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/27).

## Imágenes objetivo

| Imagen | Inventario |
|---|---|
| Cliente | Issabel 4.0.0-1, CentOS 7.9, Asterisk 11.25.3, IssabelPBX 2.11.0-48, issabel-callcenter 4.0.0-5. |
| Segunda imagen | Issabel 5 con Asterisk 18; confirmar RPM y runtime en la VM elegida. |

Crear ambas VM en VirtualBox sin conectarlas a la troncal del cliente. Usar red host-only para dos softphones/extensiones y un IVR habitual. Antes de instalar, capturar snapshot de la VM y registrar `php -v`, `/usr/bin/python3 --version`, `amportal a ma list`, propietario/grupo del servicio web/PBX y estado SELinux. El núcleo exige Python >=3.6 en `/usr/bin/python3`, PHP >=5.4 con openssl y proc_open habilitado. El inventario suministrado no confirma esos runtimes; instalar el intérprete adecuado en la VM si falta, sin cambiar el Asterisk del cliente.

## Paquete nativo

```bash
python3 tools/build.py
```

Se genera `dist/callflowhooks-0.1.0.tgz` con estructura `callflowhooks/module.xml`, página PHP, backend y extensión de ejemplo. En Module Administration de IssabelPBX, habilitar **Custom Destinations** (`customappsreg`), cargar el archivo local e instalar **CallFlow Hooks**. Si la versión no permite Upload, extraer el directorio `callflowhooks` en `/var/www/html/admin/modules/` y ejecutar la instalación con el gestor de módulos que liste esa VM (`amportal a ma install callflowhooks` en la familia 2.11). Registrar el comando y resultado efectivo en #27.

El instalador conserva un .conf existente y crea uno vacío con permisos 0600; su directorio usa 0700. La instalación por CLI como root requiere asignar el directorio y configuración al **mismo usuario que ejecuta PHP/PBX** antes de abrir el formulario. No hacer al backend o a `extensions/` escribibles por el proceso web; sólo la configuración requiere escritura. Comprobar que Asterisk puede ejecutar `backend/entry.py` (0755) y leer la configuración. No modificar archivos de dialplan generados.

Al reinstalar, se registran idempotentemente los destinos de perfiles existentes. Para perfiles nuevos, guardar desde el formulario o sincronizar después de editar manualmente. La publicación usa la API nativa de Custom Destinations, con marca de propiedad; una colisión ajena detiene el guardado. Configuración y registro de destinos son recursos distintos: ante interrupción en medio del guardado, revisar y sincronizar antes de aplicar. El generador nativo `_get_config` aporta sólo los contextos propios.

## Llamada de prueba y desactivación

1. Crear dos perfiles con la extensión `example` y destinos de internos de laboratorio diferentes. Seleccionarlos desde dos opciones del IVR normal y aplicar configuración.
2. Llamar a ambas opciones. Registrar interno alcanzado y variables `CALLFLOW_*` sin datos personales. Probar `none`, CallerID, DTMF y una variable de canal preparada por un contexto propio.
3. Deshabilitar un perfil desde el formulario. Las nuevas ejecuciones usan su contingencia; el destino sigue existiendo. Rehabilitar y repetir.
4. Para quitar el módulo, retirar primero referencias desde IVR/rutas, aplicar y esperar a que terminen llamadas en curso. Desinstalar desde Module Administration y aplicar otra vez. Se borran únicamente destinos marcados como propios; se conserva .conf para reinstalar.
5. Recuperar el snapshot de VM para la reversión completa del laboratorio. No usar desinstalación con llamadas activas como mecanismo de reversión de producción.

No se han probado estos pasos en una VM Issabel durante esta entrega. Un CI verde no confirma audio, permisos SELinux, menú de la distribución, cola ni proveedor real.
