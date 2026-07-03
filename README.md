# 🍦 Grido Audit Vision

Sistema de auditoría interna para franquicias Grido con herramientas integradas:

| Página | Función | Usuario |
|--------|---------|---------|
| 📸 **Captura de Fotos** | Sacar/subir fotos organizadas por sección e ítem | Colaborador |
| 🔍 **Auditoría** | Evaluar manualmente cada ítem (Conforme/Observación/No Conforme) y generar reportes | Dueño/Encargado |
| 📊 **Planes de Mejora** | Gestión de desvíos, plan semanal y panel ejecutivo | Dueño/Dirección |
| 📈 **Historial** | Tendencias, ítems recurrentes y comparativa por local | Dueño/Dirección |

## Funcionalidades

- **Captura guiada**: selección de sección → ítem → foto desde cámara o galería
- **Compresión automática**: ~90% de ahorro de espacio sin perder calidad de auditoría
- **Progreso en tiempo real**: visualización de ítems cubiertos y pendientes
- **Evaluación manual**: el auditor marca Conforme/Observación/No Conforme por ítem, apoyándose en la rúbrica de criterios ya redactada. La foto queda como evidencia, no como fuente de la decisión.
- **Sugerencia de IA (opcional, beta)**: en la página de Auditoría hay un panel colapsado para pedir una segunda opinión de GPT-4 Vision, pero nunca decide automáticamente — quedó desactivada como paso obligatorio porque resultaba repetitiva y poco precisa.
- **Gestión de desvíos**: cada ítem no conforme puede generar un desvío con responsable, fecha límite y detección de reincidencia.
- **Reportes**: exportación en Excel/CSV con métricas por sección
- **61 ítems** de auditoría organizados en 5 secciones (A–E)

## Despliegue en Streamlit Cloud

1. Conectá este repositorio desde [share.streamlit.io](https://share.streamlit.io)
2. Configurá los secrets en **Settings → Secrets** (`MONGODB_URI` para persistencia; `OPENAI_API_KEY` es opcional, solo si se quiere usar la sugerencia de IA beta):

```toml
MONGODB_URI = "mongodb+srv://..."
OPENAI_API_KEY = "sk-..."   # opcional
```

3. Listo — la app queda disponible en una URL pública

## Ejecución local (opcional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estructura

```
app.py                  → Punto de entrada con navegación
pagina_captura.py       → 📸 Captura de fotos (mobile-friendly)
pagina_auditoria.py     → 🔍 Auditoría manual (+ sugerencia IA opcional, beta)
pagina_mejoras.py       → 📊 Planes de mejora (desvíos, plan semanal, panel ejecutivo)
pagina_historial.py     → 📈 Historial, tendencias y stats
criteria.py             → 61 criterios de auditoría estructurados
db.py                   → Capa de datos (MongoDB Atlas)
procesar_fotos.py       → Script CLI para compresión batch (solo local, sin uso desde la app)
generar_word.py         → Utilidad de exportación a Word (sin uso desde la app actualmente)
```

## Criterios de auditoría

Basados en la **Guía de Auditorías Operativas Grido — Abril 2025**:

- **A** — Infraestructura (11 ítems)
- **B** — Experiencia del cliente (11 ítems)
- **C** — Operatoria diaria (18 ítems)
- **D** — Imagen, formato y estética (16 ítems)
- **E** — Oferta y stock (5 ítems)
