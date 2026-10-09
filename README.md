# CallFlow Hooks

Addon extensible para Issabel: un IVR normal selecciona un perfil que ejecuta un handler local JSON y continúa a un destino aprobado. Afiliados CRM será el primer caso de uso comercial.

La versión 0.2.6 en revisión incluye administración integrada **PBX → PBX Configuration → Inbound Call Control → CallFlow Hooks**, sesión/ACL de Issabel, formulario generado por esquema, perfiles independientes, .conf compartido con edición manual, destinos automáticos, entradas none/CallerID/DTMF/variable de canal, contexto por llamada y ejecución con presupuesto/contingencia. Un RPM distribuye el puente IssabelPBX, el acceso nativo anterior y el backend compartido. El formulario sigue el diseño del IVR, con navegación lateral y creación/edición por secciones; reutiliza destinos PBX y System Recordings para el audio DTMF, con entrada manual alternativa. El instalador permite usar un checkout fijado o descargar un RPM de una release publicada. La VM Issabel 4 confirmó instalación y menú nativo con 0.2.1; 0.2.2 confirmó guardado desde la web; el log posterior confirmó IVR → AGI → interno 101 atendido; audio y contingencia siguen pendientes; ver [laboratorio](docs/laboratory.md) y [diseño](docs/native-addon-design.md). Se revisa en [PR #30](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/pull/30).

- [Contrato del handler](docs/contracts/handler-v1.md).
- [Configuración y extensiones](docs/configuration.md).
- [Paquete y laboratorio](docs/laboratory.md).
- [Mapa Wayfinder](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/1), [especificación](https://github.com/JonatanGarbuyo/integracion-asterisk-ivr-custom-crm/issues/2) y [entregas](docs/planning/index.md).
- [Investigación de Asterisk e Issabel](docs/research/mecanismos-asterisk.md).

```bash
python3 -m unittest discover -s tests -v
python3 tools/build.py
python3 tools/build-rpm.py  # requiere rpmbuild y checkout limpio
```

CI ejecuta procesos JSON/AGI e instaladores con Python 3.6, 3.9 y 3.12, y los formularios reales PHP con 5.4 y 8.2, simulando las fronteras de Issabel/GitHub/herramientas del sistema. Un job separado construye e inspecciona el RPM real. Sin PHP o RPM locales, las respectivas pruebas se omiten y son obligatorias en sus jobs CI. La publicación desde un tag o rama de release coincidente con `packaging/version.json` ejecuta pruebas y publica RPM/manifiesto como prerelease de laboratorio. La modalidad `--release v0.2.6` permite instalar sin Git ni herramientas de compilación en la PBX; ver los comandos en [laboratorio](docs/laboratory.md#descarga-directa-sin-git).

Objetivos de instalación: **Issabel 4/Asterisk 11.25.3/CentOS 7.9/IssabelPBX 2.11.0-48** e Issabel 5/Asterisk 18. Compatibilidad efectiva, audio y regeneración se validarán en VM. La integración de Afiliados y el hook opcional al responder cola pertenecen a las siguientes entregas; esta versión no los instala.
