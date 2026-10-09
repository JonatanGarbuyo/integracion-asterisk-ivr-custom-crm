# Selectores de destinos y grabaciones

APIs verificadas en fuentes oficiales fijadas de IssabelPBX 2.11.0.49 y 2.12.0. El cliente informó 2.11.0-48; la fuente 49 es cercana, no prueba de esa RPM. La instalación efectiva sigue en laboratorio.

- `drawselects($goto, $index, false, false, '', $required)` genera los desplegables categoría/destino del IVR. Su séptimo argumento `true` devuelve el catálogo, que reutilizamos. POST usa `goto<index>` y `<categoría con espacios reemplazados por _><index>`. Se valida esa asociación contra el catálogo antes del backend.
- `pbxlib.js` enlaza `.destdropdown`/`.destdropdown2` y retira los hijos ocultos al enviar. CallFlow Hooks conserva esas clases e índices independientes, y añade sólo la elección catálogo/manual.
- `recordings_list(false)` lista grabaciones simples; `recordings_get_file($id)` devuelve el nombre Asterisk. El ID de formulario se valida como decimal positivo antes de llamar al lookup, que en estas fuentes interpola el ID en SQL. El nombre resultante pasa además por la validación compartida de audio.
- La captura `GET DATA` admite el audio único que usa el núcleo actual. No se habilitan composiciones `a&b`. Se almacena el nombre relativo, no un ID que requeriría consulta PHP/PBX durante la llamada.
- El helper antiguo interpola tanto `$goto` como categorías, destinos y descripciones sin escape. Por eso no insertamos su HTML: renderizamos su catálogo con escape, las clases e índices de sus dos desplegables y su JavaScript nativo. Las claves de categoría ordinarias se conservan; las que contienen caracteres especiales o colisionan al reemplazar espacios por guiones bajos usan una clave CSS segura calculada desde su etiqueta y validada con el mismo mapa al guardar. Las entidades de descripción se decodifican antes de escapar. Se seleccionan destinos existentes; no se ofrecen popovers para crearlos. Los borradores manuales también se muestran escapados.

No se copia el código de estos componentes al addon. Las pruebas simulan las APIs externas y ejecutan formulario, backend y AGI propios. No se certifica compatibilidad instalada por estas fuentes.

## Fuentes primarias

- [Helper destinos 2.11](https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/framework/amp_conf/htdocs/admin/helpers/issabelpbx_helpers.php).
- [JavaScript destinos 2.11](https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/framework/amp_conf/htdocs/admin/assets/js/pbxlib.js).
- [Grabaciones 2.11](https://github.com/IssabelFoundation/issabelPBX/blob/27a09b06dca6f6649322edbacc83e6e49ac14fa4/recordings/functions.inc.php).
- [Helper destinos 2.12](https://github.com/IssabelFoundation/issabelPBX/blob/0f77edaade296e929f2159f3165ceecc7f74b267/framework/amp_conf/htdocs/admin/helpers/issabelpbx_helpers.php).
- [Grabaciones 2.12](https://github.com/IssabelFoundation/issabelPBX/blob/0f77edaade296e929f2159f3165ceecc7f74b267/recordings/functions.inc.php).
- [Uso en IVR 2.12](https://github.com/IssabelFoundation/issabelPBX/blob/0f77edaade296e929f2159f3165ceecc7f74b267/ivr/functions.inc.php).
