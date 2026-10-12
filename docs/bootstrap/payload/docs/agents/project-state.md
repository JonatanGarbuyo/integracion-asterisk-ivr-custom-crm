# Checkpoint verificado — 2026-10-12

Reconciliar con GitHub antes de actuar. Este archivo no autoriza trabajo adicional ni certifica la PBX.

| Área | Evidencia y estado |
|---|---|
| Control main | `db138b2c3bd14c61313d3a1dd0beb17a2306089d`; orquestación legado |
| Base del addon | `feat/callflow-generic-profile`, `bc2e0a7c675b2ffbd420a2652babcd7bca107e47`, tag v0.2.8 |
| Plan/spec | mapa #1, spec #2; automatización #31; bootstrap #40 |
| Trabajo actual | #40: completar flujo, skills y evidencia recuperable; #38 pausado |
| Último #38 | run 38256917004: failure/checks; 73 tests PASS, 1 FAIL, 2 skip |
| Candidato fallido | `a9d1b6394bdfb9194fc3ad269f2cd5a388478f11`, sólo local; sin PR remoto ni parche recuperable |
| Artifact | 11751170239, sólo result.json; no fuente recuperable ni Spec/Standards ejecutados |
| PR #39 | candidato de workspace fuera del flujo, referencia no aceptada; no release v0.2.9 |
| VM | v0.2.8: el usuario confirmó idioma; otros pasos de telefonía/seguridad siguen pendientes |
| Roles aprobados | ChatGPT planifica/acepta; OpenCode implementa/revisa; merges uno por uno tras todos los gates |

## Siguiente frontera

Completar #40 por OpenCode y handoff, verificar revisiones y CI del HEAD final y mergear únicamente tras aceptación. Luego reanudar #38 desde el PR generado por Actions. #22/#23 y producción no se habilitan por completar el bootstrap.

## Brecha del legado

El legado publica PR después de checks/reviews, pierde fuente ante un check fallido y rechaza `.opencode`. El paquete `docs/bootstrap/` permite escribir cambios en rutas permitidas; requiere publicación confiable y revisiones finales antes del merge. No afirmar que la nueva automatización esté integrada mientras siga pendiente.
