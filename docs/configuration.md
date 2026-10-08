# Perfiles y extensiones

El RPM 0.2.1 registra **PBX → CallFlow Hooks**, `/index.php?menu=callflowhooks`, con sesión, ACL y CSRF nativos de Issabel. La página de IssabelPBX sin embeber sigue disponible como acceso alternativo; el `.tgz` instala únicamente ese puente, no el módulo nativo. La integración instalada se comprobará en la VM según el [laboratorio](laboratory.md). Ambas pantallas guardan en `/etc/asterisk/callflow-hooks/profiles.conf`, la misma fuente que consume el AGI. El listado y el formulario ocultan los campos declarados `secret`; un valor vacío conserva la credencial anterior. Para borrarla expresamente, editar el .conf.

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

Los internos del ejemplo deben sustituirse por destinos existentes en la PBX. El núcleo verifica la sintaxis `contexto,extensión,prioridad` y rechaza expresiones/inyecciones y bucles directos entre perfiles; la existencia y conducta del destino requieren la prueba instalada. La contingencia puede igualar el siguiente destino. No se presupone ninguna cola general.

Guardar valida y reemplaza el archivo atómicamente, con modo 0600 y bloqueo entre escritores del addon. Si la versión del formulario quedó vieja, rechaza el guardado; recargar antes de continuar. Para edición manual, conservar permisos/propietario, validar antes de publicar y usar reemplazo atómico. Un editor externo que ignore el bloqueo puede competir con un guardado web; evitar ambos simultáneamente.

```bash
/usr/bin/python3 /usr/share/callflow-hooks/backend/entry.py admin <<'JSON'
{"action":"describe"}
JSON
```

`ok:true` confirma validación, y la respuesta no incluye secretos guardados. Después de crear perfiles manualmente, usar **Sincronizar destinos de .conf**, luego **Aplicar configuración**. Los perfiles creados desde el formulario registran automáticamente su Custom Destination. El administrador debe seleccionar **Custom Destinations → CallFlow Hooks: welcome** desde una opción del IVR habitual. La ruta entrante y el resto del IVR se administran normalmente.

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
