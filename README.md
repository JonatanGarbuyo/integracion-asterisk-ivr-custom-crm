# CallFlow Hooks

**Perfil actual: Afiliados CRM.** Addon de backend: identificación por CUIL, GET acotado para obtener obra social, ruta a cola/0800 y POST stateless del miembro que respondió. Dos AGI locales, sin listener AMI, base de datos de llamadas ni reintentos durables. Python 3.6+, sólo biblioteca estándar.

**Estado:** primera versión implementada para desarrollo con mocks. Soporte objetivo Issabel 4/Asterisk 16 e Issabel 5/Asterisk 18; validación instalada, audio, troncal y CRM real pendientes. Los tiempos y políticas incluidos son defaults de laboratorio. El formulario web y DNI siguen como ampliaciones opcionales.

Nombre de la feature y namespace: **CallFlow Hooks**, `CALLFLOW_`. [Contrato de nombres y variables](docs/naming.md). El paquete y las rutas de instalación de esta entrega conservan el identificador técnico `issabel-crm`.

## Desarrollo sin PBX

```sh
python3 -m unittest discover -v
python3 -m lab.mock_crm --port 8080
```

Abrir `http://127.0.0.1:8080/` para observar avisos del operador. Datos ficticios y escenarios de falla documentados en la guía.

## Construir e instalar

```sh
python3 tools/build.py
# En la VM, desde el checkout o tarball extraído:
sudo python3 tools/addon.py install
```

Configurar `/etc/asterisk/issabel_crm.conf`, registrar el destino custom `issabel-crm-entry,s,1`, habilitar variables de miembro en colas y verificar el hook antes de realizar llamadas. El instalador conserva archivos operativos existentes y modifica sólo un include identificado en `extensions_custom.conf`. CI construye también el RPM; no instalar ambos mecanismos sobre la misma instancia.

- [Guía de instalación y aceptación en VirtualBox](docs/testing/laboratorio-virtualbox.md).
- [Contrato provisional del CRM](docs/testing/contrato-crm.md).
- [Evidencia automatizada y límites](docs/testing/evidencia.md).
- [Configuración de ejemplo](config/issabel_crm.conf.example).

## Planificación

- [Mapa Wayfinder](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/1).
- [Especificación](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/2).
- [Entregas y dependencias](docs/planning/index.md).
- [Investigación técnica](docs/research/mecanismos-asterisk.md).
- [Vocabulario](CONTEXT.md).

Seguir [AGENTS.md](AGENTS.md). Los tickets de validación física permanecen abiertos hasta contar con evidencia de la PBX local.
