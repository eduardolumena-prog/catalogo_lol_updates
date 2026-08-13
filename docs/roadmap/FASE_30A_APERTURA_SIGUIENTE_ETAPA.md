# FASE 30A — Apertura de la siguiente etapa

## Punto de partida

La línea `5.2.9-global-final / 713` está cerrada y certificada.

No debe modificarse.

## Estado heredado

- recordType: 713/713
- club: 573/713
- rarity: 645/713
- releaseYear: 278/713
- club unresolved: 140
- rarity unresolved: 68
- releaseYear unresolved: 435

## Línea A — Aplicación Android

Hallazgo registrado durante la prueba de 5.2.9:

La actualización fue detectada al utilizar manualmente **Buscar actualización**, pero no apareció automáticamente al abrir la aplicación.

La interfaz actual indica una política de comprobación automática de máximo una vez cada 12 horas.

### Trabajo recomendado siguiente

Auditar el motor de actualización de la aplicación y evaluar:

- comprobación automática al iniciar;
- reducción o rediseño del cooldown de 12 horas;
- búsqueda manual siempre forzada;
- prevención de consultas repetidas;
- conservación del comportamiento SHA-256/transaccional actual.

No se modifica todavía el código de la aplicación en FASE 30A.

## Línea B — Catálogo Maestro futuro

Cualquier enriquecimiento posterior deberá comenzar desde una nueva base de trabajo, por ejemplo V52, sin alterar V51 ni 5.2.9-global-final.

Campos pendientes:

- club: 140
- rarity: 68
- releaseYear: 435

No se crea V52 automáticamente en esta fase.

## Estado de FASE 30A

**APERTURA COMPLETADA**

La siguiente acción funcional queda pendiente de autorización:

1. priorizar la mejora del actualizador automático de la aplicación; o
2. abrir V52 para continuar enriqueciendo el Catálogo Maestro.

Recomendación técnica actual: revisar primero el comportamiento de actualización automática de la aplicación, porque fue observado directamente durante la prueba real de 5.2.9.
