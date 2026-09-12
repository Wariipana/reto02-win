# Reto 02 WIN — Escucha externa y alertas tempranas

Contexto de proyecto para Claude Code. Léelo completo antes de escribir código.

---

## Estado de la tarea inicial (fuente adicional) — RESUELTO

Se buscó y midió una fuente adicional consistente y con volumen. Resultado: **TikTok
(@win_internet) aprueba el criterio** y se añade como fuente de pulso continuo.
Ver la sección "Medición de fuentes" más abajo con los números exactos.

---

## El reto

De la diapositiva oficial (Reto 02, áreas dueñas: Comunicaciones, Marketing, Experiencia Cliente):

> ¿Cómo leemos, casi en tiempo real, lo que se dice de WIN y de la categoría en redes sociales y medios digitales, y convertimos ese ruido en algo sobre lo que un área pueda actuar el mismo día?

**Dentro del campo**: redes sociales, comentarios, foros, reseñas y prensa digital, incluida la regional. Detectar el tono, separar el tema real del ruido, y definir a quién le llega la alerta, cuándo y con qué urgencia.

**Fuera del campo**: responderle al cliente en nombre de WIN. El reto es entender y avisar, no contestar por la marca.

**Con qué se trabaja**: sólo fuentes públicas. No depende de ninguna integración con sistemas internos, ni hoy ni después.

**Cómo se juzga**: que sobre un periodo real reciente distinga la molestia pasajera del problema de verdad, y que un jefe de área diga que esa alerta le habría servido.

### Sobre la empresa

WIN (WI-NET TELECOM S.A.C.) es un ISP de fibra óptica 100% peruano. Opera en Lima, Callao y provincias incluyendo Trujillo y Chiclayo. Alrededor de 527.000 clientes de internet residencial según datos de OSIPTEL citados en prensa; la meta declarada era llegar a un millón para 2027. Competidores directos: Movistar, Claro, Entel, Bitel.

---

## Medición de fuentes (datos reales, ya verificados)

Todo lo de esta tabla fue medido ejecutando código, no estimado.

| Fuente | Granularidad | Volumen medido | Semanas vacías /26 | Veredicto |
|---|---|---|---|---|
| **Google Trends** | Horaria | 169 puntos en 7 días, 98 no-cero | **0** | Pulso primario |
| **TikTok (@win_internet)** | Por post | 93 posts en 180d (0,52/día), acelerando (4-7/sem ago-sep vs 1-4/sem mar-may) | **0** | Pulso + texto, requiere sesión para enumerar |
| **X / Twitter (twikit)** | Por post | sin medir | — | Pulso, riesgo ToS |
| Google Play | Diaria | 67 en 180d (0,39/día) | 3 | Confirmación |
| Google Maps | Por reseña | 683 reseñas ficha principal | no medible | Confirmación, frágil |
| Google News RSS | Por nota | 15 en 180d | 13 | Escalamiento |
| App Store RSS | Por reseña | 10 en 180d | 18 | Descartado |
| YouTube | Por comentario | 374, el 75% de hace 3 años | ~26 | Descartado |
| Reddit r/PERU | — | sin medir (pendiente credenciales OAuth) | — | Pendiente |

### Detalles por fuente

**Google Trends** (`pytrends`) — la fuente que resuelve el problema de continuidad.
- `timeframe='now 7-d'` devuelve resolución **horaria**: 169 puntos, 98 con valor distinto de cero
- `timeframe='today 3-m'` devuelve 93 puntos diarios sin huecos
- Permite comparar WIN contra Movistar y Claro en la misma consulta, lo que da la línea base sectorial
- **No tiene texto**. Dice que algo pasó, no qué pasó
- Los términos específicos de queja no sirven: "win no funciona", "internet caído" y "win reclamo" sólo tuvieron señal en 2-3 semanas de 12 meses. Usa términos de marca amplios

**TikTok** (`@win_internet`) — cuenta oficial verificada, 45.1K seguidores, 414.3K likes.
- Medido navegando con sesión real (Chrome, cuenta propia) y extrayendo los IDs de post del DOM: 110 posts recolectados entre 2026-01-28 y 2026-09-11, 93 de ellos dentro de los últimos 180 días
- **0 semanas vacías de 26** — la fuente con mejor continuidad después de Google Trends, y con texto
- Cadencia acelerando: 1-4 posts/semana en marzo-mayo 2026, 4-7 posts/semana en agosto-septiembre 2026
- Comentarios por post: 0-41 típico; picos de cientos en contenido viral (un video con 2.6M reproducciones tuvo 36 comentarios)
- **Contenido es marca/marketing, no quejas espontáneas** — el valor real está en los *comentarios* de cada video (ahí aparece la queja de usuario), no en el post en sí. Rol: "pulso + explicación", similar a X pero sin twikit
- **Barrera técnica**: el endpoint que lista todos los posts de una cuenta (`/api/post/item_list/`) devuelve **200 con body vacío** sin sesión iniciada — bloqueo por IP de datacenter / firma anti-bot, mismo patrón que Google Maps. Con sesión de cuenta real (cookies), el grid del perfil sí carga vía scroll
- Una vez se tiene el ID de un post (por scroll con sesión, o indexado en Google), el **detalle SÍ es accesible sin sesión**: la página de video individual trae los datos completos server-side en `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">` → `__DEFAULT_SCOPE__["webapp.video-detail"].itemInfo.itemStruct` (incluye `desc`, `createTime`, `stats.diggCount/shareCount/commentCount/playCount`). Esto evade el WAF (Slardar) que sí bloquea peticiones HTTP planas (confirmado: `curl` da un HTML de challenge de 1.4KB; Playwright con user-agent de escritorio carga la página completa, ~500KB)
- Google indexa videos individuales de esta cuenta (`site:tiktok.com/@win_internet/video`), lo que da una vía de descubrimiento de IDs sin sesión, pero incompleta y con "dark posts" (anuncios pagados no orgánicos) mezclados — se identifican porque el `webapp.video-detail` devuelve `statusMsg: "item is dark post"` en vez de `itemInfo`
- Implicación de arquitectura: **enumerar posts nuevos requiere una sesión de cuenta persistente** (cookies renovadas periódicamente); **obtener detalle/comentarios de un post ya conocido no requiere sesión**

**Google Play** (`google-play-scraper`) — app `com.win.miwin_app`
- 3,03★ de 572 ratings, 359 reseñas con texto
- Mediana de 3 reseñas por semana; 0,39 por día
- Trae texto, fecha exacta y rating. Calidad alta, volumen bajo

**App Store** — app id `6479166579`, RSS `itunes.apple.com/pe/rss/customerreviews/`
- 2,15★ de 117 ratings (peor que Android; es un dato segmentable en sí mismo)
- El RSS **sí trae fecha** por reseña, en el campo `updated`
- Sólo 60 reseñas accesibles por más que pagines. 10 en los últimos 180 días

**Google News RSS** — `news.google.com/rss/search?q=...&hl=es-419&gl=PE&ceid=PE:es-419`
- 169 notas únicas históricas, 15 en los últimos 180 días
- Agrega prensa nacional y regional en un solo feed, filtrable por consulta
- Encontró tres crisis reales de WIN, útiles para validación retrospectiva (ver más abajo)

**RSS de prensa directos** — probados uno por uno:
- Funcionan: RPP, Gestión, El Comercio, Infobae (vía `arc/outboundfeeds`), Diario Correo, Andina
- Fallan: La República (404), Perú21 (403), La Industria de Chiclayo (404), Expresión (DNS), RPP Lambayeque (feed vacío)
- Para prensa regional sin RSS, Google News con consulta geográfica es el sustituto

**Google Maps** — ficha principal `ChIJAQBsP3DIBZERVbvnAkPqTuI` (WIN San Isidro)
- 3,0★ con **683 reseñas**. Texto rico y directamente relevante
- Existe una ficha mal categorizada, "Laboratorios Win Peru" (2,5★, 43 reseñas), cuyo contenido es de clientes del internet de WIN. Hay señal de marca dispersa en fichas que WIN probablemente desconoce
- Volumen de la categoría, sólo muestreando Lima: Movistar ~7.600 reseñas, Claro ~5.400, Entel ~3.900
- **Google Maps ya publica su propia agregación temática** en la ficha, como botones de filtro con conteo. En WIN: "área" 31, "señal" 19, "denunciar" 18, "movistar" 18, "asesor" 10. Es clasificación gratis, accesible sin paginar
- **La medición de tasa falló**. Ver la sección de notas técnicas

**OSIPTEL** — la API DKAN sí funciona: `https://www.datosabiertos.gob.pe/api/3/action/package_list` devuelve 4.714 datasets. Los relevantes son `reclamos-presentados`, `reclamos-por-averías`, `reclamos-resueltos`, `conexiones-de-internet-fijo-osiptel`. Nota: `package_search` devuelve 404; usa `package_list` y `package_show?id=<slug>`.

### Candidatos descartados

| Fuente | Por qué se descartó |
|---|---|
| YouTube comments | 280 de 374 comentarios son de hace 3 años; sólo 2 en los últimos 9 días. Es picos por campaña, no flujo |
| App Store RSS | 10 reseñas en 180 días; 18 de 26 semanas vacías. El RSS sólo expone 60 reseñas históricas |
| Indecopi "Mira a quién le compras" | Sólo sanciones firmes. Evento raro de alta severidad, cero volumen |
| Downdetector Perú | HTTP 403 en las tres URLs probadas (Cloudflare) |
| OSIPTEL datos abiertos | API DKAN funciona, pero última actualización de reclamos es 2022, en XLSX tras SharePoint, y son conteos agregados sin texto |

### Candidatos pendientes

- **Reddit r/PERU** — API OAuth oficial, gratuita para volumen bajo. Requiere crear una "script app" en `reddit.com/prefs/apps` (necesita cuenta y login del usuario). Anonymous `.json` endpoint da 403 desde este entorno (bloqueo por IP de datacenter, igual que Maps/TikTok)
- **Facebook** — la página @InternetWIN tiene actividad diaria. Probablemente la fuente de mayor volumen después de X. Requiere scraper, es lo más frágil. No probado aún
- Foros peruanos de tecnología / grupos públicos de Telegram
- **Ookla Speedtest / índice ISP de Netflix** — cuantitativo, sin texto, actualización mensual. Sirve como baseline, no como pulso
- **PUNKU de OSIPTEL** (`sistemas.osiptel.gob.pe/punku/`) — no resolvió DNS desde el sandbox original; reintentar

### Cómo medir cualquier candidato nuevo

Repite exactamente este protocolo y añade la fila a la tabla de medición:

1. Extrae todo el histórico accesible
2. Calcula: total de ítems, rango de fechas, promedio por día
3. Cuenta **semanas vacías en los últimos 180 días** (esta es la métrica que decide)
4. Verifica si trae texto y fecha por ítem
5. Anota barreras técnicas: rate limit, códigos HTTP, necesidad de navegador, ToS

Criterio de aprobación: **menos de 4 semanas vacías de 26** y texto por ítem.

---

## Arquitectura propuesta

```
CAPA 1 — INGESTA (scheduler cada 15-30 min)
  Pulso continuo:      Google Trends (horario) · TikTok (@win_internet) · X vía twikit
  Con texto:           TikTok · X · Google Play · Google Maps
  Escalamiento:        Google News · RSS prensa · Indecopi
  Baseline sectorial:  OSIPTEL (mensual) · conexiones por zona
        |
CAPA 2 — NORMALIZACIÓN
  Esquema único: {id, fuente, autor_hash, texto, fecha, url, geo?, rating?, engagement?}
  Dedup por hash + near-duplicate (MinHash)
  Filtro de bots, spam y promoción de revendedores
  Almacén: Postgres + pgvector
        |
CAPA 3 — ENRIQUECIMIENTO NLP
  a) Relevancia: ¿habla de WIN o de la categoría?
  b) Tono/emoción → pysentimiento (preentrenado, no entrenar)
  c) Tema → clasificador propio fine-tuned (sí entrenar)
  d) Geo → NER de distritos y ciudades
  e) Severidad → señales de escalamiento
  f) Embeddings → agrupar publicaciones del mismo incidente
        |
CAPA 4 — SEÑAL vs RUIDO
  Serie temporal por (tema × zona)
  Baseline móvil 30 días + banda de desviación
  Anomalía = desviación significativa O aceleración de volumen
  Cruce con velocidad de propagación (engagement/hora)
        |
CAPA 5 — ENRUTAMIENTO Y ALERTA
  Matriz tema → área dueña
  Urgencia P1 / P2 / P3
  Entrega: Slack o Teams + email + dashboard
```

### Estrategia de fuentes por rol

No todas las fuentes entran igual al sistema. La frecuencia determina el rol:

- **Pulso continuo** → alimenta la serie temporal y el detector de anomalías
- **Explicación** → aporta el texto que dice qué está pasando (aquí entran los *comentarios* de TikTok, no los posts de marca)
- **Escalamiento** → no entra al z-score. Dispara alerta por el hecho de existir

Una sola nota de prensa no necesita pico estadístico para ser P1. Que exista ya es la señal. Esta distinción es de diseño, no una limitación.

### Monitorear la categoría, no sólo WIN

Está explícitamente en el reto ("lo que se dice de WIN **y de la categoría**") y resuelve dos problemas a la vez:

1. Multiplica el volumen de datos por cuatro o cinco
2. Da la línea base comparativa que hace útil la alerta

La pregunta que un jefe de área realmente necesita responder no es "¿subieron las quejas?" sino "¿subieron **sólo las nuestras**?". Si todo el sector sube el mismo día, probablemente fue un corte de backbone o un feriado. Si sólo sube WIN, es problema de WIN. Esa distinción **requiere** datos de competencia.

Marcas a monitorear: WIN, Movistar, Claro, Entel, Bitel.

---

## Capa NLP

Modelos verificados como disponibles en HuggingFace:

| Modelo | Uso | Descargas/mes |
|---|---|---|
| `pysentimiento/robertuito-sentiment-analysis` | Sentimiento en español rioplatense/LatAm, entrenado en tuits | 1.133.802 |
| `pysentimiento/robertuito-emotion-analysis` | Emoción | 297.255 |
| `pysentimiento/robertuito-hate-speech` | Discurso de odio | 174.134 |
| `paraphrase-multilingual-MiniLM-L12-v2` | Embeddings para clustering, ligero | 46.205.723 |
| `intfloat/multilingual-e5-base` | Embeddings de mayor calidad | 7.308.770 |

**Decisión importante: no entrenes un modelo de emociones desde cero.** `pysentimiento` ya está entrenado sobre tuits en español y resuelve el tono.

**Sí entrena el clasificador de tema**, porque las categorías son específicas de WIN y ningún modelo preentrenado las conoce:

- avería / caída de servicio
- facturación y cobros
- instalación
- atención al cliente
- cobertura
- precio y planes
- publicidad y reputación
- privacidad y datos

Con 150-250 ejemplos etiquetados por categoría, un fine-tuning de RoBERTuito basta. Con menos, generaliza mal.

### Ajustes estadísticos por baja frecuencia

Con fuentes de bajo volumen el z-score gaussiano falla: con media de 0,4 eventos por día, cualquier día con 3 eventos parece anomalía extrema aunque sea azar.

1. **Modelo de conteos** (Poisson o binomial negativa), no gaussiano
2. **Ventanas asimétricas por fuente**: X en horas, Play Store en semanas, prensa por evento
3. **Serie compuesta ponderada**: una sola serie que combina fuentes con pesos distintos. Una nota de prensa pesa mucho más que un tuit

---

## Enrutamiento

| Tema detectado | Área dueña | Urgencia por defecto |
|---|---|---|
| Avería, caída, cobertura | Operaciones / Red | P1 si hay cluster geográfico |
| Facturación, cobros | Experiencia Cliente | P2 |
| Atención, call center | Experiencia Cliente | P2 |
| Instalación | Experiencia Cliente | P3 |
| Publicidad, reputación | Comunicaciones / Marketing | P1 si hay prensa |
| Privacidad, filtración, legal | Comunicaciones + Legal | P1 siempre |

Señales que suben la urgencia automáticamente: mención de Indecopi u OSIPTEL, "voy a denunciar", "cambio de operador", aparición en prensa, aceleración del engagement.

Dato de apoyo: en la ficha de Google Maps de WIN, "denunciar" aparece en 18 opiniones. La señal de escalamiento ya está presente en los datos.

---

## Presentación de resultados

### Advertencia sobre el mapa de calor

Si coloreas por volumen de quejas, Lima siempre saldrá rojo y Chiclayo verde, no porque Lima esté peor sino porque ahí está la base de clientes. El mapa se convierte en un mapa de densidad de abonados disfrazado. Dos arreglos:

- **Normalizar por denominador**: usar `conexiones-de-internet-fijo-osiptel` (fuente pública) para mostrar quejas por cada mil conexiones
- **Colorear por anomalía**: cada zona se compara contra su propio histórico. Mejor opción por defecto, no necesita denominador

Segundo problema: la mayoría de publicaciones no tiene geoetiqueta. La ubicación se infiere por NER, con cobertura estimada de 20-40%. El mapa va a estar disperso. **Úsalo como vista secundaria y como filtro, no como pantalla principal.**

### Pantalla principal: tablero de triaje

Un dashboard analítico responde "¿cómo vamos?". Un tablero de triaje responde "¿qué hago hoy y en qué orden?". El reto pide lo segundo.

**Franja superior** — semáforo por área dueña. Cuatro cuadros con conteo de alertas activas.

**Zona central** — cola de alertas priorizada. Cada tarjeta lleva:
- Titular en lenguaje humano ("Pico de quejas por cobro duplicado, zona norte de Lima")
- Volumen y velocidad (18 menciones, +340% vs baseline, creciendo)
- Ventana temporal (empezó hace 6 horas)
- Sparkline con la banda de normalidad de fondo
- 3 publicaciones reales de ejemplo, textuales, con link
- Área asignada y urgencia
- Botón "esto es ruido" para retroalimentar el modelo

**Zona inferior** — histórico: small multiples y mapa.

### Gráficos, en orden de importancia

1. **Small multiples con banda de baseline** — una grilla de mini-gráficos, uno por tema, con la banda gris de normalidad al fondo. Cuando la línea sale de la banda, se pinta de rojo. Este gráfico **es** el argumento central: la molestia pasajera se queda dentro de la banda, el problema de verdad la rompe
2. Área apilada de volumen por tema
3. Barra de mezcla de fuentes por alerta (da credibilidad y detecta migración de reseñas a prensa)
4. Coropletas por z-score, como filtro
5. Línea de tiempo de eventos, para la demo retrospectiva

Evitar: nubes de palabras y medidores tipo velocímetro.

### Opciones técnicas

| Herramienta | A favor | En contra | Tiempo |
|---|---|---|---|
| Streamlit | Todo en Python, conecta directo al pipeline | Estética limitada | 3-5 h |
| Grafana | Alertas nativas, series de tiempo excelentes | Débil para texto; se ve a monitoreo de infra | 4-6 h |
| Metabase / Superset | Rápido sobre Postgres | Genérico, poco control del layout | 3-4 h |
| React + Recharts | Control total, mejor en pitch | El que más tiempo consume | 8-12 h |

Recomendación: híbrido. Backend Python a Postgres, presentación en React con Recharts, **sólo la pantalla de triaje**. Si el tiempo aprieta, Streamlit con CSS custom llega al 80%.

### La pieza que vale más que el dashboard

Un jefe de área no vive en un dashboard: vive en Slack, Teams o el correo. Considera que el entregable estrella sea **la alerta misma**, maquetada como llegaría de verdad: mensaje de Slack con titular, volumen, mini-gráfica, tres citas reales y botón de escalamiento.

El dashboard es donde investigas después. La alerta es donde actúas el mismo día.

---

## Validación retrospectiva

El criterio dice "sobre un periodo real reciente". Google News ya entregó tres eventos reales de WIN para probar:

1. **Caída masiva de internet en Lima** con reportes de usuarios en prensa — caso de incidente técnico
2. **Sanción de Indecopi por anuncios engañosos** — caso de reputación y marketing
3. **Filtración de datos de casi 300 mil clientes** — caso de crisis con implicancia legal

Para cada uno, corre el pipeline sobre la ventana de fechas y demuestra:
- Cuántas horas antes del pico de prensa se habría disparado la alerta
- A qué área la habría enrutado
- Con qué nivel de urgencia

La distancia entre "el sistema alertó" y "salió en prensa" es la métrica estrella del pitch.

---

## Notas técnicas y trampas conocidas

### TikTok: cómo se resolvió el bloqueo del WAF

1. `curl` u otro HTTP plano contra `tiktok.com` recibe un challenge de bot-detection (Slardar WAF), HTML de ~1.4KB con `Please wait...`, nunca el contenido real
2. Playwright con Chromium headless + user-agent de escritorio normal **sí** pasa el WAF para páginas de perfil y de video individual (HTML completo, ~500KB)
3. El grid de videos del perfil (`/@usuario`) NO viene en el HTML inicial ni con Playwright sin sesión: depende de una llamada XHR a `/api/post/item_list/` que devuelve **200 con body vacío** sin cookies de sesión válidas
4. Con sesión real (login vía Google u otro método, cookies del navegador) el mismo grid sí carga con scroll normal
5. El **detalle de un video ya conocido** (`/@usuario/video/<id>`) sí trae todo server-side sin sesión: buscar `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">` → `__DEFAULT_SCOPE__["webapp.video-detail"].itemInfo.itemStruct`
6. Google indexa videos individuales (`site:tiktok.com/@cuenta/video`) — sirve para descubrir IDs sin sesión, pero de forma incompleta y mezclado con "dark posts" (ads no orgánicos, detectables por `statusMsg: "item is dark post"`)
7. El entorno tenía dos intérpretes de Python separados (`/usr/bin/python3` sin pip, `/lsiopy/bin/python3` con pip/playwright) — usar `/lsiopy/bin/python3` para todo lo que dependa de `playwright`/`pyee`

### Google Maps: la medición que falló

Se intentó medir la tasa de reseñas por semana y **no se logró**. Documentado para que no repitas el camino:

1. El endpoint interno `listugcposts` devuelve **403**
2. Playwright necesita `ignore_https_errors=True` si hay proxy de egress
3. La pestaña se llama **"Opiniones"**, no "Reseñas". El botón tiene `aria-label` que empieza con `"Revisiones para "`
4. El clic funciona de forma **intermitente**: 3 de cada 4 intentos. Hace falta espera activa por el botón
5. El scroll se detiene siempre en **10 tarjetas, que son 5 reseñas duplicadas**
6. El menú "Ordenar opiniones" no expone opciones clicables: timeout de 30s

Los puntos 5 y 6 apuntan a limitación por **IP de datacenter**. Desde una IP residencial peruana el comportamiento debería ser distinto. **Prueba esto primero desde una conexión normal antes de invertir tiempo.**

Alternativa limpia: la Places API oficial devuelve 5 reseñas por ficha. Consultando a diario y guardando incrementalmente, en dos semanas tienes la tasa medida sin pelear con anti-bot.

Si el tiempo aprieta, los conteos de keywords de Maps ("señal 19", "denunciar 18") son visibles sin paginar y ya dan señal temática.

### Otras trampas

- `datosabiertos.gob.pe`: usa `/api/3/action/package_list` y `package_show?id=<slug>`. `package_search` devuelve 404
- Reddit devuelve 403 desde IPs de datacenter (confirmado también en este entorno con el endpoint anónimo `.json`). Usa la API OAuth oficial
- Google News RSS necesita `hl=es-419&gl=PE&ceid=PE:es-419` para resultados peruanos
- Scrapers de GitHub que se evaluaron: `gaspa93/googlemaps-scraper` (520★), `egbertbouman/youtube-comment-downloader` (1254★), `Mohammedcha/gplay-scraper` (308★), `AgiMaulana/Instagram-Comments-Scraper` (177★), `mohdtalal3/facebook_post_comment_scraper` (40★). Los de Facebook e Instagram son los más frágiles

### Riesgo de ToS

twikit es un scraper no oficial de la API interna de X. Va contra los Términos de Servicio, la cuenta puede banearse y hay rate limiting agresivo.

El scraping de TikTok vía Playwright (sin API oficial) tiene un riesgo similar en espíritu, aunque más leve en superficie: no usa una API privada con autenticación de app, sólo HTML público renderizado, pero enumerar el catálogo completo sí requiere una sesión de cuenta real que podría ser limitada por TikTok si el patrón de acceso es detectado como automatizado.

**No lo ocultes en el pitch.** Un jurado corporativo va a preguntar. Ten lista la lámina: qué fuentes son 100% limpias, cuáles son scraping, y qué plan de mitigación existe (rotación, rate limiting, o migrar a la API oficial si el proyecto escala).

---

## Dependencias

```bash
pip install pytrends google-play-scraper feedparser twikit \
            pysentimiento sentence-transformers transformers torch \
            psycopg2-binary pandas scikit-learn playwright
playwright install chromium
```

## Alcance realista para el hackathon

Con Google Trends + TikTok + Google Play + Google News + RSS de prensa tienes cinco fuentes funcionando sin necesitar credenciales de API de terceros. twikit y Reddit quedan como fuentes adicionales si hay tiempo (twikit por volumen/velocidad, Reddit pendiente de credenciales OAuth).

Facebook e Instagram son roadmap, no entregable. Son las más frágiles y pueden quemarte medio día.

**Prioridad si el tiempo se acorta:**
1. Pipeline de ingesta con las fuentes limpias (Trends, TikTok, Play, News/RSS)
2. Clasificación de tema y tono
3. Detección de anomalía con banda de baseline
4. Tarjeta de alerta maquetada
5. Validación retrospectiva sobre los tres eventos reales
6. Dashboard completo
7. Mapa
