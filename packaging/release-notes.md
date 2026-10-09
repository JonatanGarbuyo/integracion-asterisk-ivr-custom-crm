CallFlow Hooks 0.2.6: selectores nativos de destinos y grabaciones.

- Destino siguiente y contingencia reutilizan el selector del IVR: categoría y destino PBX, incluidas colas e internos.
- Audio para solicitar dígitos lista grabaciones simples de System Recordings, con Sin audio.
- Conserva entrada manual, perfiles existentes, credenciales, borradores y validación. Los IDs de audio se resuelven al guardar a un nombre relativo; AGI y .conf mantienen su contrato.
- El audio seleccionado se usa para entrada DTMF, sin añadir un saludo general. Los archivos/destinos que se eliminen fuera del addon requieren revisar los perfiles.

Sigue en PBX Configuration → Inbound Call Control. Guardar actualiza el .conf; Aplicar cambios regenera el dialplan. No aplica automáticamente ni introduce staging.

El usuario confirmó instalación de 0.2.5 y anteriormente una llamada IVR → AGI → interno101 atendido. Los selectores, audio audible, contingencia y permisos efectivos requieren prueba en la VM; Issabel 5 sigue pendiente. No incorpora Afiliados CRM ni respuesta de cola.

```bash
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/v0.2.6/tools/install.py -o /tmp/callflow-install.py
sudo /usr/bin/python3 /tmp/callflow-install.py --release v0.2.6
```

Actualización directa sin Git ni rpm-build, conservando perfiles. El instalador verifica versión, commit, SHA256 y dependencias. Para sólo descargar: agregar `--prepare-only --output /tmp/callflow-rpm`.
