# Evidencia y límites de la entrega

La primera versión se desarrolla por autorización del usuario con mocks, sin acceso a la PBX. Las pruebas ejecutan los programas reales como procesos y hablan por stdin/stdout con un doble del protocolo Asterisk; el CRM es un servidor HTTP real sobre loopback. No se reemplazan los colaboradores internos del addon.

Fronteras verificadas: identificación/enrutamiento por AGI, aviso de Queue por AGI, GET/POST, configuración y CLI de instalación/aplicación/desinstalación. Respuestas AGI incluyen `endpos` de GET OPTION/STREAM FILE según `res_agi.c` de Asterisk 18.

Cobertura: ruta reconocida, terminador configurable, checksum/inválidos, no encontrado, JSON/error/tamaño, obra ambigua/sin mapa, transferencia HTTP lenta con deadline total, datos previos borrados, afiliado reconocido en general, reasignación de mapa durante espera, autenticación, rechazo de conexión, error HTTP de aviso, miembro Local exacto sin interno inventado, mapa actualizado, aviso lento sin pipes heredados, timeout con slot liberado, saturación, runtime ausente, identidades de llamadas simultáneas del mismo y distintos afiliados, instalación idempotente, rechazo de candidato y conservación de dialplan ajeno y normalización de permisos de secretos. También se prueba el contrato público del mock y su inbox por usuario.

El test de aviso lento exige EOF del AGI antes de 0,8 s mientras el receptor demora 1,5 s. Es un umbral de prueba con margen para el runner, **no** un SLA aprobado de audio. El GET de transferencia lenta tiene presupuesto de 0,25 s y margen de proceso total inferior a 0,8 s. Medir en la VM los límites que se usarán en servicio.

## No demostrado por mocks

- Audio real, ofertas sin respuesta emitidas por Queue, timing del bridge y paquetes/hook efectivos de Issabel 4/5.
- Persistencia y convivencia con grabación/anuncios tras regeneración real de Issabel, SELinux y mecanismos reales de login.
- Marcación 0800, permisos/CallerID y respuesta de la troncal.
- Contrato del proveedor y apertura de la ficha en su frontend.
- Políticas/límites aprobados para piloto y rendimiento bajo carga de producción.

Los tickets que requieren estas observaciones permanecen abiertos. El formulario web y DNI siguen fuera del alcance inicial. No interpretar una suite verde o un RPM construido como certificación de PBX.

## Reproducir

```sh
python3 -m unittest discover -v
python3 -m compileall -q issabel_crm tools lab
python3 tools/build.py
```

CI repite tests en Python 3.9/3.12 y en un contenedor Python 3.6.15; después construye tarball y RPM. Ver el resultado efectivo del run antes de descargar sus artifacts. La guía de VirtualBox establece la siguiente etapa de evidencia.

## Fuentes de protocolo y hooks

- https://github.com/asterisk/asterisk/blob/18/res/res_agi.c
- https://github.com/asterisk/asterisk/blob/16/apps/app_queue.c
- https://github.com/asterisk/asterisk/blob/18/apps/app_queue.c
- https://github.com/asterisk/asterisk/blob/18/configs/samples/queues.conf.sample
- https://github.com/IssabelFoundation/issabelPBX/blob/master/queues/functions.inc/dialplan.php
