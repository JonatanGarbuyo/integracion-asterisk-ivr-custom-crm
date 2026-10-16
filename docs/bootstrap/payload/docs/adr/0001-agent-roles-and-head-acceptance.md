# Roles y aceptación del HEAD

Estado: decisión explícita del usuario, 12/10/2026. Implementación de #40 pendiente.

ChatGPT planifica y actúa como operador de aceptación final; OpenCode implementa/corrige y realiza dos revisiones independientes desde la configuración del repositorio. Los workflows publican mediante guards. El PR draft es el handoff durable antes de la revisión adversarial; un candidato fallido se retoma desde el mismo PR.

La aceptación requiere criterios satisfechos, gates completos, Standards PASS, Spec PASS y CI exitoso sobre el HEAD actual. Cualquier cambio de HEAD exige renovar ambas revisiones y CI. El operador puede mergear una entrega por vez, sin conflictos; los modelos no reciben credenciales de publicación ni promueven producción.

Esto sustituye el flujo legado que condicionaba la existencia del PR a haber aprobado ambas revisiones y no preservaba código ante fallo. Durante bootstrap, sus checks son auxiliares: el paquete importado requiere revisiones y CI del HEAD final antes de aceptar.
