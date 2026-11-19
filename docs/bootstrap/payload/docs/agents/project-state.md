# Checkpoint verificado — 2026-10-12

Reconciliar con GitHub antes de actuar. Este archivo no autoriza trabajo adicional ni certifica la PBX.

| Área | Evidencia y estado |
|---|---|
| Control main | `4528057d497268a0e08d52b3e364702ab24657e0`; bootstrap #42 fusionado; árbol `72aeb59adb6ee4848d26fa551f29af2d907e87aa` idéntico al HEAD revisado |
| Base del addon | v0.2.8 = `bc2e0a7c675b2ffbd420a2652babcd7bca107e47`; base permitida avanzó a `90798e5749c06136d6b6e34991c2a40382dde668` con planificación `docs/bootstrap` únicamente |
| Plan/spec | mapa #1, spec #2; automatización #31; bootstrap #40 y primera frontera #41 |
| Trabajo actual | continuar #41 por OpenCode con evidencia durable; #40/#38 pausados |
| Último #38 | run 38256917004: failure/checks; 73 tests PASS, 1 FAIL, 2 skip |
| Candidato fallido | `a9d1b6394bdfb9194fc3ad269f2cd5a388478f11`, sólo local; sin PR remoto ni parche recuperable |
| Artifact | 11751170239, sólo result.json; no fuente recuperable ni Spec/Standards ejecutados |
| PR #39 | candidato de workspace fuera del flujo, referencia no aceptada; no release v0.2.9 |
| Intento amplio #40 | run 38263830613: failure/checks; 83 PASS, 1 FAIL, 3 ERROR, 2 skip; Spec/Standards no ejecutados |
| Fuente #40 | candidato `8c7939a1f84828bb314f75db3ef4088b322dfb96` no publicado; artifact 11754486120 verificado, sólo result.json, sin patch; no recuperación posible |
| Intento #41 | run 38265908134: review-failed tras 2 intentos; candidato local `19a44df4bbe0b5a6bd3e471e1a66ea1d30d10c55`; Spec FAIL + Standards FAIL |
| Evidencia #41 | artifact 11755469602, SHA256 `ba6ee476d21203bde031d43e710f4a32fe41d334d800dc32f3bf2f73825ea718`, sólo result.json; sin fuente/patch/informes; commit remoto 404, sin PR |
| Pruebas #41 | gates existentes del addon exitosos; discovery 76, sin evidencia de tests nuevos de recuperación; no aceptación del bootstrap |
| Recursos preparados | skills/configs/glosario/reglas en payload de bootstrap; todavía no instalados en sus rutas definitivas ni aceptados |
| CI de la planificación | runs 38263795094 y 38263786923 exitosos para `90798e5749c06136d6b6e34991c2a40382dde668`; no prueban implementación de #40 |
| VM | v0.2.8: el usuario confirmó idioma; otros pasos de telefonía/seguridad siguen pendientes |
| Roles aprobados | ChatGPT planifica/acepta; OpenCode implementa/revisa; merges uno por uno tras todos los gates |

## Siguiente frontera

Bootstrap #42 aceptado: HEAD `446db6fd183571e02ec84d9a7b11bf6a64a4bbef`, 41 tests locales PASS, Spec6130604382 PASS, Standards6130932011 PASS, CI38293819145 success, reviews38293819263 intento2 success. Excepción única del operador finalizada. No release/deploy del addon. Captura de cambios no comprometidos/recuperación integral y #41 completo siguen pendientes.

Continuar #41 por OpenCode después de #42: captura de cambios no comprometidos, recuperación/verificación integral y reviews del handoff publicado. Leer y reutilizar los controles aceptados de reference; el operador vuelve a planificación/publicación/aceptación, sin más código propio. #40/#38 y producción mantienen sus bloqueos. Los candidatos antiguos no se recuperan retrospectivamente.

## Brecha del legado

El legado publica PR después de checks/reviews, pierde fuente ante un check fallido y rechaza `.opencode`. El paquete `docs/bootstrap/` permite escribir cambios en rutas permitidas; requiere publicación confiable y revisiones finales antes del merge. No afirmar que la nueva automatización esté integrada mientras siga pendiente.

## Recuperación verificada — 2026-10-13

Run 38297335558 finalizó failure/checks, no timeout. Artifact11770232326 (82740 bytes), ZIP SHA256 f640051c47ba56250fb14b0aa32dfdd741f3ba0a25db7edcf831edffabf017d3, conserva dos candidatos y los reportes del primero.

Candidato final64c8e0a6f3464d30a3ff91100f70b77992815d3a recuperado sin cambios de implementación: 7 archivos completos, SHA256/Git blobs/modos verificados, sin exclusiones ni truncación. Base tree5c0d7d5078bf78d55d0e60279513bab0c448dc0a; patch aplicado en worktree aislado; recovered tree0ef5c15e888b8fb231d5dee367a3ab0653f35c14 coincide exactamente. Metadatos de commit nuevos; no afirmar mismo SHA original.

PR draft #43: https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/pull/43
HEAD e7465b5198d5aacc887bfc877602f27cf3d70dc8, base f6e7598044297bed2d8e533a16852d06d1a80695. Sin merge/release/deploy ni modificación del código del agente.

Tests nuevos reproducidos: 24 tests, 2 FAIL + 8 ERROR. ReviewCli omite mkdir docs (7 errores); RestoreCli clona dos veces al mismo destino (1 error); dos fallos de captura/restauración no comprometida. Run completo100 tests, 2 FAIL + 8 ERROR + 2 skip. Los reportes Spec/Standards FAIL son del primer SHA e750e45e18f9025ca1125b6ee8c40be5fb8b5d49; no revisan HEAD final. Standards sólo guardó marcador, no causas.

Bloqueo real antes de relanzar: approved_pr exige PR bot, rama feat/callflow-agent-issue-N y draft; el PR recuperado por el operador no cumple esos guards. No lanzar /agent-fix-cycle que sabemos rechazado ni /agent-ticket desde la base sin la fuente recuperada. La excepción de implementación del operador terminó con #42; no editar controles desde ChatGPT ni suplantar autor del bot.

Próxima frontera de planificación: habilitar una entrada de recuperación verificable para OpenCode (run/artifact/base/HEAD/tree y PR43 fijados), preservar ese PR y evitar ampliar permisos a PR arbitrarios. Sólo después OpenCode corrige fixtures/fallos y completa handoff/reviews de #41; no rehacer fuente desde logs. Registrar esta limitación como needs-info hasta disponer de esa ruta. #40/#38 siguen pausados.

## Frontera activa — 2026-10-13

Ticket #44 ready-for-agent: permitir continuación validada del PR recuperado #43 y revisión del handoff de controles. Sin bloqueadores; #41 queda needs-info/blocked-by #44; #40/#38 pausados. OpenCode implementa en staging aprobado; no se modificó su código ni los controles vivos. Plan y fuente recuperada verificados en GitHub; no aceptación ni despliegue de #43.

## Nuevo objetivo autorizado — 2026-10-16

Usuario elige Dynamic Routes + AGI independientes; ya no necesita addon para este caso. Spec #45 y ticket vertical #46, scripts/carpetas separados en tools/afiliados-crm-agi, PHP5.4+, mock CRM mientras llega contrato. Sólo documentación preparada por el operador; código y tests por OpenCode. #44 terminó failure/timeout run38404676319, candidato1ca4a9df30623ebf36f5bf7d4a7de647127ee127; no se relanza ni se presume pérdida/recuperación de sus artifacts sin inspección. #43/#41/#40/#38 permanecen sin aceptación y pausados; no borrar ni cerrar automáticamente. No hay ejecución activa al planificar. La aceptación final conserva gates/Standards/Spec/CI del HEAD publicado; legacy reviews auxiliares no bastan. No merge/release/deploy.

## Estado vigente — 2026-10-16, AGI standalone

El usuario confirmó puestos fijos y pidió pausar addon/bootstrap. Único objetivo actual: spec45/ticket46, Dynamic Routes + map fijo interno→usuarioCRM, sin dependencia de CallFlow Hooks. Cola6000 Local y QAGI confirmados por dialplan real; no agentes clásicos configurados.

Run38920481537 finalizó failure/timeout en review-standards: código sí generado, checks existentes completados, SpecFAIL por falta de tests nuevos/guía incompleta, Standards sin resultado. Artifact12055162925 verificado (SHA25671decd053c024b5aded8a386995c8ca0bcb459d2e306024290aac5278d979673); seis archivos completos, sin truncación/exclusiones. Recuperados sin edición como árbola6abcce83e92ae6292f6f1598b8323f9b05158a6, PR draft47, rama feat/afiliados-crm-agi, HEAD43b7dfb21bdd1485faa7772b30f1f586328967ad. Allí están los scripts reales en tools/afiliados-crm-agi, no en main ni en la base de planificación.

Pendientes: tests públicos de AGI/HTTP, completar guía, revisión de código y gates del HEAD final. No php-lint local (PHP ausente), validación PBX/CRM real, aceptación, merge, release ni despliegue. No confundir checks del addon con pruebas standalone. #44 marcado needs-info/pausado, junto con #38/#40/#41. No relanzar ni implementar esos tickets como requisito funcional del AGI. La limitación del guard bot impide /agent-fix-cycle directo del PR47; no se ejecutó un reintento conocido como inválido. Conservar fuente/PR y roles OpenCode implementación/review, operador publicación/aceptación.

## Continuación autorizada — 2026-10-16, controlador standalone acotado

PR47 aislado sobre main, mismos siete blobs, HEADed6a445a4f0773a4f4100a52f12416df9ca6275d; no arrastra addon y no cambia implementación. Se conserva el mismo PR. Main continúa4528057... . Usuario autorizó continuar tests/guía; el controlador actual exige PRbot/estructura addon y spec2 fija, por lo que no puede hacerlo todavía.

Frontera técnica #48, ready-for-agent/sin bloqueadores: generar por OpenCode un handoff mínimo que sólo habilite PR47 y sus gates/reviews standalone, preservando controles/bot fuera de esa excepción. Código únicamente en docs/bootstrap/generated/standalone-pr47/ y tests públicos aprobados. El operador publica/verifica/acepta; no modifica código ni relanza comandos que sabemos inválidos. #46 espera esta entrega; no necesita más datos para mocks. #44 y demás addon permanecen pausados; sin merge/release/deploy.

## Auditoría más reciente — 2026-10-16

#48 terminó failure/no-changes, stageimplement/attempt1 en run38925863812. Guards/setup correctos; sin candidato, tests ni revisiones. Artifact12056074471 verificado, SHA256c25836ae0720be081aa984013c0a1eef50cfd46cde7872b9f4e60117bd850db0, sólo result.json/summary.md sin explicación del implementador. No atribuir causa no observada. El enlace38925867362 era un run skipped de otro comentario y se corrigió en GitHub. #48 needs-info por diagnóstico insuficiente, sin reintento. PR47 sigue draft/main HEADed6a445a4f0773a4f4100a52f12416df9ca6275d; tests/guía de46 siguen pendientes. Addon pausado, sin aceptación/merge/deploy. Próxima reanudación debe preservar un informe breve de bloqueo/no-changes, sin transcripciones ni secretos.

## Contrato real recibido — 2026-11-19

El desarrollador entregó central.md con GET /api/central/preatendedor (opcion/cuil/llamada) y POST /api/central/llamada-atendida (formulario llamada/interno), ambos X-Api-Key y base/Atenciones. Spec45/ticket46 actualizados; contrato versionado y README aclarado en PR47 HEAD93fc2483e77f79af27d41d37bde7253b9a22db42. Sólo documentación: código todavía provisional, GET sin auth/id/obra_social y POSTJSON/Bearer no son compatibles con API real. No ejecución ni aceptación nueva.

Se elimina map interno→usuarioCRM: Atenciones resuelve operadora mediante Mi interno. Correlación exige UNIQUEID original≤40, mismo en reintentos y aviso, sin reemplazo por canales agente/Local. GET tiene presupuesto total3s y cualquier HTTP no200/schema inválido/timeout va al Call Center; QAGI también en esa contingencia. POST asincrónico formulario, sin CUIL/referencias/id afiliado ni agenteCRM; resultados200 OK/SIN_VALIDACION/SIN_OPERADOR y errores no alteran conversación. Referencias sólo memoria, no logs/CDR/jobs/vars de atención. Tabla de destino recibida se documenta como PROPUESTA del Call Center, pendiente de confirmación operativa; Portal es anuncio de URL y falta destino final, opción3 sinGET y falta destinoPBX.

#48 sigue needs-info por no-changes sin explicación; no se relanzó. Addon pausado. Pendientes externos: URLs/claves por canal seguro, IP origen/TLS, casos ficticios, confirmación reglas/opción3/Portal. Mocks pueden prepararse con contrato conocido. Tests/Spec/Standards/CI actuales y PBX real siguen sin aprobar; sin merge/release/deploy.

## Aclaración de alcance confirmada — 2026-11-19

El usuario corrigió la interpretación: el AGI sólo consulta Atenciones y devuelve prestadora; TODO el mapa prestadora→cola/destino vive en Dynamic Routes. No reglas de afiliación/titularidad/activo/proveedor/referencias/provincia, cortes o Portal en scripts/conf. CRM_ROUTE_KEY conserva el nombre exacto; si está ausente o falla consulta queda vacío y aplica Default del módulo (Call Center); si la prestadora no está mapeada, el AGI igual la devuelve y el módulo usa Default.

Spec45/ticket46 y contrato/README corregidos en PR47 HEAD592bc4ba1ae123538680488266779de804d02c48, sólo documentación. Se mantiene GETopcion/cuil/llamada con X-Api-Key, timeout3s, UNIQUEID original y POSTformulario sólo llamada/interno. Mi interno de Atenciones resuelve usuario; sin mapCRM. Una única ruta puede recibir IVR1/2 y pasar IVR_DIGIT_PRESSED (confirmada en fuente2.11, verificar instalación), sin duplicar mapa. Código y tests siguen pendientes; #48 bloqueado, addon pausado; sin ejecución, aceptación, merge o despliegue.

## Corrección implementada — 2026-11-19, PR47

La aclaración final del usuario sustituye el alcance raw-only anterior: AGI evalúa las reglas para devolver un valor; Dynamic Routes mantiene el mapa valor→destino y ejecuta el control de llamada. CRM_ROUTE_KEY = CALL_CENTER / PORTAL / INVALID_CUIL / END_CALL. CRM_PRESTADORA adicional conserva el nombre literal para optar por un mapa por afiliación. No Goto/Queue/Hangup/Playback dentro de scripts.

Spec45/ticket46 reconciliados. Por el pedido actual de crear/corregir ahora, se realizó implementación directa acotada y se dejó constancia en #46 comentario7022433543; no se atribuye ese código a OpenCode. PR47 HEAD 9ae684dd5722b8660a2384e9c10dceb215c01a40, árbol b576e57c5a5d07e532b5ca8f09fc081d2b38e307 comprobado igual al worktree probado. Contrato real X-Api-Key/GET con opcion-cuil-llamada/POST formulario llamada-interno, correlación original, QAGI y worker asíncrono. Config/mock/guía actualizados. Addon y controlador48 siguen pausados, sin modificar guards.

Verificación local: 24 tests públicos PHP8.4+cURL/AGI/HTTP PASS, php-lint4 PASS; TLS CA/hostname, reglas/orden, fallos3s, POST no bloqueante, privacidad y mock. Nueva validación CI standalone PHP5.4/8.4 y revisiones OpenCode independientes con controles/modelos/perfiles aprobados y SHA exacto. Aún pendientes al publicar este checkpoint; no se presume aprobación. No instalación PBX, integración CRM real, aceptación, merge, release ni deploy. Pendientes externos: URL/clave testing, certificado/IP, destinos/audioPortal, menú aislado y aviso a operadora.

### Gates del HEAD 9ae684dd5722b8660a2384e9c10dceb215c01a40

Run44621548471: tests PHP5.4.45 y PHP8.4 SUCCESS, 24 pruebas públicas en cada versión y php-lint4 PASS. Spec terminó failure/command-failed sin informe; artifact14577003991 (240 bytes), logs inspeccionados, no asumir causa ni aprobación. Standards aún en curso al registrar. No reintento ciego, no aceptación/merge/deploy. Implementación ya publicada en PR47, no confundir este bloqueo de revisión con ausencia de scripts.

## Frontera corregida — 19/11/2026: decisión y prestadora en una salida

Usuario aclara que atender implica cola específica por prestadora, conservando filtros. Spec45/ticket46 actualizados: CRM_ROUTE_KEY devuelve primero INVALID_CUIL/END_CALL/PORTAL; sólo cuando corresponde atención devuelve PRESTADORA:<nombre literal> si existe, o CALL_CENTER si falta/falla API. Matches a colas permanecen en Dynamic Routes; prefijo evita colisión con claves reservadas. Dos rutas nativas con argumentos1/2, mismo AGI. CRM_PRESTADORA auxiliar no es selector principal. HEAD9ae684d todavía no implementa esa combinación; no afirmar lo contrario. Corrección por OpenCode pendiente según roles. Run44621548471 finalizó failure: tests5.4/8.4 SUCCESS, Spec y Standards fallaron ejecución, sin aceptación. No reintento a ciegas ni cambios nuevos de implementación/guards/secretos; addon pausado, sin merge/deploy.

### Salida literal confirmada por el usuario

Se descarta expresamente el prefijo PRESTADORA:. Cuando corresponde atender, CRM_ROUTE_KEY debe devolver el nombre literal de prestadora recibido, por ejemplo Osde; Dynamic Routes mapea Osde→cola. Preservar case/espacios/acentos. Claves de rechazo/Portal prevalecen; sin prestadora/fallo→CALL_CENTER. Spec45/ticket46 corregidos. Implementación combinada todavía pendiente; no hubo ejecución ni cambios de código por esta decisión.

## Corrección publicada y decisión confirmada — 19/11/2026

Usuario confirma rechazo del titular de baja en opción2 y solución final AGI+Dynamic Routes sin continuar plugin para este caso. PR47 HEAD b29f179279627923c0ee7420a54fcc384bc79084, árbol 84ee1a01342f4fa6054622e1e5cda18cd0cafefe comprobado igual al worktree probado. CRM_ROUTE_KEY devuelve prestadora literal (Osde) sólo si corresponde atención; políticas de Portal/rechazo prevalecen; sin prestadora/fallo→CALL_CENTER. README/contrato con dos Dynamic Routes, argumentos1/2 al mismo script y una variable de resultado. Notificación Queue sin cambios.

TDD público RED→GREEN de Osde, suite26 PHP8.4+cURL+AGI/HTTP PASS (17.155s), php-lint PASS. CI es validación de desarrollo, no dependencia de ejecución ni instalación en Issabel. Esta corrección no cambia workflows/guards/modelos/secretos. Validación del HEAD nuevo pendiente al publicar. Run anterior44621548471: tests5.4/8.4 SUCCESS; Spec command-failed y Standards model-no-text, sin informes aprobados. No se reintentó ese run. Sin aceptación manual, merge ni deploy. Próximo paso funcional: VM/menú aislado y Atenciones testing.
