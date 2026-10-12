CallFlow Hooks 0.2.9 — formulario integrado al diseño PBX.

- Uso y eliminación inmediatamente después del título, con icono y ayuda de referencias como IVR. Se conservan POST, confirmación y comprobaciones del servidor.
- Un único Nombre del perfil visible; identificador interno oculto y estable, generado al crear. Cambiar el nombre conserva referencias IVR y contextos.
- Límite del handler y Tiempo para ingresar dígitos sin unidad en la etiqueta ni ayudas permanentes de rangos; entrada en segundos enteros positivos. Configuraciones anteriores con fracciones se conservan hasta elegir expresamente un entero.
- Mensaje del handler de ejemplo aclara que es texto del ejemplo; el audio DTMF se reproduce al pedir dígitos.

Actualizar sin desinstalar, conservando perfiles y credenciales:

```bash
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/v0.2.9/tools/install.py -o /tmp/callflow-install.py
sudo /usr/bin/python3 /tmp/callflow-install.py --release v0.2.9
```

Recargar CallFlow Hooks y aplicar los cambios pendientes en Configuración PBX. Confirmar ubicación de acciones, edición de nombre, entrada entera y ayudas en la VM. El usuario confirmó el idioma de v0.2.8; esta publicación no certifica Issabel5 ni agrega CRM/hook de cola.
