CallFlow Hooks 0.2.8 — idiomas, segundos y eliminación de perfiles.

- Interfaz en inglés/español según el idioma de Configuración PBX, incluidos campos, ayudas, botones, errores y borradores. Catálogos compilados incluidos.
- Destino de contingencia / Fail Over Destination y Destino al continuar / Continue Destination.
- Límites del handler y entrada DTMF en segundos, con fracciones exactas; el .conf conserva milisegundos.
- Eliminar perfiles mediante POST con confirmación, autorización, CSRF y versión. Lista referencias y bloquea perfiles usados o APIs de uso no disponibles.
- Retira sólo destinos legacy propios; conserva perfiles y credenciales ajenos ante fallos de limpieza/escritura. Aplicar cambios sigue siendo manual en PBX.

Actualización de laboratorio desde 0.2.7, sin Git:

```bash
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/v0.2.8/tools/install.py -o /tmp/callflow-install.py
sudo /usr/bin/python3 /tmp/callflow-install.py --release v0.2.8
```

No requiere desinstalar. El instalador conserva perfiles, credenciales y referencias IVR. Recargar la página después de actualizar y pulsar Apply Config / Aplicar cambios si hay cambios pendientes.

Implementación revisada en PR #37, con CI Python 3.6/3.9/3.12, PHP 5.4/8.2 y RPM aprobada. La publicación vuelve a ejecutar pruebas y construcción sobre el commit fijado. Idioma efectivo, referencias reales, eliminación y aplicación del dialplan requieren prueba instalada. Issabel 5, CRM y respuesta de cola continúan pendientes.
