# AgenticNomina — Instrucciones permanentes para Codex

## Propósito

AgenticNomina es un sistema auditable de conciliación y revisión de nómina para Colombia. Ayuda a detectar diferencias, aplicar reglas versionadas, generar evidencia y organizar decisiones humanas. No reemplaza el juicio de nómina, contabilidad, recursos humanos, legal o cumplimiento.

## Idioma

- La interfaz, reportes, hojas de Excel, mensajes operativos y documentación funcional deben estar en español.
- El código puede usar identificadores en inglés coherentes con la arquitectura existente.
- No renombrar componentes existentes sólo para traducirlos.

## Fuente de verdad y seguridad

- `origin/main` es la fuente técnica de verdad. Antes de cada incremento, verificar rama, árbol y sincronización; revisar README, roadmap, configuración, modelos y pruebas.
- Tratar archivos de nómina como altamente sensibles: nunca versionar PDFs, Excel operativos, identificaciones, nombres reales, correos, firmas ni soportes. Usar sólo datos sintéticos en fixtures y pruebas.
- Antes de commit o push, revisar diff, staging y no rastreados. Mantener entradas reales externas e ignoradas por Git.

## Política conservadora y trazabilidad

- No inventar reglas laborales, fiscales, contables ni políticas internas; no dar efecto financiero a reglas provisionales, incompletas, ambiguas o no aprobadas.
- Ante incertidumbre usar `PENDIENTE`, `EN_VALIDACION` o `REVIEW`. No transferir aprobaciones financieras entre períodos ni entre versiones de regla; el modo estricto reconoce únicamente una aprobación completa para el identificador y versión exactos.
- Conservar período, regla/versión, origen y referencia de evidencia, decisión, responsable, fecha, motivo, precedente y estado de revisión. No sobrescribir silenciosamente decisiones anteriores.

## Forma de trabajo

1. Implementar incrementos pequeños, aislados y con datos sintéticos; evitar refactors amplios y no modificar entradas reales.
2. Añadir pruebas, reabrir programáticamente Excel sintéticos cuando corresponda y documentar la aceptación operativa pendiente.
3. Ejecutar `pytest`, `ruff check .` y `git diff --check`; revisar privacidad antes de publicar.
4. Crear un commit funcional aislado sólo después de validar localmente. Antes de fusionar, verificar los checks de GitHub y GitGuardian.
5. Tras fusionar, volver a `main`, actualizarla y confirmar árbol limpio, commit contenido y validaciones correctas.

## Detenciones y terminación

- No pedir decisiones intermedias si pueden representarse conservadoramente como revisión.
- Detenerse ante cambios locales inesperados, riesgo de aplicar una regla sin aprobación válida, ambigüedad que altere resultados financieros, política empresarial no suministrada, acción irreversible no autorizada o error técnico irresoluble.
- No declarar terminado sólo por compilar o pasar pruebas: incluir, cuando aplique, implementación, pruebas, documentación, validación de Excel, privacidad, commit, PR, checks, fusión y verificación desde `main`.
