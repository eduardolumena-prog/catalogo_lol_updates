# FASE 53 — Publicación de imágenes certificadas

## Objetivo
Publicar en el canal remoto consumido por la aplicación el catálogo certificado de imágenes ya recuperado en FASE 50/51, sin volver a auditar identidades.

## Baseline certificado
- 713 identidades canónicas.
- 693 registros con imagen verificada/cubierta.
- 20 registros `USER_SUPPLIED_IMAGE_PENDING`.
- Sin identity guessing.
- Las fotografías personales nunca son evidencia oficial.

## Problema confirmado
El `manifest.json` de producción todavía publica `5.3.6-global-final`, generado por `PHASE49_GUIDE31_TRANSPARENT_PUBLISHER`, por lo que la aplicación recibe el catálogo de 713 registros pero no el conjunto final de 693 imágenes certificadas.

## Gates de publicación
1. Recuperar el artefacto certificado de FASE 50/51 y reutilizarlo; no reiniciar la auditoría de 713.
2. Construir un `catalog.json` remoto con exactamente 713 identidades canónicas sin cambios.
3. Mantener exactamente 20 registros pendientes salvo nueva evidencia certificada.
4. Publicar las 693 referencias de imagen certificadas/cubiertas mediante tipos soportados por la app.
5. Generar un ZIP compatible con `lol-catalog-update-v1`, schemaVersion 2.
6. Calcular y verificar SHA-256 del catálogo y del ZIP.
7. Usar una versión estrictamente superior a `5.3.6-global-final` para que la app detecte la actualización.
8. Validar descarga, hash, importación y conservación de datos personales antes de cambiar `main`.
9. Actualizar `manifest.json` solamente después de que todos los gates anteriores pasen.
10. Probar que el teléfono puede actualizar sin reinstalar la APK.

## Seguridad
Todo se prepara en `autopilot/phase53-publish-certified-images`. No se modifica `main` hasta certificación completa.
