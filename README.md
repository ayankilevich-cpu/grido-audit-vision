# 🍦 Grido Audit Vision

Sistema de auditoría interna para franquicias Grido con dos herramientas integradas:

| Página | Función | Usuario |
|--------|---------|---------|
| 📸 **Captura de Fotos** | Sacar/subir fotos organizadas por sección e ítem | Colaborador |
| 🔍 **Auditoría IA** | Analizar fotos con GPT-4 Vision y generar reportes | Dueño/Encargado |

## Funcionalidades

- **Captura guiada**: selección de sección → ítem → foto desde cámara o galería
- **Compresión automática**: ~90% de ahorro de espacio sin perder calidad de auditoría
- **Progreso en tiempo real**: visualización de ítems cubiertos y pendientes
- **Análisis con IA**: evaluación automática de conformidad usando GPT-4 Vision
- **Reportes**: exportación en Excel/CSV con métricas por sección
- **61 ítems** de auditoría organizados en 5 secciones (A–E)

## Despliegue en Streamlit Cloud

1. Conectá este repositorio desde [share.streamlit.io](https://share.streamlit.io)
2. Configurá los secrets en **Settings → Secrets**:

```toml
OPENAI_API_KEY = "sk-..."
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
pagina_auditoria.py     → 🔍 Auditoría con IA
criteria.py             → 61 criterios de auditoría estructurados
procesar_fotos.py       → Script CLI para compresión batch (solo local)
```

## Criterios de auditoría

Basados en la **Guía de Auditorías Operativas Grido — Abril 2025**:

- **A** — Infraestructura (11 ítems)
- **B** — Experiencia del cliente (11 ítems)
- **C** — Operatoria diaria (18 ítems)
- **D** — Imagen, formato y estética (16 ítems)
- **E** — Oferta y stock (5 ítems)
