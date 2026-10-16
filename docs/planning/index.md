# Planificación de CallFlow Hooks

Las issues son canónicas. Este índice enlaza las entregas y sus relaciones sin duplicar sus cuerpos.

- [Mapa Wayfinder: CallFlow Hooks — addon extensible para Issabel](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/1).
- [Especificación: CallFlow Hooks — addon extensible para Issabel](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/2).
- [Acuerdos y aprobación de la descomposición](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/9).

## Estado

**Primera entrega autorizada y en revisión en [PR #30](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/pull/30).** Las demás entregas conservan sus dependencias y estado; la publicación de tickets no autoriza desplegar en producción.

## Entregas aprobadas

| Entrega | Bloqueado por |
|---|---|
| [Perfil genérico administrable desde Issabel](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/21) | — |
| [Afiliados CRM: consulta y selección de destino](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/22) | [Perfil genérico administrable desde Issabel](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/21) |
| [Atención en cola y acciones externas opcionales](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/23) | [Afiliados CRM: consulta y selección de destino](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/22) |
| [Aplicar cambios sin cruzar llamadas o usuarios](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/24) | [Atención en cola y acciones externas opcionales](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/23) |
| [Fallas y concurrencia de extensiones](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/25) | [Atención en cola y acciones externas opcionales](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/23) |
| [Otro rubro y segundo adaptador sin cambios del núcleo](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/26) | [Atención en cola y acciones externas opcionales](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/23) |
| [Addon completo en Issabel 4 y 5](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/27) | [Aplicar cambios sin cruzar llamadas o usuarios](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/24), [Fallas y concurrencia de extensiones](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/25), [Otro rubro y segundo adaptador sin cambios del núcleo](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/26), [Inventario de la PBX y de su entorno de prueba](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/4) |
| [Adaptador del CRM real y apertura de ficha](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/28) | [Atención en cola y acciones externas opcionales](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/23), [Capacidades de consulta y presentación de fichas del CRM](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/5) |
| [Aceptación completa y preparación de piloto](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/29) | [Addon completo en Issabel 4 y 5](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/27), [Adaptador del CRM real y apertura de ficha](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/28) |

Las dependencias nativas incluyen las condiciones externas que ya tienen ticket: inventario de laboratorio para instalación y capacidades del proveedor para CRM real. La entrega de proveedor necesita una PBX de pruebas y no espera a completar la validación de ambas combinaciones.

## Inicio después de autorización

La primera entrega es **Perfil genérico administrable desde Issabel**. Incluye formulario mínimo, configuración, registro automático de Custom Destination y un handler genérico comprobado con mocks. La verificación instalada y el proveedor real se certifican en sus entregas posteriores.

Después del hook de cola pueden avanzar cambios durante llamadas, matriz de fallas y segundo rubro/adaptador. El piloto sólo se prepara al completar las validaciones instaladas y del proveedor, con destinos, troncal, políticas y límites aprobados.

## Antecedentes sustituidos

Las entregas anteriores quedan archivadas como sustituidas, no completadas. Sus cuerpos, checks y comentarios conservan la evidencia del prototipo específico de Afiliados CRM; no certifican el addon genérico.

- [Primera llamada completa con CRM simulado](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/11).
- [Cambiar destinos y operadores desde configuración](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/12).
- [Continuar atención ante identificación o consulta fallida](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/13).
- [Derivar una obra social a un 0800](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/14).
- [Avisos aislados en llamadas simultáneas y ante fallas](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/15).
- [Instalar y conservar el flujo en Issabel 4 y 5](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/16).
- [Abrir la ficha en el CRM real](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/17).
- [Validar la versión completa y preparar piloto reversible](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/18).
- [Formulario de configuración en Issabel](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/19).

El [PR del prototipo Afiliados CRM](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/20) se conserva sin mergear como referencia. La primera entrega genérica se revisa en su propia rama.

## Relaciones

El manifiesto conserva las relaciones históricas y añade las nueve entregas activas como sub-issues de la especificación, con sus bloqueos aprobados. El workflow de planificación sincroniza esas relaciones nativas; los tickets históricos cerrados no forman parte de la frontera activa.

## Automatización de desarrollo

[OpenCode: tickets, pruebas y revisiones externas](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/31) está autorizado como preparación separada. Ver [activación y límites](../agents/opencode.md). No cambia los bloqueos ni la autorización de las entregas del addon.
