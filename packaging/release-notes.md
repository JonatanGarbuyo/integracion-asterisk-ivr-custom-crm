CallFlow Hooks 0.2.7 — integración PBX y perfiles con nombre editable.

- Ayudas explican destino al continuar y destino ante fallo/deshabilitado.
- Nombre del perfil editable; identificador y referencias IVR estables.
- Selectores sin modo manual, con popovers de alta de los módulos PBX. Valores actuales ajenos al catálogo se conservan como opción.
- CallFlow Hooks aparece como categoría de destinos, con perfiles y enlace de edición.
- Perfil actualizado es breve; el shell muestra Aplicar cambios.
- Se retira menú/ACL externo y su página del RPM. Se preservan permisos de Configuración PBX.

Instalación de laboratorio: 

```bash
curl -fL https://raw.githubusercontent.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/v0.2.7/tools/install.py -o /tmp/callflow-install.py
sudo /usr/bin/python3 /tmp/callflow-install.py --release v0.2.7
```

Para empezar limpio: quitar referencias IVR/rutas y Aplicar cambios; esperar llamadas terminadas; desinstalar con rpm -e issabel-callflow-hooks. Sólo si terminó bien, eliminar /etc/asterisk/callflow-hooks y /var/lib/callflow-hooks. Esto borra perfiles/credenciales. No forzar scriptlets ni borrar dialplan generado.

Se comprueba contra fronteras simuladas y procesos reales; popovers/nombres/categoría y migración efectiva necesitan VM. Issabel5 pendiente. No incorpora Afiliados CRM ni respuesta de cola.
