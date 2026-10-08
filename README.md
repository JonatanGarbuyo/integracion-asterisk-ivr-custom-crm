# CallFlow Hooks

Addon extensible para Issabel: un IVR normal selecciona un perfil que ejecuta un handler local JSON y continúa a un destino aprobado. Afiliados CRM será el primer caso de uso comercial.

La primera entrega incluye formulario nativo generado por esquema, perfiles independientes, .conf compartido con edición manual, destinos automáticos, entradas none/CallerID/DTMF/variable de canal, contexto por llamada y ejecución con presupuesto/contingencia. Se revisa en [PR #30](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/pull/30).

- [Contrato del handler](docs/contracts/handler-v1.md).
- [Configuración y extensiones](docs/configuration.md).
- [Paquete y laboratorio](docs/laboratory.md).
- [Mapa Wayfinder](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/1), [especificación](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/2) y [entregas](docs/planning/index.md).
- [Investigación de Asterisk e Issabel](docs/research/mecanismos-asterisk.md).

```bash
python3 -m unittest discover -s tests -v
python3 tools/build.py
```

CI ejecuta procesos JSON/AGI con Python 3.6, 3.9 y 3.12, y el formulario real PHP con 5.4 y 8.2, simulando únicamente las fronteras de Issabel. Sin PHP local, esas pruebas se omiten localmente y son obligatorias en CI.

Objetivos de instalación: **Issabel 4/Asterisk 11.25.3/CentOS 7.9/IssabelPBX 2.11.0-48** e Issabel 5/Asterisk 18. Compatibilidad efectiva, audio y regeneración se validarán en VM. La integración de Afiliados y el hook opcional al responder cola pertenecen a las siguientes entregas; esta versión no los instala.
