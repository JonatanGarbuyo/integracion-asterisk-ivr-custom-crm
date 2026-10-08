CallFlow Hooks: addon nativo de Issabel con perfiles genéricos, menú/ACL, puente IssabelPBX y handlers JSON desde un IVR normal.

Corrección 0.2.2: el guardado fallido conserva el formulario y el último borrador de la sesión, incluso al recargar. Muestra errores junto a los campos y distingue permisos, acceso y versión de configuración. Las credenciales son de escritura: no se guardan en el borrador y deben reingresarse si se habían cambiado. Incluye ayudas para destinos `contexto,extensión,prioridad` y permite sincronizar destinos sin completar un nuevo perfil.

Versión de laboratorio. La VM del usuario confirmó instalación y menú nativo en Issabel 4 con 0.2.1. Las pruebas automatizadas y el empaquetado RPM verifican la corrección; guardar/aplicar, ACL completos, SELinux y llamadas/audio requieren prueba instalada. Issabel 5 también requiere validación en VM. Afiliados CRM y el hook de respuesta de cola pertenecen a entregas posteriores.

Instalar sin Git ni rpm-build (Python >=3.6, RPM, rpm2cpio y cpio):

```bash
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/v0.2.2/tools/install.py -o /tmp/callflow-install.py
sudo /usr/bin/python3 /tmp/callflow-install.py --release v0.2.2
sudo /usr/sbin/callflow-hooksctl status
```

El instalador descarga el RPM y manifiesto, comprueba versión, commit y SHA256, valida dependencias y comprueba el estado final. Conserva perfiles existentes. Después de instalar, abrir PBX → CallFlow Hooks, revisar destinos y aplicar configuración desde PBX.

Para preparar únicamente la descarga: agregar `--prepare-only --output /tmp/callflow-rpm` al comando del instalador, sin ejecutar la instalación.
