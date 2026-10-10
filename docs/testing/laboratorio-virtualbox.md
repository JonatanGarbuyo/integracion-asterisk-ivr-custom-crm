# Instalar y validar el addon en VirtualBox

El desarrollo y las pruebas automáticas funcionan sin una PBX. Esta etapa verifica aquello que un doble no demuestra: hook instalado, audio, miembros reales, rutas salientes y persistencia después de aplicar configuración. Comenzar en Issabel 5/Asterisk 18 y repetir en Issabel 4/Asterisk 16.

## Máquina y red

Asignación inicial sugerida: 2 vCPU, 4 GiB de RAM y 40 GiB de disco. Instalar la ISO y tomar un snapshot antes del addon. No se necesita troncal para IVR/colas; el 0800 real se prueba posteriormente con una ruta autorizada.

Red sencilla: adaptador 1 NAT para repositorios y adaptador 2 sólo-anfitrión para softphones, HTTP/SSH y CRM del anfitrión. Configurar IPs en la misma subred. Los softphones en el anfitrión alcanzan la IP de la VM; la VM alcanza la IP del anfitrión, no `127.0.0.1`. Un teléfono físico requiere una red alcanzable adicional, por ejemplo puente en Ethernet. El problema previo de VirtualBox con Secure Boot debe resolverse en el anfitrión antes de iniciar la VM; es independiente del addon.

Registrar inventario antes de instalar:

```sh
cat /etc/os-release
asterisk -rx 'core show version'
python3 --version
rpm -qa | sort | rg -i 'issabel|asterisk|python3'
asterisk -rx 'core show application AGI'
asterisk -rx 'core show application Queue'
asterisk -rx 'dialplan show ext-queues'
```

Si `rg` no está instalado, usar `grep -Ei` para el inventario. Se requiere Python **3.6 o posterior**, la cuenta/grupo `asterisk` y AGI/Queue. Resolver el runtime antes de instalar si la imagen no lo incluye; Python 2 no sirve. No se declara compatibilidad instalada a partir del número de ISO.

## CRM simulado

En el anfitrión, desde el checkout:

```sh
python3 -m lab.mock_crm --host 0.0.0.0 --port 8080
```

Usar la IP del adaptador sólo-anfitrión en `lookup_url` y `notify_url` de la VM. Abrir en el anfitrión `http://127.0.0.1:8080/` y elegir `crm-user-a` o `crm-user-b` para observar fichas ficticias.

| CUIL ficticio | Afiliado | Obra | Destino de ejemplo |
|---|---|---|---|
| 20123456786 | af-demo-1 | OS_A | cola 601 |
| 27234567891 | af-demo-2 | OS_B | cola 602 |
| 20345678906 | af-demo-external | OS_EXTERNAL | 08001234567; reemplazar antes de llamar |
| 20456789014 | af-demo-ambiguous | dos obras | general |
| 20567890121 | af-demo-unmapped | sin mapa | general |

Todos pasan el dígito de control de los fixtures. Su carácter ficticio se refiere al uso de prueba; no consultar estos valores contra un padrón real.

Opciones para inyectar fallas: `--lookup-delay 5`, `--lookup-status 500`, `--notify-delay 10`, `--notify-status 503`, `--trickle-interval 0.1`. Reiniciar el mock con la opción elegida. Opcionalmente, `MOCK_CRM_TOKEN` exige el mismo bearer en los endpoints; en ese modo inspeccionar con un cliente autenticado, ya que el dashboard no administra tokens. Los avisos viven en memoria (máximo 500), sin persistencia entre reinicios.

## Instalación

Desde el checkout o tarball extraído en la VM:

```sh
sudo python3 tools/addon.py install
sudo cp /etc/asterisk/issabel_crm.conf /etc/asterisk/issabel_crm.local.conf
# Editar el candidato: IP del CRM, colas, miembros y datos de conexión.
sudo python3 /usr/lib/issabel-crm/addon.py validate --config /etc/asterisk/issabel_crm.local.conf
sudo python3 /usr/lib/issabel-crm/addon.py apply --config /etc/asterisk/issabel_crm.local.conf
```

El instalador conserva los `.conf` existentes y agrega sólo un bloque identificado con `#include issabel_crm_extensions.conf` a `extensions_custom.conf`. No cambia `extensions_additional.conf`, definiciones generadas de cola, troncales ni base de datos de Issabel. No crea colas, internos ni una entrada de menú web. El addon inicial es un paquete de backend con destino custom; el formulario sigue en el ticket opcional.

La receta RPM está en `packaging/issabel-crm.spec`; CI construye el RPM y tarball. En un checkout local, `python3 tools/build.py` genera `dist/issabel-crm-0.1.1.tar.gz` y checksum. Si se instala RPM, administrarlo siempre con RPM: su script postinstalación agrega el mismo include y permisos. No mezclar la desinstalación manual con una instalación administrada por RPM.

### Preparar Issabel

1. Crear internos de prueba, una cola general 600 y colas 601/602. Agregar los miembros y mapear **la interfaz exacta observada**, por ejemplo `SIP/1001`, `PJSIP/1001`, `Local/1002@from-queue/n` o `Agent/1003`. Que una cadena figure como ejemplo no certifica el mecanismo de login del Call Center.
2. Grabar/subir el audio de ingreso como `custom/enter-cuil`. Indicar 11 dígitos y `#`, o el terminador configurado (`*` también admitido). Comprobar que la ruta de sonido exista en el idioma del canal. Los defaults (dos intentos, checksum, timeout y fallback general) son **propuestas de laboratorio**, pendientes de acordar para producción.
3. Verificar que el dialplan instalado de `ext-queues` consuma `VQ_AGI`/`QAGI` y pase el AGI a `Queue()`. Si el paquete no lo hace, detener la habilitación del flujo e inventariar el punto custom compatible. No sustituir todo `Queue()` ni deshabilitar grabación/anuncios para hacer funcionar el addon.
4. Habilitar `setinterfacevar=yes` en cada cola atendida, usando el punto custom de colas que realmente incluya la instalación. Cuando `queues_custom.conf` se carga **después** de la definición generada, se puede reabrir una categoría así:

```ini
[600](+)
setinterfacevar=yes
[601](+)
setinterfacevar=yes
[602](+)
setinterfacevar=yes
```

Verificar el orden de includes de `queues.conf` antes de copiarlo y conservar cualquier ajuste preexistente. Si se carga antes, usar el include posterior soportado en esa instalación; no editar `queues_additional.conf`. Esta parte todavía requiere evidencia en ambas imágenes.

5. Crear en Issabel un **Custom Destination** con `issabel-crm-entry,s,1` y asignarlo a una opción del IVR. Aplicar configuración. Para pruebas internas puede usarse una extensión libre en `from-internal-custom` que haga `Goto(issabel-crm-entry,s,1)`; comprobar que no colisione con el plan existente.
6. Comprobar permisos/SELinux según la imagen. No deshabilitar SELinux como paso del instalador; diagnosticar los AVC si bloquea ejecución, lectura de `.conf`, locks o salida HTTP y ajustar el contexto/política del laboratorio según el paquete real.

```sh
sudo asterisk -rx 'dialplan reload'
sudo asterisk -rx 'module reload app_queue.so'
asterisk -rx 'dialplan show issabel-crm-entry'
asterisk -rx 'queue show 601'
```

El wrapper entra a la cola generada `ext-queues`, conservando sus opciones. Guarda y encadena un `QAGI`/`VQ_AGI` previo; conserva `QGOSUB`. No aplicar el wrapper recursivamente como AGI previo. Verificar también el resultado de ese encadenamiento con los hooks existentes del laboratorio.

## Configuración y llamadas en curso

Los mapas, conexión y límites están en `/etc/asterisk/issabel_crm.conf`, con formato `.conf/INI leído por el AGI`. Sólo el archivo generado `issabel_crm_extensions.conf` es dialplan incluido por Asterisk. No incluir el INI directamente como dialplan. La configuración se edita manualmente o mediante candidato + `validate`/`apply` (reemplazo atómico del INI).

Cada AGI lee un snapshot completo. El destino y afiliado de una llamada quedan en su canal; el hook de atención lee la configuración vigente al responder. Cada ingreso guarda una huella del mapa de agentes en el canal; si ese mapa cambia antes de atender, se omite el aviso con `notification_mapping_changed`, evitando reasignar una ficha a un usuario distinto. Las nuevas llamadas usan el mapa nuevo. Un cambio de endpoint puede afectar avisos posteriores, incluyendo llamadas ya en espera; no modifica su afiliado ni destinatario. Para fallback inicial y timeout del externo, `apply` regenera el dialplan y requiere recarga. Los mapas no requieren un servicio adicional.

Conservar `runtime_dir=/run/issabel-crm`: systemd-tmpfiles lo recrea al reiniciar. Si se cambia, administrar explícitamente creación, propietario `asterisk`, permisos y recreación al boot. Una ruta inexistente omite avisos y genera diagnóstico. No contiene datos de llamadas.

## Pruebas de aceptación local

- CUIL reconocido: cola correcta, aviso sólo al responder, usuario/ficha correspondientes. Una oferta que no responde no debe producir aviso.
- CUIL vacío, incompleto o inválido: mensajes, intentos acotados y cola general. Abandono: sin ficha inventada ni procesos de consulta acumulados.
- GET caído, lento, con error y con transferencia lenta: timeout total y general; no esperar indefinidamente.
- Aviso lento: medir desde respuesta hasta audio con el CRM demorado; el tiempo remoto no debe añadirse. El worker termina dentro del límite y la conversación continúa.
- Dos o más llamadas simultáneas (mismo y distintos afiliados): comparar interacción, miembro y usuario. Miembro sin mapa y saturación: audio continúa y búsqueda manual.
- 0800: configurar un número/ruta autorizados, comprobar CallerID, transformaciones, ocupado/rechazo/timeout. El addon usa `Dial(Local/<0800>@from-internal/n,...,g)` para pasar por las rutas salientes de Issabel; un fallo retorna a general. Una salida contestada no dispara un aviso propio de operador CRM. Verificar que la ruta no conteste anticipadamente el canal Local y oculte un fallo remoto.
- Aplicar configuración, recargar y reiniciar: repetir llamada y verificar grabación, anuncios y conducta existente.
- Repetir inventario y matriz en ambas combinaciones. Completar luego el contrato y apertura de ficha del CRM real.

## Reversión

Restaurar la opción de IVR anterior y aplicar configuración en Issabel antes de retirar el addon. En instalación manual:

```sh
sudo python3 /usr/lib/issabel-crm/addon.py uninstall
sudo asterisk -rx 'dialplan reload'
```

Para RPM: `sudo rpm -e issabel-crm`, y luego recargar. Los mapas y secretos se conservan en la instalación manual; con RPM, los archivos modificados siguen la política de preservación `.rpmsave`. Retirar sólo las líneas `setinterfacevar` que agregaste si ya no se necesitan y no pertenecían a la cola anterior. Comprobar una llamada normal posterior. No ejecutar un piloto hasta registrar la evidencia local y el contrato real.
