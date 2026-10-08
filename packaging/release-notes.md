CallFlow Hooks: addon nativo de Issabel con perfiles genéricos, menú/ACL, puente IssabelPBX y handlers JSON desde un IVR normal.

Corrección 0.2.3: desde la página nativa, el enlace Configuración PBX abre `/index.php?menu=pbxadmin`. El acceso alternativo IssabelPBX conserva su enlace propio. Al guardar, el mensaje identifica el destino que debe elegirse desde una opción de IVR normal: Custom Destinations → CallFlow Hooks: <identificador>. La guía detalla esa vinculación.

Conserva las mejoras 0.2.2 de errores y recuperación de borradores sin credenciales. Versión de laboratorio: el usuario confirmó instalación, menú y guardado del perfil `example` en Issabel 4 con 0.2.2. Aplicar configuración, llamadas/audio, ACL completos y SELinux permanecen pendientes. Issabel 5 requiere validación en VM; Afiliados CRM y respuesta de cola son entregas posteriores.

Instalar sin Git ni rpm-build (Python >=3.6, RPM, rpm2cpio y cpio):

```bash
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/v0.2.3/tools/install.py -o /tmp/callflow-install.py
sudo /usr/bin/python3 /tmp/callflow-install.py --release v0.2.3
sudo /usr/sbin/callflow-hooksctl status
```

El instalador descarga el RPM y manifiesto, comprueba versión, commit y SHA256, valida dependencias y comprueba el estado final. Conserva perfiles existentes. Después de instalar, abrir PBX → CallFlow Hooks, revisar destinos y aplicar configuración desde PBX.

Para preparar únicamente la descarga: agregar `--prepare-only --output /tmp/callflow-rpm` al comando del instalador, sin ejecutar la instalación.
