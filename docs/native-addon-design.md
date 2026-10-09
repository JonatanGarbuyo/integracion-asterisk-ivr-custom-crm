# Administración nativa e instalación desde el repositorio

Diseño de la corrección de la primera entrega, ticket [#21](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/21). La versión 0.2.5 implementa este diseño con pruebas en fronteras simuladas y construcción RPM real. Se distribuye como prerelease de laboratorio; la VM Issabel 4 confirmó instalación y menú nativo con 0.2.1; 0.2.2 confirmó guardado desde la web; el log posterior confirmó dialplan aplicado, AGI y atención en 101; ACL completos, audio, contingencia y la VM Issabel 5 siguen pendientes. La especificación y los tickets de GitHub siguen siendo canónicos.

## Componentes

| Componente | Responsabilidad | Ubicación prevista |
|---|---|---|
| Acceso nativo Issabel anterior | Compatibilidad, sesión y ACL | `/var/www/html/modules/callflowhooks/` |
| Módulo IssabelPBX integrado | Formulario, Custom Destinations y generación del dialplan | `/var/www/html/admin/modules/callflowhooks/` |
| Núcleo y extensiones | Administración JSON, ejecución AGI y handlers | `/usr/share/callflow-hooks/` |
| Configuración | Fuente compartida entre formulario, CLI y llamadas | `/etc/asterisk/callflow-hooks/profiles.conf` |

Un RPM instala los componentes juntos. Desde 0.2.5, por solicitud del usuario, la interfaz principal es **PBX → PBX Configuration → Inbound Call Control → CallFlow Hooks**. `category`/`embedcategory` registran esa categoría en el menú PBX; no se modifica el editor del IVR ni se añade un menú mediante JavaScript. El shell normal muestra Aplicar cambios y el módulo marca `needreload` al guardar/sincronizar. El acceso nativo anterior conserva `menu.xml`, ACL y formulario con un enlace a la nueva ubicación, para una actualización compatible. En Issabel 4 embebido se comprueba además `hasModulePrivilege` del framework, porque su wrapper construye `AMP_user` como admin. La sección PBX se comprueba en todos los accesos PBX. Si existe una sesión Issabel, se exige además su permiso de módulo incluso sin embeber, para no confiar en un AMP admin heredado. Cuando falta el ACL del framework se deniega y se indica abrir desde Configuración PBX de Issabel. Un login PBX independiente sin sesión Issabel conserva su control de sección. Ambos accesos comparten formulario y backend. El RPM instala el núcleo compartido; el `.tgz` conserva sólo la estructura del puente.

Guardar valida y reemplaza el .conf que consumen nuevas ejecuciones AGI. Aplicar regenera el dialplan; no se agrega configuración pendiente/activa ni recarga automática en esta corrección de menú y diseño.

La investigación [del registro nativo](research/addon-nativo-issabel.md) respalda los mecanismos; las versiones exactas instaladas se comprueban en laboratorio. No se modifica el editor de IVR ni se mantiene un fork de éste.

## Interfaz administrativa

- Listar perfiles y su estado, crear/editar un perfil y descubrir extensiones instaladas.
- Generar campos desde el mismo esquema que consume el administrador JSON existente.
- Mantener la misma configuración `.conf`, validación, control de versión y tratamiento de secretos.
- Guardar y sincronizar únicamente Custom Destinations propios mediante el adaptador PBX.
- Mostrar el destino que debe seleccionarse en el IVR normal y si hay cambios pendientes de aplicar mediante el flujo PBX habitual.
- Validar acceso nativo y CSRF en cada operación de escritura. El proceso web no recibe privilegios root; la instalación de software permanece en CLI/RPM.

El formulario no implementa todavía el perfil comercial ni el hook de respuesta de cola. Las dos funciones conservan sus entregas separadas.

## Instalar sin transferir archivos manualmente

El usuario solicita instalar directamente desde GitHub. El repositorio incluye `tools/install.py` y su uso en [laboratorio](laboratory.md); el administrador puede descargarlo y ejecutarlo en la PBX, o ejecutarlo desde un checkout. La prerelease de laboratorio permite descargar el RPM sin instalar Git ni herramientas de construcción en la PBX.

**Versiones publicadas:** seleccionar un tag de release explícito. El instalador obtiene el manifiesto y el RPM apropiado, comprueba su integridad y metadatos de versión/arquitectura y usa el gestor de paquetes local. No exige Python de desarrollo, Git ni `rpmbuild` en la PBX cuando instala un RPM publicado. Los checksums detectan corrupción; la autenticidad depende además del canal y de la procedencia de la publicación, no sólo del checksum.

**Desarrollo:** instalar una revisión explícita desde un checkout del repo. La construcción reutiliza el mismo empaquetado RPM que CI/releases. El modo informa las herramientas de construcción necesarias y falla antes de mutar la PBX si faltan; no presupone que un commit cualquiera tenga un RPM publicado. No utiliza silenciosamente `main` o la última versión.

La descarga/preparación y la instalación son pasos distinguibles. Si la descarga falla o no coincide con la versión solicitada, no se instala nada. Se registra la versión y el commit de origen para reproducir el laboratorio. El instalador no despliega automáticamente una nueva versión por consultar GitHub.

## Ciclo de instalación

1. Comprobar Issabel/framework/PBX, Python >=3.6, PHP >=5.4, usuario efectivo de los servicios y Custom Destinations; informar dependencias faltantes. Conservar Python del sistema. No cambiar los repositorios del sistema ni actualizar globalmente la PBX.
2. Obtener o construir el paquete fijado y verificarlo antes de instalar.
3. Instalar código con propiedad/permisos de paquete; configurar acceso a `.conf` según los usuarios efectivos de web y Asterisk. Preservar una configuración existente y verificar permisos/SELinux sin deshabilitarlo.
4. Registrar módulo nativo y ACL, conservando permisos previamente configurados; registrar el adaptador PBX con su gestor. Evitar duplicados y recursos ajenos.
5. Validar configuración y sincronizar destinos propios. Informar el resultado de cada fase y el paso de aplicar configuración; no confundir instalación parcial con éxito ni prometer una transacción entre recursos diferentes.
6. Verificar versiones, menú, acceso y registro. La llamada real y el audio se comprueban en la VM.

Reinstalar la misma versión es idempotente. Actualizar conserva perfiles y permisos. Una desinstalación comprueba referencias activas a destinos propios, retira los componentes/menú/recursos propios y conserva `.conf`; la limpieza de configuración requiere una acción explícita separada. No puede dejar referencias de IVR apuntando a código retirado. La reversión de laboratorio usa el snapshot y una versión anterior compatible; no se promete downgrade arbitrario de esquemas.

## Verificación y límites

- Empaquetado: contenido y permisos del RPM, correspondencia de versión/commit y manifiesto de publicación.
- Instalador: descarga fallida, versión incorrecta, dependencias ausentes, reinstalación, actualización conservando perfiles, fallo parcial y desinstalación con referencias existentes. Simular GitHub y herramientas del sistema en las fronteras CLI.
- Administración: sesión/ACL/CSRF nativos, esquema → formulario → `.conf` → destino → handler, sin secretos en respuestas o logs.
- Issabel 4 VM: instalar desde el repo sin copiar archivos, ver el menú propio, guardar dos perfiles, aplicar PBX y ejecutar llamadas desde el IVR normal. Registrar evidencia instalada aparte del CI.
- Issabel 5 VM: comprobar inventario real y repetir las pruebas de registro, administración y generación. El código oficial conserva IssabelPBX, pero eso no certifica la imagen objetivo.

Las pruebas cubren el formulario nativo, permisos/CSRF, ciclo de vida e instalador; el job RPM construye e inspecciona el paquete. La evidencia instalada sigue pendiente: un CI verde no certifica menú, audio, SELinux ni compatibilidad efectiva de la imagen.
