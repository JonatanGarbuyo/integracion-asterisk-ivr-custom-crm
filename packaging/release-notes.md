CallFlow Hooks 0.2.5: administración integrada en PBX Configuration → Inbound Call Control.

- Menú junto a IVR y Call Flow Control, en el contexto del botón habitual Aplicar cambios.
- Navegación de perfiles a la derecha, vista inicial con Agregar perfil, formulario de creación/edición por secciones y ayudas junto a las etiquetas, siguiendo el diseño del IVR.
- Al crear se indica cómo vincular el Custom Destination. Al editar se informa Perfil actualizado.
- Con sesión Issabel, permisos del framework además de la sección PBX, incluso sin embeber; credenciales y borradores conservan sus protecciones.
- El acceso anterior PBX → CallFlow Hooks sigue disponible con enlace a la nueva ubicación. Se conservan perfiles, destinos y backend compartido.

Guardar sigue reemplazando el .conf que leen las nuevas ejecuciones AGI. Aplicar cambios regenera el dialplan PBX; esta versión no incorpora configuración pendiente/activa ni recarga automática.

El usuario confirmó instalación de 0.2.4 y llamada por opción 1 explícita → AGI → interno 101 atendido. El nuevo menú/diseño aún requiere comprobación en su VM. Audio, contingencia, ACL instalados completos e Issabel 5 siguen pendientes. Afiliados CRM y respuesta de cola son entregas posteriores.

Instalar sin Git ni rpm-build (Python >=3.6, RPM, rpm2cpio y cpio):

```bash
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/v0.2.5/tools/install.py -o /tmp/callflow-install.py
sudo /usr/bin/python3 /tmp/callflow-install.py --release v0.2.5
sudo /usr/sbin/callflow-hooksctl status
```

El instalador comprueba versión, commit y SHA256 y conserva perfiles. Abrir PBX → PBX Configuration → Inbound Call Control → CallFlow Hooks, revisar y usar Aplicar cambios.

Para preparar únicamente la descarga: agregar `--prepare-only --output /tmp/callflow-rpm`, sin instalar.
