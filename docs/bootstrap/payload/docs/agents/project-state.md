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
