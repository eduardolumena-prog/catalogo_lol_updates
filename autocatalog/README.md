# ELM AutoCatalog — fase 1: detección y publicación automática segura

**Rama de preparación. No habilitar GitHub Actions ni fusionar sin autorización.**
Base congelada: `5.3.6-global-final` / 713 muñecas; `main` y el
`manifest.json` productivos no se modifican en esta rama.

## Fuente oficial

- The MGA Shop: https://shop.mgae.com/collections/new-l-o-l-surprise
- Catálogo L.O.L. completo: https://shop.mgae.com/collections/l-o-l-surprise
- Descubrimiento preferido: `products.json` Shopify (solo lectura).
- Si se bloquea JSON: HTML únicamente como aviso de productos pendientes;
  **ninguna muñeca se promueve automáticamente desde HTML**.
- No se descargan ni replican fotos; se usa la referencia HTTPS de la
  imagen individual publicada oficialmente cuando se puede asociar
  inequívocamente. No se usa fotografía del paquete sorpresa como
  retrato de una muñeca no identificada.

## Política de publicación

El sistema **no convierte productos aleatorios en personajes**.
Solo agrega una muñeca cuando el listado oficial identifica un único
personaje en un producto individual, existe una serie ya certificada,
no hay coincidencia con nombre+serie, URL de producto o identidad, y se
conserva la procedencia. Por ahora estas reglas cubren:

- O.M.G. Music Festival, productos «Featuring NOMBRE – Fashion Doll».
- O.M.G. Hello Kitty & Friends, productos «– NOMBRE».

Todo lo demás pasa a `autocatalog/candidates.json` para seguimiento
automático. La lista de candidatos NO implica un lanzamiento
individual confirmado. No se inventan rareza, año, club ni códigos
oficiales; `officialCode` queda nulo si MGA no lo proporciona.

Cada publicación crea un JSON completo compatible con la app, un ZIP
con `catalog.json` y un manifest con nuevos SHA-256. Conserva los
`canonicalId` anteriores, accesorios, relaciones, series e imágenes.
El publicador falla antes de cambiar `manifest.json` cuando el origen
no es verificable.

## Comandos

```bash
python -m unittest discover -s tests -p 'test_autocatalog.py' -v
python tools/autocatalog.py
python tools/autocatalog.py --publish
```

- Comando sin `--publish`: únicamente actualiza candidatos de descubrimiento.
- Comando con `--publish`: prepara publicación solo para altas de muñecas
  inequívocas; sin altas, no cambia el manifest.
- El workflow está configurado para una ejecución diaria **únicamente
  después de su integración en `main`**. No se ha ejecutado.
- GitHub commit/bot publica solo el paquete validado y candidatos.

## Límites de automatización

- Necesita acceso HTTPS estable a las fuentes oficiales y permisos de
  escritura del bot en GitHub Actions; si la fuente cambia, falla cerrado.
- No puede identificar de forma fiable los personajes escondidos en
  un envase surtido sin una lista o guía individual oficial.
- La app actual ya comprueba el manifest automáticamente, pero exige
  consentimiento para instalar; el modo sin confirmación requiere
  una modificación de la app y su nueva compilación.
- El estado de `Mi Colección`, favoritos, notas e imágenes personales
  **no forma parte de este repositorio**, ni se transmite al publicador.
- El código incluye pruebas sin red. Antes de activar producción se
  requieren pruebas de integración de fuente real y APK en teléfono.
