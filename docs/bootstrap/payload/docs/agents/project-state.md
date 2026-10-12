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
