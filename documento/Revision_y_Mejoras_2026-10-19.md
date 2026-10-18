# Revisión técnica y visual del Laboratorio 09

19 de octubre de 2026 | CC3084 Data Science | UVG

Esta nota complementa la explicación del avance y documenta la revisión realizada con asistencia de Codex. Corresponde al estado actual de los archivos locales. El avance conserva su fecha y contenido; esta nota no acredita una entrega anterior ni aportes manuales del equipo.

## Problemas y mejoras aplicadas

- Ejecución en Windows. El generador no buscaba Arial en las carpetas de fuentes de Windows. Ahora detecta la instalación del sistema y del usuario. Se creó un entorno virtual local y se documentaron comandos de PowerShell que no requieren cambiar la política de ejecución.
- Dependencias. La generación exigía instalar Prophet y CmdStanPy aunque los intervalos ya estaban guardados. El entorno base contiene las dependencias de exportación y verificación; el reajuste se instala mediante requirements-modelo.txt. Las versiones directas del entorno base están fijadas.
- Ruta del Laboratorio 1. La extracción dependía de una ubicación relativa específica. Ahora preparar_datos.py recibe --lab1 y comprueba la existencia de los archivos necesarios antes de escribir. La reproducción ordinaria utiliza los agregados incluidos en datos/.
- Validación. Las comparaciones se alinean por Fecha. Se detectan meses faltantes o duplicados, columnas ausentes, valores no finitos, límites invertidos, métricas desactualizadas, perfiles estacionales inconsistentes y porcentajes con denominadores incorrectos. Los controles continúan activos al usar python -O.
- Verificación del resultado. Se recalculan MAE y RMSE para los seis modelos a partir de sus predicciones originales. Se revisan los dos tamaños de impresión, página única, resolución del PNG, textos de KPI y métricas, SVG editable y correspondencia entre el ZIP y sus archivos.

## Decisiones visuales de la revisión

El eje histórico termina explícitamente en junio de 2026, para que su cierre coincida con la cobertura parcial del último año. Se mantienen las anotaciones de pandemia y cambio metodológico y la comparación sobre la suma Turista + Excursionista.

Las columnas conservan el orden calendario y el origen cero. Los tres promedios mensuales más altos de 2009-2019 se seleccionan desde los datos y se distinguen con borde, acento naranja y etiqueta directa. Esta redundancia permite reconocerlos también sin distinguir colores. Semana Santa, bono 14 y fin de año se presentan como contexto; la serie no demuestra causalidad.

El observado se representa con línea continua y la estimación de Prophet con línea discontinua. Ambos comparten escala; la banda identifica el intervalo predictivo nominal del 95 %. Las guías quedan sobre la banda para conservar la referencia cuantitativa. Esta evaluación usa meses ya observados y no proyecta fechas posteriores a junio de 2026.

Los cuatro KPI, los extremos del cuadrante y la reducción de RMSE se obtienen de insumos validados. La tabla conserva las métricas del Lab 1 y el orden por RMSE. Se mantiene la paleta azul oscuro, verde azulado y naranja y el recorrido de contexto, calendario, comparación, estimación y decisiones.

## Correspondencia con la guía

- Bloque 1: titular narrativo, subtítulo y cuatro KPI con período y denominador.
- Bloque 2: historia mensual, media móvil y eventos anotados.
- Bloque 3: perfil de estacionalidad y cuatro extremos entre las siete series seleccionadas.
- Bloque 4: comparación de seis modelos y estimación sobre la prueba con intervalo rotulado.
- Bloque 5: cinco recomendaciones, fuente académica y pie de créditos del equipo.
- Formatos: PNG de 2400 x 3394 px; PDF A3 vertical y alternativa 11 x 17 pulgadas, una página cada uno. Son tamaños diferentes y se conservan ambos.

## Verificación y pendientes de entrega

Las pruebas automatizadas trabajan con copias temporales de los datos y cubren alteraciones deliberadas y filas reordenadas. El registro de verificación enumera las métricas recalculadas y hashes de los insumos. Un resultado técnico correcto no certifica aprobación académica ni sustituye la inspección visual de las exportaciones.

Falta confirmar los nombres, carnés y grupo de Canvas en creditos.json. El pie conserva el crédito genérico al equipo hasta contar con esa información. También corresponde actualizar la copia de Canva y facilitar al docente los enlaces y permisos reales de trabajo compartido.

La guía exige historial de contribuciones de cada integrante y limita la difusión pública de los datos. La revisión permanece local, con identidad Git de Ian Cumes, reconocimiento de la asistencia de Codex y fechas reales. La visibilidad y los permisos del repositorio deben ser gestionados por su propietario conforme al uso académico autorizado.

Fuentes: guía Laboratorio 09 Visualización Estática 2026; explicación del avance incluida en documento/; agregados, predicciones y metadatos incluidos en datos/. No se recuperó la base detallada ni se reentrenó Prophet en esta revisión.
