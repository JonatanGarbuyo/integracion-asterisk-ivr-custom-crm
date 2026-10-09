CallFlow Hooks: addon nativo de Issabel con perfiles genéricos, menú/ACL, puente IssabelPBX y handlers JSON desde un IVR normal.

Corrección 0.2.4: el preflight distingue el servidor Asterisk de sus consolas remotas. Consulta el archivo PID indicado por `core show settings` y comprueba el UID numérico de ese proceso, sin rechazar una consola `asterisk -rvvv` abierta como root. Un servidor con UID root/ajeno, PID ausente o inválido se sigue rechazando. Conserva las correcciones de enlace nativo, destinos y borradores anteriores.

Versión de laboratorio: el usuario confirmó guardado con 0.2.2 y aportó una llamada IVR → AGI → interno 101 atendido. La opción 1 entró por la salida inválida del IVR: configurar una opción explícita para validar el recorrido previsto. La actualización 0.2.3 falló antes de instalar por UID observados 0/997; que el proceso root fuera una consola aún necesita confirmarse en VM. Audio, contingencia, ACL completos e Issabel 5 siguen pendientes. Afiliados CRM y respuesta de cola son entregas posteriores.

Instalar sin Git ni rpm-build (Python >=3.6, RPM, rpm2cpio y cpio):

```bash
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/v0.2.4/tools/install.py -o /tmp/callflow-install.py
sudo /usr/bin/python3 /tmp/callflow-install.py --release v0.2.4
sudo /usr/sbin/callflow-hooksctl status
```

El instalador descarga el RPM y manifiesto, comprueba versión, commit y SHA256, valida dependencias y comprueba el estado final. Conserva perfiles existentes. Después de instalar, abrir PBX → CallFlow Hooks, revisar destinos y aplicar configuración desde PBX.

Para preparar únicamente la descarga: agregar `--prepare-only --output /tmp/callflow-rpm` al comando del instalador, sin ejecutar la instalación.
