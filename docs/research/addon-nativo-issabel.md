# Registro nativo de un addon en Issabel 4 y 5

Investigación del 2026-10-08, a partir de fuentes de Issabel Foundation. Esta nota describe mecanismos e hipótesis; no cambia por sí sola el alcance aprobado ni certifica las imágenes instaladas.

## Evidencia de laboratorio aportada por el usuario

- VM Issabel 4, Python 3.6.8 y Python 2.7.5 coexistentes.
- `module_admin list` registra `callflowhooks 0.1.0 Enabled`.
- La página `/admin/config.php?display=callflowhooks` aparece en IssabelPBX sin embeber.
- No aparece en el menú de Configuración PBX embebido de Issabel.

Esto permite descartar que el módulo esté ausente o sin registrar en IssabelPBX. No comprueba todavía ejecución AGI, escritura de perfiles, generación de destinos ni llamadas.

## Hay dos registros diferentes

| Capa | Archivos y registro | Página y permisos |
|---|---|---|
| Módulo IssabelPBX | `/var/www/html/admin/modules/<nombre>/`, `module.xml`, `module_admin` | `/admin/config.php?display=<nombre>`; secciones del administrador PBX |
| Módulo nativo Issabel | `/var/www/html/modules/<nombre>/index.php`, `menu.xml`, `issabel-menumerge` | `/index.php?menu=<nombre>`; recurso y permisos del framework Issabel |

La capa nativa incluye `index.php` y llama a `_moduleContent(&$smarty, $module_name)`. Puede cargar bibliotecas, traducciones y plantillas/activos del tema del módulo. El framework autentica al usuario y verifica el permiso `access` del recurso seleccionado antes de mostrar el contenido. Esto existe en las ramas oficiales 4.0 y en el código actual de la serie 5. [S1, S2, S3]

El paquete CallFlow Hooks 0.1.0 contiene la primera estructura, no la segunda: su `module.xml` registra un menú PBX y no incluye `menu.xml` de Issabel ni el punto de entrada `_moduleContent`. El hecho de verse sin embeber es consistente con ese empaquetado. [Código local: `module/module.xml`, `module/page.callflowhooks.php`, `tools/build.py`]

## Por qué puede faltar en el menú PBX embebido

El wrapper oficial de Issabel 4 refresca la lista de módulos PBX, consulta `module_xml`/`mod_serialized` y sólo recorre módulos que declaran **`embedcategory`**. Luego comprueba el estado habilitado y el privilegio PBX correspondiente del usuario. El `category` usado por el menú independiente no sustituye a `embedcategory`. [S4]

CallFlow Hooks 0.1.0 declara `<category>Applications</category>` pero no `<embedcategory>…</embedcategory>`. La omisión explica la invisibilidad si la VM usa el wrapper observado. Es una hipótesis fuerte, todavía pendiente de verificar contra el archivo instalado en esa VM; también deben comprobarse sus privilegios. El comportamiento ya está presente en una fuente oficial de noviembre de 2019, no sólo en la rama posterior. El IVR oficial ilustra ambos atributos diferentes. [S4, S5, S6]

Agregar `embedcategory` y actualizar el registro PBX sería una posible corrección de visibilidad embebida. **Seguiría siendo un módulo IssabelPBX**, no una administración nativa de Issabel. No debe presentarse como cumplimiento de la intención aclarada por el usuario.

## Registro nativo y empaquetado

El comando oficial `/usr/bin/issabel-menumerge` recibe un documento XML con raíz `module`, `menulist` y `menuitem`. Lee atributos `menuid`, `parent`, `desc`, `module`, `link`, `order` y `type`, además de grupos/permisos y privilegios. Actualiza o crea el menú mediante `paloMenu` y el recurso ACL mediante `Installer`. La ruta del módulo nativo debe existir previamente. [S7]

El módulo PBX oficial usa `pbxconfig` como padre del menú PBX. En Issabel 4, `pbxadmin` es un módulo nativo (`module="yes"`); en la serie 5 pasa a ser una entrada con enlace `/admin/`. Para una entrada propia CallFlow Hooks bajo PBX, el candidato es un `menuitem` propio con `parent="pbxconfig"`, `module="yes"`, `link=""`, y un `index.php` nativo independiente del wrapper PBX. Esta es una recomendación técnica, no una decisión nueva de alcance. [S8, S9]

El empaquetado RPM oficial coloca instaladores y `menu.xml` bajo `/usr/share/issabel/module_installer/<paquete-versión-release>/`, instala las páginas bajo `/var/www/html/modules/`, y llama a `issabel-menumerge` durante instalación/actualización. El framework instala además `issabel-menuremove` para retirar entradas y recursos. Por tanto un addon nativo puede empaquetarse como RPM con instalación, actualización y desinstalación explícitas; la disponibilidad comercial de un catálogo de Addons no es un requisito de este registro. [S10, S11]

La implementación examinada concede por defecto el recurso nuevo al grupo administrador, con fallback histórico al identificador 1. XML puede declarar grupos explícitos. En actualización, `updateResourceMembership` crea/actualiza el recurso pero no reescribe los permisos de los grupos: el instalador debe conservar las decisiones ACL existentes y comprobar su resultado. No conviene resolver visibilidad otorgando permisos globales. [S7, S12]

Una página nativa debe usar la sesión y ACL Issabel y mantener protección CSRF en las operaciones de escritura; no basta con reutilizar el guard `ISSABELPBX_IS_AUTH` de la página PBX. Los formularios y servicios de configuración existentes pueden reutilizarse detrás de un nuevo punto de entrada con autenticación correcta. La protección CSRF y el diseño del puente PBX son requisitos propuestos para la corrección, no funcionalidades verificadas aquí. [S2, S3; inferencia de integración]

## Issabel 5 sigue utilizando IssabelPBX

La especificación RPM oficial `issabel-pbx.spec` declara `Version: 5.0.0` y `Requires(pre): issabelPBX >= 2.12.0`. El paquete PBX separado se llama `issabelPBX`, declara versión 2.12.0 e instala mediante su propio framework. El cambio de 2023 hizo que la integración exterior abra `/admin/` en un frame en lugar de usar el módulo embebido anterior. [S9, S10, S13]

El código de autenticación exterior de la serie 5 reutiliza sesión/ACL Issabel para IssabelPBX; al otorgar secciones vuelve a seleccionar módulos con `embedcategory`. La serie 5 conserva integración con el proyecto **IssabelPBX**, derivado del framework FreePBX, pero estos datos no prueban compatibilidad con versiones arbitrarias de FreePBX upstream. [S14]

No se inspeccionó la imagen Issabel 5 del 20261001 ni sus RPM instalados. Las ramas 4.0 examinadas declaran `issabel-pbx 4.0.0-8` y `issabel-framework 4.0.0-13`, diferentes de los RPM 4.0.0-6 y 4.0.0-10 comunicados por el cliente. La evidencia histórica respalda el mecanismo, pero el contenido exacto de esos RPM y los permisos efectivos requieren validación local.

## Consecuencia técnica candidata

Conservar el núcleo Python, contrato JSON, perfiles `.conf` y AGI. Agregar una administración verdaderamente nativa de Issabel, con registro de menú/ACL y empaquetado propio. Mantener el módulo IssabelPBX como puente para generar dialplan y registrar destinos, si se confirma esa distribución de responsabilidades. No es necesario sustituir el IVR ni modificar el wrapper de Issabel; agregar sólo un enlace al formulario PBX sería una solución de acceso, no una administración nativa completa.

## Fuentes primarias fijadas

- [S1 — Cargador nativo Issabel 4, `paloSantoNavigation.class.php`](https://github.com/IssabelFoundation/framework/blob/a3f73d29b48b50be97e899b7cafc88a115b775ac/framework/html/libs/paloSantoNavigation.class.php)
- [S2 — Autenticación/autorización exterior Issabel 4, `index.php`](https://github.com/IssabelFoundation/framework/blob/a3f73d29b48b50be97e899b7cafc88a115b775ac/framework/html/index.php)
- [S3 — Cargador actual del framework, `paloSantoNavigation.class.php`](https://github.com/IssabelFoundation/framework/blob/8f0a6f3045cf1608d294036b77aa5e0f3c66cabc/framework/html/libs/paloSantoNavigation.class.php)
- [S4 — Wrapper Issabel 4, `contentIssabelPBX.php`](https://github.com/IssabelFoundation/pbx/blob/1595c329f270fb04b8502ed75fdd8148b0d75d5b/modules/pbxadmin/libs/contentIssabelPBX.php)
- [S5 — Wrapper histórico de noviembre de 2019](https://github.com/IssabelFoundation/pbx/blob/ec31ff743786a89bcee546953af0225b59c8c9b9/modules/pbxadmin/libs/contentIssabelPBX.php)
- [S6 — IVR oficial: `category` y `embedcategory`](https://github.com/IssabelFoundation/issabelPBX/blob/0f77edaade296e929f2159f3165ceecc7f74b267/ivr/module.xml)
- [S7 — `issabel-menumerge`, rama 4.0](https://github.com/IssabelFoundation/framework/blob/a3f73d29b48b50be97e899b7cafc88a115b775ac/additionals/usr/bin/issabel-menumerge)
- [S8 — Menú PBX Issabel 4](https://github.com/IssabelFoundation/pbx/blob/1595c329f270fb04b8502ed75fdd8148b0d75d5b/menu.xml)
- [S9 — Cambio de integración a frame y versión 5](https://github.com/IssabelFoundation/pbx/commit/97b7ddfc96c21e583ce66812c8a54bcc508396f8)
- [S10 — RPM `issabel-pbx`, serie 5](https://github.com/IssabelFoundation/pbx/blob/253809d17e137987aa69729ce5af1e5b7e0ce937/issabel-pbx.spec)
- [S11 — RPM `issabel-framework`, serie 5](https://github.com/IssabelFoundation/framework/blob/8f0a6f3045cf1608d294036b77aa5e0f3c66cabc/issabel-framework.spec)
- [S12 — Registro de menú y permisos en `Installer`, rama 4.0](https://github.com/IssabelFoundation/framework/blob/a3f73d29b48b50be97e899b7cafc88a115b775ac/framework/html/libs/paloSantoInstaller.class.php)
- [S13 — Paquete oficial `issabelPBX` 2.12.0](https://github.com/IssabelFoundation/issabelPBX/blob/0f77edaade296e929f2159f3165ceecc7f74b267/issabelPBX.spec)
- [S14 — Autenticación Issabel para IssabelPBX, serie 5](https://github.com/IssabelFoundation/pbx/blob/253809d17e137987aa69729ce5af1e5b7e0ce937/setup/var/www/html/admin/issabel_issabelpbx_auth.php)
