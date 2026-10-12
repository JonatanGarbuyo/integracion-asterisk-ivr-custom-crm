# Perfiles y extensiones

El RPM 0.2.8 ubica la administración en **PBX → PBX Configuration → Inbound Call Control → CallFlow Hooks**. El shell PBX muestra su botón habitual **Aplicar cambios** después de guardar. La página usa navegación lateral de perfiles, creación/edición en una tabla por secciones y ayudas como el IVR normal. Al crear informa cómo vincular el destino al IVR; al editar no repite esa instrucción. En Issabel 4 embebido mantiene la ruta `index.php?menu=pbxadmin&display=callflowhooks`; dentro del frame PBX o sin embeber usa `config.php?display=callflowhooks`. La actualización retira el menú y ACL del acceso anterior `/index.php?menu=callflowhooks`; sólo se administra desde Configuración PBX, con su ACL existente. El `.tgz` instala sólo el puente; se recomienda el RPM completo. Web y CLI guardan en `/etc/asterisk/callflow-hooks/profiles.conf`, la misma fuente que consume el AGI. El listado y el formulario ocultan los campos declarados `secret`; un valor vacío conserva la credencial anterior. Para borrarla expresamente, editar el .conf.

```ini
[profile:welcome]
extension = example
enabled = true
next_destination = ext-local,201,1
fallback_destination = ext-local,202,1
execution_budget_ms = 1000
input_source = callerid
input_variable =
input_prompt =
input_max_digits = 20
input_timeout_ms = 5000
settings = {"greeting":"Buen día","style":"normal","api_token":""}

[profile:night]
extension = example
enabled = true
next_destination = ext-local,203,1
fallback_destination = ext-local,202,1
execution_budget_ms = 1000
input_source = none
settings = {"greeting":"Guardia","style":"breve","api_token":""}
```

El formulario integrado reutiliza el catálogo de `drawselects()` y el JavaScript de IssabelPBX para **Destino al continuar** y **Destino de contingencia**: seleccionar la categoría (Queues, Extensions, IVR, etc.) y su destino existente. Los textos se renderizan escapados porque el helper antiguo no lo garantiza. El `.conf` guarda la cadena real de Asterisk, por ejemplo `ext-queues,6000,1`; se conserva la validación de sintaxis y las restricciones del núcleo. No hay selector de modo manual. Un valor existente del .conf que no está en el catálogo aparece como **Destino actual**, se conserva y puede reemplazarse por un destino PBX. La edición manual sigue disponible en el .conf. Los módulos que declaran popovers ofrecen **Agregar nuevo** dentro del selector, mediante el editor PBX de ese módulo.

**Audio para solicitar dígitos** lista las grabaciones simples de **System Recordings**, como el IVR. Un audio del .conf fuera del catálogo se muestra como valor actual. Se guarda el nombre relativo del archivo, por ejemplo `custom/bienvenido`, sin cambiar el esquema ni añadir IDs al runtime. **Sin audio** guarda un valor vacío; un nombre manual que no figura en el catálogo se conserva. No se aceptan IDs inexistentes ni grabaciones compuestas: la captura actual `GET DATA` utiliza un único audio. El mensaje se usa sólo cuando la fuente de entrada es DTMF; no es un saludo general ni síntesis del campo Saludo del ejemplo.

Los catálogos se consultan al abrir/guardar el formulario; el AGI continúa usando sólo el .conf. Renombrar/eliminar un archivo o destino fuera del addon requiere revisar los perfiles que lo usan. Si las APIs de selector no están disponibles, se informa el problema y se conservan los valores actuales; no se ofrece un editor manual en la web. No se copia ni se modifica el editor de IVR ni la base de datos de grabaciones/destinos.

Los internos del ejemplo deben sustituirse por destinos existentes en la PBX. El núcleo verifica la sintaxis `contexto,extensión,prioridad` y rechaza expresiones/inyecciones y bucles directos entre perfiles; la existencia y conducta del destino requieren la prueba instalada. La contingencia puede igualar el siguiente destino. No se presupone ninguna cola general.

**Guardar** valida y reemplaza el archivo atómicamente, con modo 0600 y bloqueo entre escritores del addon. **Aplicar cambios** regenera el dialplan PBX; no mantiene una copia pendiente separada: las nuevas ejecuciones AGI leen el .conf ya guardado. No se aplica automáticamente ni se introduce staging en esta entrega. Si la versión del formulario quedó vieja, rechaza el guardado y conserva el borrador; revisar los valores antes de volver a guardar. Para edición manual, conservar permisos/propietario, validar antes de publicar y usar reemplazo atómico. Un editor externo que ignore el bloqueo puede competir con un guardado web; evitar ambos simultáneamente.

Cuando falla un guardado, la página conserva el formulario y señala los campos inválidos. El último borrador fallido se mantiene en la sesión administrativa y se recupera al recargar; **Descartar borrador** sólo borra ese borrador. Las credenciales ingresadas no se conservan ni se muestran: volver a ingresarlas si se habían cambiado. La configuración previamente guardada se conserva ante errores de validación, versión o permisos.

La respuesta JSON del administrador incluye `error_code` y `field_errors` en fallas: `validation_error`, `stale_configuration`, `permission_denied`, `io_error` o `configuration_error`. Las claves de campo siguen el esquema (`settings.<campo>` para extensiones); los mensajes describen la regla, sin incluir valores enviados ni excepciones externas. La web distingue fallas de acceso al archivo y errores de campos; los permisos/SELinux deben comprobarse en la PBX si el mensaje los identifica.

```bash
/usr/bin/python3 /usr/share/callflow-hooks/backend/entry.py admin <<'JSON'
{"action":"describe"}
JSON
```

`ok:true` confirma validación, y la respuesta no incluye secretos guardados. Después de crear perfiles manualmente, usar **Sincronizar destinos de .conf**, luego **Aplicar configuración**. Los perfiles creados desde el formulario publican automáticamente su destino en la categoría CallFlow Hooks. El registro Custom Destinations anterior se conserva como compatibilidad, sin cambiar la cadena del destino. El administrador debe seleccionar **CallFlow Hooks → nombre del perfil** desde una opción del IVR habitual. La ruta entrante y el resto del IVR se administran normalmente.

Cada extensión del RPM vive en `/usr/share/callflow-hooks/extensions/<nombre>/manifest.json`, con su ejecutable. Estos archivos se instalan como código confiable del addon y no son editables desde el formulario. Ejemplo:

```json
{
  "identifier":"example",
  "title":"Contexto de ejemplo",
  "contract_version":1,
  "command":["@python","handler.py"],
  "fields":{
    "greeting":{"type":"string","label":"Saludo","default":"Hola","required":true,"max_length":80},
    "style":{"type":"choice","label":"Estilo","default":"normal","options":["normal","breve"]},
    "api_token":{"type":"secret","label":"Credencial","default":""}
  }
}
```

`@python` selecciona el mismo intérprete que ejecuta el núcleo. Otra extensión puede declarar un ejecutable absoluto de PHP, Node u otro lenguaje; los argumentos son una lista, sin shell, y el directorio de trabajo es el de la extensión. El formulario central descubre sus campos sin código específico para cada módulo.

Tipos disponibles: `string`, `secret`, `choice`, `integer`, `boolean`. Validaciones: `required`, `max_length`, `pattern` (string/secret), `options` (choice), `minimum`/`maximum` (integer). Los defaults deben respetar el tipo. Los secretos no admiten defaults con contenido. El esquema describe configuración; la validación de CUIL, DNI u otras identidades pertenece a cada extensión.

DTMF usa `GET DATA`, con audio opcional, máximo de dígitos y tiempo de espera de Asterisk; ese plazo es para captura de dígitos, independiente del presupuesto del proceso handler. `channel` lee la variable declarada por `input_variable`; `callerid` usa CallerID; `none` entrega entrada vacía. La elección no modifica el handler ABI.

## Nombre e identidad

**Nombre del perfil** es editable y se usa en navegación y destinos. **Identificador del perfil** es la clave estable del contexto `callflow-profile-<id>`; permanece fijo al editar. Los perfiles anteriores sin display_name toman su identificador como nombre. Renombrar no cambia referencias IVR ni el contrato del handler.

**Destino al continuar** se usa al recibir una respuesta continue válida del handler. **Destino de contingencia** se usa si el handler falla, supera el presupuesto, devuelve una respuesta inválida o el perfil está deshabilitado; el wrapper lo establece antes de iniciar AGI. Un resultado route sólo puede elegir destinos aprobados. Estas explicaciones están en las ayudas del formulario.

## Eliminación, segundos e idioma

Al editar un perfil se muestra el número y la lista de objetos que usan su destino, con enlaces locales al editor. **Eliminar perfil** exige confirmar y enviar el formulario con sesión, ACL, CSRF y versión vigentes. Reconsulta las referencias al recibir POST: IVR, rutas y otros módulos PBX. La protección también escanea referencias internas del .conf; el validador actual rechaza rutas entre perfiles, por lo que una edición manual de ese tipo bloquea la configuración y la eliminación hasta corregirla. Esto no habilita encadenar perfiles. Si faltan o fallan las APIs de uso, la página sigue disponible y la eliminación queda bloqueada. Primero desvincular los objetos y aplicar cambios. Abrir un enlace o enviar GET nunca elimina un perfil.

Una eliminación correcta retira sólo el perfil y su Custom Destination legacy administrado, conserva los secretos/perfiles ajenos y marca Aplicar cambios; la regeneración deja de emitir su contexto. El borrador de otro perfil se conserva. La limpieza legacy se verifica antes del reemplazo atómico y versionado del .conf. Si éste falla, el perfil y su proveedor nativo de destino permanecen disponibles; puede haberse retirado una fila legacy redundante. Revisar el error, recargar y reintentar: no se anuncia éxito ni se restaura una copia con secretos ocultos.

**Límite del handler** y **Tiempo para ingresar dígitos** se editan en segundos. Sus defaults son 1 y 5; límites 0.05–5 y 0.1–15, respectivamente. Se aceptan hasta tres decimales, por ejemplo 0.05 y 1.5. Las claves web execution_budget_seconds/input_timeout_seconds se convierten exactamente a enteros execution_budget_ms/input_timeout_ms; el .conf, administrador JSON y AGI siguen usando milisegundos. No hay migración ni redondeo de los valores anteriores. Un error conserva el texto ingresado en el borrador sin credenciales.

**Destino de contingencia** (**Fail Over Destination** en inglés) recibe la llamada si el perfil está deshabilitado, el handler falla, excede su límite o devuelve una respuesta inválida. Por ejemplo, el administrador puede seleccionar una cola existente con operadores para resolver la contingencia. El núcleo no inventa una cola general. **Destino al continuar / Continue Destination** conserva la conducta continue del contrato.

La interfaz usa `modgettext::_($msgid, 'callflowhooks')`, siguiendo el idioma efectivo del shell PBX y su cookie lang. Los mensajes originales son ingleses y se distribuyen catálogos GNU compilados para es/es_ES/es_AR. No existe selector de idioma propio ni se fuerza el locale del servidor. Sin modgettext se usa el dominio gettext del locale activo, o inglés si gettext no está disponible. El RPM y archivo de módulo incluyen los .mo; la VM no necesita compilarlos. Cambiar idioma traduce etiquetas, ayudas y errores, pero conserva nombres escritos por el administrador, destinos, grabaciones, enums/IDs, secretos y el idioma/audio de la llamada.

Las pruebas PHP usan el selector externo de idioma como seam y leen los catálogos GNU reales (gettext cuando está disponible). La presentación efectiva del shell y la eliminación en la PBX instalada requieren la comprobación en VM.
