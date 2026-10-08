# Planificación de la integración

Las issues son canónicas. Este documento permite navegar sin duplicar sus cuerpos.

- [Mapa Wayfinder: integración IVR y colas Issabel ↔ CRM](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/1).
- [Especificación: integración IVR y colas Issabel ↔ CRM](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/2).

## Implementación

| Entrega | Bloqueado por | Alcance |
|---|---|---|
| [Primera llamada completa con CRM simulado](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/11) | — | Primera versión |
| [Cambiar destinos y operadores desde configuración](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/12) | [Primera llamada completa con CRM simulado](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/11) | Primera versión |
| [Continuar atención ante identificación o consulta fallida](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/13) | [Cambiar destinos y operadores desde configuración](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/12) | Primera versión |
| [Derivar una obra social a un 0800](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/14) | [Cambiar destinos y operadores desde configuración](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/12) | Primera versión |
| [Avisos aislados en llamadas simultáneas y ante fallas](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/15) | [Cambiar destinos y operadores desde configuración](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/12) | Primera versión |
| [Instalar y conservar el flujo en Issabel 4 y 5](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/16) | [Cambiar destinos y operadores desde configuración](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/12) | Primera versión |
| [Abrir la ficha en el CRM real](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/17) | [Cambiar destinos y operadores desde configuración](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/12) | Primera versión |
| [Validar la versión completa y preparar piloto reversible](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/18) | [Continuar atención ante identificación o consulta fallida](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/13), [Derivar una obra social a un 0800](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/14), [Avisos aislados en llamadas simultáneas y ante fallas](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/15), [Instalar y conservar el flujo en Issabel 4 y 5](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/16), [Abrir la ficha en el CRM real](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/17) | Primera versión |
| [Formulario de configuración en Issabel](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/19) | [Cambiar destinos y operadores desde configuración](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/12), [Instalar y conservar el flujo en Issabel 4 y 5](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/16) | Opcional |

## Inicio y pendientes

La primera entrega es **Primera llamada completa con CRM simulado**. Requiere PBX de laboratorio y acceso de configuración; aún no se proporcionaron. Los valores operativos de mapas se cargan al implementar. El contrato real del CRM bloquea su integración real y el piloto, pero permite desarrollar contra el simulador.

Políticas no aprobadas y límites pendientes permanecen explícitos en la especificación y en las entregas correspondientes. No se habilita producción durante esta migración.
