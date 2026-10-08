# Instalación de laboratorio

Esta entrega se verifica contra procesos reales y fronteras simuladas. Las dos PBX instaladas, audio, regeneración de configuración, miembros de cola y permisos/SELinux efectivos quedan en [la entrega de laboratorio](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/27).

## Imágenes objetivo

| Imagen | Inventario |
|---|---|
| Cliente | Issabel 4.0.0-1, CentOS 7.9, Asterisk 11.25.3, IssabelPBX 2.11.0-48, issabel-callcenter 4.0.0-5. |
| Segunda imagen | Issabel 5 con Asterisk 18; confirmar RPM y runtime en la VM elegida. |

Crear ambas VM en VirtualBox sin conectarlas a la troncal del cliente. Usar red host-only para dos softphones/extensiones y un IVR habitual. Antes de instalar, capturar snapshot de la VM y registrar `php -v`, `/usr/bin/python3 --version`, `amportal a ma list`, propietario/grupo del servicio web/PBX y estado SELinux. El núcleo exige Python >=3.6 en `/usr/bin/python3`, PHP >=5.4 con openssl y proc_open habilitado. El inventario suministrado no confirma esos runtimes; instalar el intérprete adecuado en la VM si falta, sin cambiar el Asterisk del cliente.

## Instalar directamente desde el repositorio

La versión 0.2.0 instala un módulo nativo **PBX → CallFlow Hooks** y el puente IssabelPBX. No requiere transferir un `.tgz`. Usar únicamente la VM de laboratorio y conservar el snapshot anterior.

Para construir desde el repo se requieren `git`, `rpm-build`, Python >=3.6, PHP >=5.4 y las herramientas habituales de Issabel. Si yum sigue consultando mirrorlist retirados de CentOS 7, usar la configuración temporal Vault ya utilizada para instalar Python; el instalador no modifica repositorios ni hace una actualización global.

```bash
git clone --branch feat/callflow-generic-profile https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm.git
cd integracion-asterisk-ivr-custom-crm
CFH_REVISION="$(git rev-parse HEAD)"
git checkout --detach "$CFH_REVISION"
sudo /usr/bin/python3 tools/install.py --checkout "$PWD" --ref "$CFH_REVISION"
```

El comando fija y registra el commit descargado. Para repetir una versión concreta, sustituir `CFH_REVISION` por su SHA completo antes del checkout. El árbol debe estar limpio. El instalador comprueba la PBX antes de construir/reemplazar el paquete, construye el RPM, verifica su manifiesto/checksum/metadatos y lo instala con `rpm -Uvh --replacepkgs`. No aplica automáticamente los cambios PBX al instalar: revisar destinos e IVR y usar Aplicar configuración.

Para preparar el RPM sin instalarlo:

```bash
/usr/bin/python3 tools/install.py --checkout "$PWD" --ref "$CFH_REVISION" --prepare-only --output dist/prepared
```

### Versiones publicadas

Cuando exista una release `v0.2.0` con RPM y `manifest.json`, se podrá descargar sólo el instalador y ejecutar:

```bash
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/v0.2.0/tools/install.py -o /tmp/callflow-install.py
sudo /usr/bin/python3 /tmp/callflow-install.py --release v0.2.0
```

Esta modalidad requiere `rpm2cpio` y `cpio`, pero no `git` ni `rpmbuild` en la PBX. **El tag/release no ha sido publicado durante esta corrección**; los comandos de release son futuros. El workflow de publicación se ejecuta al crear un tag coincidente con la versión del paquete. El checksum detecta corrupción y se contrasta además la identidad del RPM; no equivale por sí solo a una firma de un editor independiente.

## Registro, permisos y actualización

El RPM coloca el formulario en `/var/www/html/modules/callflowhooks`, el puente en `/var/www/html/admin/modules/callflowhooks` y el backend/extensiones en `/usr/share/callflow-hooks`. Se registra menú/ACL mediante `issabel-menumerge`. Por defecto, el framework concede acceso al grupo administrador; los permisos adicionales se administran en Issabel y la actualización conserva sus decisiones.

El paquete requiere que los procesos PHP/httpd y Asterisk usen el mismo usuario de servicio no root. Comprueba los procesos y el usuario configurado de la PBX; si difieren, detiene la instalación e informa la causa. La configuración usa directorio 0700 y archivo 0600 propiedad de ese usuario. Después del gestor PBX se restablecen esos permisos y propiedad root del código propio. No modificar Python del sistema ni deshabilitar SELinux para instalar; verificar los contextos efectivos desde web y llamada en la VM.

Repetir el instalador permite reinstalar/reparar la misma versión y actualizar desde un nuevo checkout o release. Conserva `profiles.conf` y sus secretos. Después de una instalación parcial, corregir la fase informada y repetir; no anunciar éxito hasta que el registro nativo, puente y metadatos coincidan.

```bash
sudo /usr/sbin/callflow-hooksctl status
```

Al migrar desde el `.tgz` 0.1.0, se conservan perfiles y destinos propios. El generador prefiere el runtime compartido del RPM; los archivos antiguos del `.tgz` que RPM no posee pueden seguir presentes, pero no se usan como runtime cuando existe el compartido. Guardar/sincronizar valida colisiones y registra destinos propios; nunca escribir directamente en dialplan generado.

El `.tgz` de `tools/build.py` sigue siendo únicamente un artefacto del puente IssabelPBX. No usarlo como alternativa al RPM si se espera el menú nativo.

## Llamada de prueba y desactivación

1. Crear dos perfiles con la extensión `example` y destinos de internos de laboratorio diferentes. Seleccionarlos desde dos opciones del IVR normal y aplicar configuración.
2. Llamar a ambas opciones. Registrar interno alcanzado y variables `CALLFLOW_*` sin datos personales. Probar `none`, CallerID, DTMF y una variable de canal preparada por un contexto propio.
3. Deshabilitar un perfil desde el formulario. Las nuevas ejecuciones usan su contingencia; el destino sigue existiendo. Rehabilitar y repetir.
4. Para quitar el módulo, retirar primero referencias desde IVR/rutas, aplicar y esperar a que terminen llamadas en curso. Ejecutar `sudo rpm -e issabel-callflow-hooks`. El paquete rechaza referencias activas a destinos propios y llamadas en curso; retira el puente, regenera PBX y elimina su menú/ACL. Esa regeneración aplica los cambios PBX pendientes, por lo que deben revisarse antes de quitarlo. Si falla la recarga se conserva el código y se puede repetir tras corregir. Se borran únicamente destinos marcados como propios; se conserva .conf para reinstalar.
5. Recuperar el snapshot de VM para la reversión completa del laboratorio. No usar desinstalación con llamadas activas como mecanismo de reversión de producción.

No se han probado estos pasos en una VM Issabel durante esta entrega. Un CI verde no confirma audio, permisos SELinux, menú de la distribución, cola ni proveedor real.
