# Selectores de destinos y grabaciones

APIs verificadas en fuentes oficiales fijadas de IssabelPBX 2.11.0.49 y 2.12.0. El cliente informó 2.11.0-48; la fuente 49 es cercana, no prueba de esa RPM. La instalación efectiva sigue en laboratorio.

- `drawselects($goto, $index, false, false, '', $required)` genera los desplegables categoría/destino del IVR. Su séptimo argumento `true` devuelve el catálogo, que reutilizamos. POST usa `goto<index>` y `<categoría con espacios reemplazados por _><index>`. Se valida esa asociación contra el catálogo antes del backend.
- `pbxlib.js` enlaza `.destdropdown`/`.destdropdown2` y retira los hijos ocultos al enviar. CallFlow Hooks conserva esas clases e índices independientes.
- `recordings_list(false)` lista grabaciones simples; `recordings_get_file($id)` devuelve el nombre Asterisk. El ID de formulario se valida como decimal positivo antes de llamar al lookup, que en estas fuentes interpola el ID en SQL. El nombre resultante pasa además por la validación compartida de audio.
- La captura `GET DATA` admite el audio único que usa el núcleo actual. No se habilitan composiciones `a&b`. Se almacena el nombre relativo, no un ID que requeriría consulta PHP/PBX durante la llamada.
- El helper antiguo interpola tanto `$goto` como categorías, destinos y descripciones sin escape. Por eso no insertamos su HTML: renderizamos su catálogo con escape, las clases e índices de sus dos desplegables y su JavaScript nativo. Las claves de categoría ordinarias se conservan; las que contienen caracteres especiales o colisionan al reemplazar espacios por guiones bajos usan una clave CSS segura calculada desde su etiqueta y validada con el mismo mapa al guardar. Las entidades de descripción se decodifican antes de escapar. Desde 0.2.7 se conservan las entradas popover y se emiten data-url, data-class, data-mod y clases por módulo a partir de active_modules y drawselects_module_hash. PBX crea el destino y actualiza las opciones mediante closePopOver; una nueva solicitud valida el catálogo actualizado. Dentro de un popover no se ofrecen popovers anidados. Los borradores manuales también se muestran escapados.

No se copia el código de estos componentes al addon. Las pruebas simulan las APIs externas y ejecutan formulario, backend y AGI propios. No se certifica compatibilidad instalada por estas fuentes.

## Fuentes primarias

- [Helper destinos 2.11](https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/framework/amp_conf/htdocs/admin/helpers/issabelpbx_helpers.php).
- [JavaScript destinos 2.11](https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/framework/amp_conf/htdocs/admin/assets/js/pbxlib.js).
- [Grabaciones 2.11](https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/recordings/functions.inc.php).
- [Helper destinos 2.12](https://github.com/IssabelFoundation/issabelPBX/blob/0f77edaade296e929f2159f3165ceecc7f74b267/framework/amp_conf/htdocs/admin/helpers/issabelpbx_helpers.php).
- [Grabaciones 2.12](https://github.com/IssabelFoundation/issabelPBX/blob/0f77edaade296e929f2159f3165ceecc7f74b267/recordings/functions.inc.php).
- [Uso en IVR 2.12](https://github.com/IssabelFoundation/issabelPBX/blob/0f77edaade296e929f2159f3165ceecc7f74b267/ivr/functions.inc.php).

0.2.7 publica `callflowhooks_destinations`, `callflowhooks_getdestinfo` y `callflowhooks_check_destinations` con los contratos de los callbacks IVR. Los contextos existentes no cambian; las filas Custom Destinations anteriores se mantienen como compatibilidad. El adaptador web concentra esta dependencia PBX; el AGI sigue leyendo el .conf.

Los IDs de popover también se resuelven mediante `<módulo>_destination_popovers()`, incluyendo categorías vacías como Extensions/Users de core. El catálogo y metadata devuelven vacío ante un fallo del backend para preservar formularios ajenos; la pantalla propia muestra el diagnóstico y las comprobaciones de referencias fallan de forma cerrada. [Custom Destinations 2.11](https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/customappsreg/functions.inc.php) rechaza altas cuyo destino ya tiene propietario en `framework_identify_destinations`: un perfil cargado desde .conf se publica mediante el callback, sin intentar agregar una fila legacy duplicada. La desinstalación comprueba tanto perfiles de .conf como filas legacy.
