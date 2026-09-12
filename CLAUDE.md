# Reto 02 WIN — Escucha externa y alertas tempranas

Contexto de proyecto para Claude Code. Léelo completo antes de escribir código.

**Datos de ejemplo**: `sample_data/` tiene un dataset sintético (ficticio, no real)
con el mismo esquema que la base real, para que otro agente entienda la
estructura sin necesitar acceso a la base de datos ni exponer contenido real
de terceros. Ver `sample_data/README.md`.

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
| **Discord (WIN server, #general)** | Por mensaje | 31 mensajes reales extraídos (8-12 sep 2026), sin medición formal de continuidad | no medido | Pulso + texto, extracción manual periódica (no automatizable por ToS) |
| **TikTok (@win_internet + competencia)** | Por post | 100 items en base (95 nuevos en última corrida automatizada) | **0** (medición previa) | Pulso + texto, **ahora automatizable** con sesión de cookies + captcha resuelto una vez |
| **X / Twitter** | Por tuit | 41 tuits en base (primera corrida), rango 2017-2025 | no medido | Pulso + texto + escalamiento, **automatizable** con sesión de cookies, sin captcha visto |
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
- Se intentó automatizar esto con `ingest/save_session.py`: lanza un Chromium headed visible en
  el escritorio/VNC del usuario, para que el usuario inicie sesión manualmente y Playwright
  serialice cookies+localStorage a disco sin que el asistente las lea directamente (esa acción
  — leer `document.cookie` — está bloqueada por diseño). **No funcionó**: la cuenta de TikTok
  usada inicia sesión vía "Continuar con Google", y Google bloquea ese flujo OAuth dentro de
  cualquier Chromium lanzado por Playwright por detectarlo como navegador automatizado,
  independientemente de que las credenciales sean correctas (error visible: *"Couldn't sign
  you in, this browser or app may not be secure"*). Tampoco hay una vía alternativa vía Claude
  in Chrome: esa herramienta no expone ninguna función de exportar `storage_state`, sólo
  navegación/clics/lectura de página — usarla para leer cookies caería en el mismo bloqueo
- **Resuelto después, vía exportación manual de cookies**: el usuario exportó las cookies de
  su sesión de TikTok con una extensión de navegador (Cookie-Editor/EditThisCookie) y las
  compartió directamente — el asistente nunca las leyó de `document.cookie`, sólo las convirtió
  de formato. `ingest/convert_cookies.py` transforma ese export al `storage_state` de
  Playwright, guardado en `.sessions/tiktok_state.json` (permisos 600, fuera de git)
- **Aviso de seguridad importante**: las cookies se compartieron pegadas en texto plano en la
  conversación con el asistente — eso las expone igual que si se hubieran filtrado, sin importar
  qué se haga con ellas después. Quedó como decisión explícita del usuario no rotarlas/invalidar
  la sesión pese a la recomendación de hacerlo. Cualquiera con acceso al historial de esa
  conversación podría reutilizarlas mientras sigan vigentes
- Con la sesión cargada, la primera carga headless mostró un **captcha de deslizar puzzle**
  (anti-bot por fingerprinting/IP distinta a la del navegador original) al intentar acceder al
  grid de videos — las cookies por sí solas no bastan, TikTok también verifica la huella del
  cliente. El usuario resolvió el captcha manualmente una vez, en un Chromium headed visible vía
  VNC; `ctx.storage_state()` se volvió a guardar tras eso, y **las cargas headless posteriores
  ya no lo pidieron de nuevo** — la sesión quedó "confiada" para ese entorno
- `ingest/tiktok.py::discover_ids_with_session()` usa esta sesión guardada para hacer scroll y
  extraer URLs de video/foto sin intervención humana. Corrida real: **96 items recolectados** de
  las 4 cuentas monitoreadas (WIN + Movistar/Claro/Entel), 95 insertados tras dedup — TikTok
  pasó de 5 a 100 items totales en la base en una sola corrida
- Limitación que persiste: el scroll se estabiliza en un tope (~26 items por cuenta observado)
  incluso con sesión válida — no trae el historial completo, sólo lo más reciente por carga.
  Suficiente para pulso continuo si se corre periódicamente vía cron, no para reconstruir todo
  el histórico de una cuenta de una sola vez
- `normalize/pipeline.py::run_tiktok()` ahora, sin pasarle `--tiktok <archivo>`, llama a
  `discover_ids_with_session()` automáticamente — **queda apto para cron**, a diferencia del
  estado anterior. Pendiente: agregarlo de hecho al crontab (hoy sigue fuera, ver `cron/README.md`)

**Discord** (servidor oficial "WIN server", `discord.com/invite/gamer-win`) — hallazgo del
usuario a partir de las ponencias del hackathon: WIN tiene un servidor propio para su línea de
planes gamer, con un canal de soporte técnico. Verificado real y explorado con una cuenta de
usuario normal (con permiso explícito del usuario, quien confirmó autorización de WIN para el
hackathon — ver nota de ToS abajo antes de construir nada más aquí).

- Servidor real, verificado vía API pública de invitación (`GET /api/v10/invites/gamer-win`, sin
  auth): **5.849 miembros, ~1.000-1.034 en línea**. Descripción oficial del guild: *"Servidor
  oficial de los gamers de win, disfruta con otros winners o reporta inconvenientes en tu
  servicio"*. Tiene `WinBot`, un bot propio de WIN para onboarding/tickets de soporte
- Estructura de canales vista como miembro normal (no admin): `bienvenidas`, `enlaces-utiles`
  (bloqueado para no-clientes), `actualizaciones-del-servidor`, `blog`, `registro-clientes`,
  `ayuda`, `general`, `off-topic`. Sólo 8 canales visibles — el servidor es mucho más grande
  puertas adentro (probablemente tiene canales de voz y quizá texto adicionales sólo para
  clientes verificados, y posiblemente tickets privados 1-a-1 vía `WinBot`)
- `#ayuda` es informativo/anuncios (explica el sistema de tickets), **no** es el canal donde
  los clientes escriben sus quejas libremente — los tickets de soporte real probablemente son
  canales/hilos privados por usuario, invisibles para un miembro normal y para el propio dueño
  del hackathon (confirmado: quien organiza no tiene acceso admin al servidor)
- **`#general` sí es chat libre en tiempo real** (`¡En este canal puedes hablar con cualquier
  persona!`) y ahí sí aparecen quejas técnicas espontáneas con timestamp al minuto. Durante la
  exploración manual (12 de septiembre de 2026) se observó, en vivo, un patrón consistente con
  una caída de servicio real siendo reportada por varios usuarios de forma casi simultánea —
  exactamente el tipo de señal temprana que el reto busca. Revisando el historial hacia atrás
  (sesiones de días previos) se confirmó actividad recurrente con contenido técnico relevante
  (quejas de velocidad, hardware/cableado, comparación con otros ISP) y densidad de mensajes
  aparentemente alta. No se guardó ni se transcribió contenido textual de mensajes de terceros
  en este repositorio — la verificación fue visual, vía navegador, sin persistir datos
- **No se hizo medición cuantitativa formal** (no se contaron mensajes/día ni semanas vacías,
  a diferencia de las demás fuentes) — sólo exploración manual vía navegador para confirmar
  viabilidad. Pendiente si se decide construir un extractor real
- El widget público de Discord (`GET /api/guilds/<id>/widget.json`, sin auth) sólo expone
  canales de **voz**, no da mensajes ni canales de texto — no sirve como atajo sin sesión

*Riesgo de ToS y cómo se resolvió aquí*: Discord prohíbe explícitamente el scraping sin
consentimiento por escrito, y hay precedente reciente (investigadores de UFMG, Brasil)
donde Discord calificó como violación de sus políticas el patrón "cuenta de usuario se une a
un servidor ampliamente descubrible y extrae mensajes", incluso siendo investigación académica
anonimizada. La vía limpia es un bot de aplicación invitado por un administrador del servidor
(WIN), pero se confirmó que quienes dirigen el hackathon no tienen ese acceso hoy. El usuario
confirmó que **el hackathon cuenta con autorización de WIN**, lo cual cambia el análisis de
riesgo/consentimiento frente a TikTok/X (ahí el riesgo era sólo de la cuenta usada; acá hay
además datos de terceros/clientes de WIN de por medio).

*Por qué no se automatiza en tiempo real ("self-bot")*: se investigó si había alguna forma de
"escuchar" mensajes nuevos pasivamente sin que contara como automatización prohibida. La
respuesta, confirmada contra la documentación oficial de Discord: la prohibición es sobre **qué
tipo de token se conecta al Gateway** (WebSocket en tiempo real), no sobre si el bot escribe o
sólo lee. Un bot de aplicación con permisos de sólo lectura es legítimo, pero debe ser invitado
por un admin del servidor (WIN) — acceso que no tenemos hoy. Conectar el **token de la cuenta de
usuario personal** al Gateway, aunque sea sólo para recibir eventos sin nunca escribir, es
exactamente la definición de "self-bot": Discord lo prohíbe sin excepción y puede terminar la
cuenta permanentemente, sin importar cuidados técnicos (captcha, delays, human-like typing).
No se construyó ningún cliente de Gateway por este motivo.

*Modelo adoptado: extracción histórica + polling humano-asistido, sin protocolo.* Es la única
vía compatible con el ToS usando la cuenta de usuario ya unida:
- Un humano (el usuario del proyecto) abre `#general` en su propio cliente, hace scroll hacia
  atrás como cualquier miembro, y lee lo que ve en pantalla — no hay automatización de la
  cuenta, es uso normal de la interfaz
- `ingest/discord_manual.py::parse_manual_batch()` normaliza esos mensajes (ya extraídos por un
  humano) al esquema `Item` — no hace red, no toca Discord, es sólo la capa de normalización
- Se repite periódicamente (ej. 1x/día) para capturar mensajes nuevos — polling, no un listener
  de eventos en tiempo real
- **Corrida real** (12 de septiembre de 2026, vía Claude in Chrome + lectura manual del DOM):
  31 mensajes extraídos de `#general`, ventana del 8 al 12 de septiembre de 2026, 30 insertados
  tras dedup. Contenido real: reportes de caída de servicio con zona geográfica mencionada
  (varios distritos de Lima, en fechas y horas distintas — señal de avería recurrente, no un
  evento único), y discusión de producto (planes, ExitLag). Los autores se guardaron con
  identificadores genéricos, no los nombres de usuario reales de Discord — dato sensible que no
  hace falta para el análisis de tema/sentimiento
- **Nota de manejo de datos**: el intento de documentar contenido citado de Discord directamente
  en este archivo (`CLAUDE.md`, versionado en git) fue bloqueado por el sistema por tratarse de
  datos de terceros de una fuente que requiere consentimiento. Los mensajes reales sólo se
  persisten en la base de datos local (`items`, fuente `discord_win_general`), nunca en el
  repositorio de código
- No hay descubrimiento automático de qué scrollear ni cuánto — cada sesión de extracción manual
  cubre lo que el humano decida revisar en ese momento, sin garantía de cobertura completa

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

- **Discord (WIN server)** — confirmado real y con quejas espontáneas en `#general` (ver detalle arriba). Pendiente: medición cuantitativa formal y decisión de vía de acceso (bot admin autorizado por WIN vs. seguir con cuenta de usuario)
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
- **app técnico** (agregada tras revisar el corpus real — ver "Actualización tras ampliar
  datos" más abajo: bugs de la app propia de WIN, distinto de una avería del servicio de
  internet)

Con 150-250 ejemplos etiquetados por categoría, un fine-tuning de RoBERTuito basta. Con menos, generaliza mal.

### Capa 4: detección de anomalías (ya construida, validada contra un caso real)

`anomaly/detect.py` implementa los dos modelos de la sección "Ajustes estadísticos por baja
frecuencia": banda de baseline móvil (gaussiano) sobre la serie horaria de Trends, y modelo de
conteos (Poisson, leave-one-out sobre toda la ventana, no sólo "hoy") sobre `(fuente, tema,
día)` para los items de texto.

*Campo `confianza`*: con menos de `MIN_DIAS_CONFIANZA_ALTA` (5) días de histórico en una
combinación (fuente, tema), la anomalía igual se reporta pero marcada `confianza="baja"` — más
honesto que ocultarla del todo mientras una fuente nueva (como Discord) acumula profundidad.
Por debajo de `MIN_DIAS_CONFIANZA_BAJA` (3 días) no se reporta nada, ni con baja confianza.

*Por qué se evalúa toda la ventana y no sólo el día actual*: la primera versión sólo comparaba
"hoy" contra el histórico previo, así que un pico de hace 2-3 días (ya no "el día actual") nunca
se detectaba. Se cambió a leave-one-out sobre cada día de la ventana — necesario tanto para
alertas sobre eventos recientes como para la validación retrospectiva de los tres eventos
históricos de WIN (ver esa sección más abajo).

**Caso real validado (12 de septiembre de 2026)**: los reportes de avería extraídos de Discord
(#general, 8-12 sep) muestran picos el 9 y el 11 de septiembre, con 2-3 zonas de Lima distintas
mencionadas por día. El modelo de Poisson por sí solo **no** los marca como `alerta` —
matemáticamente correcto: con sólo 3 días de histórico y valores de 2-3 eventos/día, un salto de
2 a 3 no es estadísticamente distinguible del azar. Esto expuso un límite real del método
puramente estadístico con series tan cortas — ver la sección de enrutamiento por cluster
geográfico, más abajo, para cómo se resolvió sin depender sólo del z-score.

Trends funciona con 30 días de histórico horario ya acumulados. El modelo de conteos por tema
sobre fuentes de mayor profundidad (Google Play, News) requiere que la ingesta continua acumule
más semanas de flujo reciente para que las anomalías reales (si las hay) se separen del ruido
histórico — revisar de nuevo según avance la cronología de datos.

### Clasificador de tema por reglas (provisional, ya construido)

`nlp/rules_classifier.py` — diccionario de keywords en español peruano por categoría +
matching por regex con normalización de acentos (reusa `normalize_text` de
`normalize/dedup.py`). No reemplaza el fine-tuning; sirve para (a) tener `items.tema`
poblado ya, y (b) generar candidatos etiquetados para que un humano arme el dataset real
de entrenamiento — los items sin match quedan con `tema = NULL`, sin forzar clasificación.

Corrida real sobre los 484 items del corpus: 130 clasificados (354 sin match).
Conteo por categoría: publicidad_reputacion 32, facturacion_cobros 31,
averia_caida_servicio 25, precio_planes 15, atencion_cliente 12, instalacion 8,
privacidad_datos 4, cobertura 3. Ninguna categoría quedó en cero, aunque cobertura y
privacidad_datos tienen volumen bajo — esperable dado que Google Play/News no son donde
más aparece ese tipo de queja. `precio_planes` mezcla quejas de precio con noticias de
negocio (adquisiciones, contratos mayoristas); es aceptable como primer corte pero conviene
revisarlo antes de usarlo como dataset de entrenamiento definitivo.

**Actualización tras ampliar datos (12 sep 2026, sesión de acumulación para el fine-tuning)**:
corpus creció a 788 items (Twitter con 24 queries de marca/tema, más historial de Discord
extraído manualmente hasta el 1 de septiembre). 272 items clasificados por reglas — mejoras
concretas encontradas revisando el corpus real, no hipotéticas:

- **Categoría nueva `app_tecnico`** (21 items): 63 quejas de Google Play sobre bugs de la app
  (login roto, código de verificación que no llega, "actualizar datos") no encajaban en ninguna
  de las 8 categorías originales — no es avería de *internet*, es la app en sí. Se agregó como
  9na categoría con `enrutamiento` propio (Experiencia Cliente, P3)
- **`privacidad_datos` ampliada con vocabulario real de threat-intel**: el hallazgo más serio
  del corpus — un tuit de una cuenta de threat-intel reportando venta de una base de datos con
  350.000 registros de clientes de WIN — no se clasificaba porque el diccionario sólo tenía
  frases genéricas ("filtración de datos"), no el vocabulario real ("venta de base de datos",
  "threat alert", "actor de amenaza", etc.). Ya corregido y verificado: el caso real ahora
  clasifica correctamente
- **Desempate por prioridad de categoría**: `classify()` ahora hace que `privacidad_datos` gane
  cualquier empate/casi-empate frente a otras categorías (antes el desempate era puramente por
  conteo de matches, y 3 casos reales de "hackearon a Win" caían en `publicidad_reputacion` por
  tener más matches ahí que en `privacidad_datos`, a pesar de ser claramente incidentes de
  seguridad) — justificado porque `privacidad_datos` ya es "P1 siempre" en el enrutamiento
- Se quitó `"ciberseguridad"` sola del diccionario de `privacidad_datos`: generaba un falso
  positivo real ("Win Negocios va por nuevo nicho con servicio de ciberseguridad" — es un
  producto que WIN *vende*, no un incidente que sufre)

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

### Capa 5 (ya construida y validada): enrutamiento + tarjeta de alerta

- `nlp/geo.py` — extracción de geo por lista cerrada de distritos de Lima/Callao (más simple que
  un NER entrenado, mismo techo de cobertura baja advertido en CLAUDE.md). `enrich.py` la pobla
  en `items.geo` junto con sentimiento/embedding.

  **Cobertura real medida sobre el corpus completo (598 items): 1.7% (10 items)** — más baja que
  el 20-40% estimado originalmente. Desglose por fuente: Google Play 0/336, TikTok 0/100,
  Discord 3/19, Google News 7/143 (pero esas 7 son "Lima y Callao" en titulares de mercado, no
  quejas geolocalizadas — ruido, no señal útil). Se investigó ampliar el diccionario con
  patrones indirectos ("norte/sur de Lima", "mi distrito", nombres de calles) revisando el
  corpus real, y **no aparecieron** — no es un problema del extractor, Google Play y TikTok (73%
  del corpus) simplemente no traen esa información en el texto. Se agregaron Trujillo/Chiclayo
  al diccionario (ciudades donde WIN opera) con un filtro de contexto que exige una señal de
  queja junto al nombre de la ciudad, porque sus únicas menciones en el corpus son marketing de
  TikTok (eventos patrocinados: "Rally de Arequipa", "Concurso Ecuestre Arequipa") — sin el
  filtro, se contarían posts promocionales como incidencias reales en esa ciudad. Tras esta
  ampliación la cobertura total **no cambió** (sigue en 10/598): confirma que el techo por
  keywords ya está alcanzado con los datos disponibles hoy.

  La señal geo real de estos 10 items sigue siendo suficiente para el caso de Discord (los 3
  reportes de avería trajeron distrito, y eso bastó para el enrutamiento P1 de la Capa 5) — pero
  no alcanza para segmentar geográficamente Google Play o TikTok. Para eso, la vía real no es
  texto libre sino datos estructurados: cruzar contra el dataset público de OSIPTEL
  (`conexiones-de-internet-fijo-osiptel`, ya identificado en la sección de fuentes) para
  comparar volumen de quejas *totales* de una fuente contra la distribución real de clientes por
  zona — no requiere geo por mensaje individual, sólo agregados. No implementado todavía.
- `alerts/routing.py` — matriz tema → área/urgencia, con las señales de escalamiento automático
  (Indecopi, OSIPTEL, "voy a denunciar", etc.) y el criterio de cluster geográfico para
  avería/caída **ya conectado a geo real**: 2+ zonas distintas mencionadas el mismo día → P1;
  si ningún item trae geo, cae a un proxy por volumen (3+ items) para no perder recall
- `alerts/generate.py` — arma la `TarjetaAlerta` completa a partir de las anomalías de la Capa 4.
  Usa **todos** los items del día (no sólo los 3 de ejemplo) para el análisis de cluster
  geográfico, y de ahí toma los 3 primeros para mostrar como citas
- `alerts/render_slack.py` — convierte la tarjeta en el payload real de Slack Block Kit
  (header, campos, sparkline ASCII, citas con link al original, botones "Esto es ruido" /
  "Ver en el tablero"). El botón de ruido ya tiene a dónde escribir: `items.es_ruido` existe en
  el esquema desde el principio. **No incluye el envío real** (falta la URL del webhook de
  Slack, que debe proveer WIN)

**Caso real de punta a punta (12 de septiembre de 2026)**: el pipeline completo (Discord →
normalización → sentimiento/geo → clasificador de tema → detección de anomalías → tarjeta de
alerta) procesó los reportes de avería reales y generó tarjetas con urgencia **P1** para el 9 y
11 de septiembre (2+ distritos distintos por día) y **P2** para el 12 (sin distinción geo clara,
sólo volumen). Esto ocurre **aunque el detector estadístico marque `severidad=normal`** — el
enrutamiento por cluster geográfico actúa independiente del z-score, igual que ya hacía el
enrutamiento por prensa/escalamiento para publicidad_reputacion. Es la primera demostración
completa del criterio central del reto ("distinguir la molestia pasajera del problema de
verdad") con datos reales, no sintéticos.

### Escalamiento directo: alertas sin depender de un pico estadístico (hueco cerrado)

El CLAUDE.md original ya decía, en "Estrategia de fuentes por rol": *"Una sola nota de prensa
no necesita pico estadístico para ser P1. Que exista ya es la señal."* — pero ese camino nunca
se construyó: hasta esta sesión, **toda** tarjeta de alerta salía de `anomaly/detect.py`, que
sólo detecta picos de volumen. El hallazgo más grave del corpus real (la venta de una base de
datos de 350.000 registros de clientes de WIN, encontrada en Twitter) no generaba ninguna
tarjeta, porque los eventos de `privacidad_datos` están dispersos en 12 años sin concentración
temporal — nunca hay suficiente densidad para que el detector de conteos lo vea como anomalía.

`alerts/generate.py::_tarjetas_por_escalamiento_directo()` cierra ese hueco: genera una tarjeta
por cada item individual (no agrupado por día) cuyo `tema` esté en `TEMAS_ESCALAMIENTO_DIRECTO`
(hoy sólo `privacidad_datos`) o cuyo texto contenga una señal de `SENALES_ESCALAMIENTO` — sin
pasar por el detector de anomalías. Cada tarjeta lleva un campo `antiguedad` legible ("hace 2h",
"hace 5d", "hace 3a") calculado con `_antiguedad_legible()`, porque un escalamiento directo no
filtra por recencia (decisión explícita: mostrar todo el historial de eventos críticos, no sólo
los recientes, ya que sirven también para la validación retrospectiva) — sin ese campo, un
evento de 2022 se vería igual de urgente que uno de hoy en el tablero.

`SENALES_ESCALAMIENTO` se amplió con vocabulario real de threat-intel encontrado en el corpus
("threat alert", "data leak", "data breach", "base de datos extraída/filtrada", "venta de base
de datos", "actor de amenaza"), y `FUENTES_PRENSA` ahora incluye `"twitter"` — X trae cobertura
real de prensa/threat-intel además de quejas directas de usuarios, a diferencia de cuando sólo
se consideraba RSS de medios tradicionales.

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

### X / Twitter: por qué no hay atajo gratuito

Se evaluaron todas las vías sin usar una cuenta real (decisión explícita: no arriesgar una
cuenta de X todavía). Ninguna sirve:

- API oficial v2 sin autenticación: 401
- API oficial v2, tier gratuito: **descontinuado desde febrero 2026** para desarrolladores
  nuevos. El modelo actual es pay-per-use desde el primer request ($0.005 por lectura, $0.015-0.20
  por post creado), sin capa gratuita
- Nitter (instancias públicas): 3 de 4 conocidas caídas (`nitter.net`, `nitter.poast.org`,
  `nitter.privacydev.net`). La única viva (`xcancel.com`) tiene antibot/captcha activo — mismo
  patrón de bloqueo que TikTok y Google Maps, no hay forma de pasarlo sin sesión/navegador real
- twikit: es la única vía funcional conocida, pero **requiere cuenta real logueada** y no se
  probó por la misma razón de arriba

Conclusión de esa primera revisión: X seguía en la categoría "pulso, riesgo ToS" sin alternativa
gratuita, mientras no se usara una cuenta real.

### X / Twitter: resuelto después, vía cookies exportadas manualmente (mismo patrón que TikTok)

El usuario exportó las cookies de su sesión de X con una extensión de navegador y las compartió
directamente — mismo mecanismo y mismo aviso de seguridad que con TikTok (ver esa sección):
las cookies quedaron expuestas en texto plano en la conversación, decisión explícita del usuario
no rotarlas. `ingest/convert_cookies.py` las convirtió a `storage_state`, guardado en
`.sessions/twitter_state.json` (permisos 600, fuera de git).

A diferencia de TikTok, **la sesión de X no mostró ningún captcha ni verificación anti-bot** en
la primera carga headless — ni en `/home` ni en `/search`. No se necesitó el paso de "resolver
captcha en Chromium visible" que sí hizo falta para TikTok.

`ingest/twitter.py` hace scraping vía Playwright: navega a `x.com/search?q=<query>&f=live`,
hace scroll, y parsea el DOM de cada `<article>` (X no tiene un endpoint JSON público accesible
sin backend propio, a diferencia del SSR de TikTok). El parseo requirió una corrección real:
la primera versión cortaba el cuerpo del tuit en la primera mención a otra cuenta (`@usuario` a
mitad de texto), perdiendo el resto del mensaje — se corrigió filtrando líneas de metadata
(handle, fecha, métricas) por patrón en vez de por posición, y reconstruyendo el cuerpo con todo
lo que queda.

Queries monitoreadas: `"WIN internet Peru"`, `"WIN fibra Peru"`, `"WIN OSIPTEL"`,
`"Wi-Net Telecom"`. Corrida real: 42 tuits recolectados (41 tras dedup), rango 2017-2025. Ya
apareció señal de alto valor en la primera prueba: una queja real citando directamente a
`@IndecopiOficial` y `@OSIPTEL` sobre una caída masiva (dispara el escalamiento automático de
`alerts/routing.py`), y una queja con distrito mencionado ("sigo sin internet aquí en
Chorrillos"). También apareció una alerta de una cuenta de threat-intel sobre una posible
filtración de datos de **"Win Empresas"** — nombre similar pero **no verificado si es la misma
WIN (WI-NET TELECOM) del proyecto o una entidad de negocio B2B separada**; no se asumió que son
la misma empresa, queda pendiente de verificar antes de tratarlo como incidente de la marca.

Riesgo de ToS: mismo tipo de riesgo que TikTok (scraping vía navegador automatizado con una
cuenta real, contra los términos de X) — se acepta el mismo nivel de riesgo ya asumido ahí, no
uno nuevo. `run_twitter()` en `normalize/pipeline.py` está listo para cron pero **no se agregó
todavía** (ver `cron/README.md`) — pendiente la misma confirmación explícita que se pidió para
automatizar TikTok.

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
