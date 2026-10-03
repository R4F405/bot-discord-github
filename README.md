# Bot Discord Github 🤖

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![discord.py](https://img.shields.io/badge/discord.py-library-7289DA.svg)](https://github.com/Rapptz/discord.py)

Un bot de integración para Discord y GitHub que recibe webhooks de GitHub y envía notificaciones automáticas con embeds personalizados a un canal de Discord específico.

## ✨ Características

- **🔔 Notificaciones de GitHub a Discord**:
  - **Pull Requests**:
    - Notificación al abrir un nuevo PR con información del autor, branch y número de commits
    - Notificación al hacer merge de un PR con detalles del usuario que hizo el merge
  - **Workflows de GitHub Actions**:
    - Notificaciones de workflows completados exitosamente (✅)
    - Notificaciones de workflows fallidos (❌)
    - Información del branch y actor que ejecutó el workflow
  - **Comentarios**:
    - Comentarios generales en pull requests
    - Comentarios de revisión de código con archivo y línea específica

- **🎨 Embeds Personalizados**:
  - Códigos de color según el tipo de evento
  - Información estructurada y fácil de leer
  - Enlaces directos a GitHub
  - Avatares de usuarios

- **🔒 Seguridad**:
  - Validación de firma HMAC de GitHub para verificar autenticidad
  - Servidor web seguro con aiohttp

## ✅ Requisitos

- Python 3.8+
- Una cuenta de Discord
- Un repositorio de GitHub
- Un servidor de Discord donde tengas permisos para añadir bots

## 🔗 Dependencias

- `discord.py`
- `aiohttp`
- `python-dotenv`

## 🚀 Instalación

1. Clona este repositorio:
   ```bash
   git clone https://github.com/R4F405/bot-discord-github.git
   cd bot-discord-github
   ```

2. Crea un entorno virtual e instala las dependencias:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/MacOS
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. Configura las variables de entorno (consulta la sección "⚙️ Configuración").

4. Ejecuta el bot:
   ```bash
   python main.py
   ```
   Deberías ver un mensaje indicando que el bot y el servidor de webhooks están listos.

## ⚙️ Configuración

### 1. 📄 Crear un archivo .env

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```env
DISCORD_TOKEN=your_discord_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret
TARGET_CHANNEL_ID=discord_channel_id
```

### 2. 🔑 Obtener Token de Discord

1. Ve al [Portal de Desarrolladores de Discord](https://discord.com/developers/applications).
2. Haz clic en "New Application" y dale un nombre.
3. Navega a la sección "Bot" en el panel lateral.
4. Haz clic en "Add Bot".
5. Bajo el nombre del bot, haz clic en "Reset Token" y copia el token generado.
6. Pega el token en `DISCORD_TOKEN` en tu archivo `.env`.

### 3. 📨 Invitar el Bot a tu Servidor

1. En el [Portal de Desarrolladores de Discord](https://discord.com/developers/applications), selecciona tu aplicación.
2. Ve a "OAuth2" → "URL Generator".
3. Selecciona los siguientes permisos:
   - En "SCOPES": `bot`
   - En "BOT PERMISSIONS": `Send Messages` y `Embed Links`
4. Copia la URL generada, pégala en tu navegador y selecciona el servidor donde quieres añadir el bot.

### 4. 🆔 Obtener ID del Canal de Discord

1. En Discord, ve a "Ajustes de Usuario" → "Avanzado".
2. Habilita el "Modo de desarrollador".
3. Haz clic derecho en el canal donde quieres recibir las notificaciones y selecciona "Copiar ID".
4. Pega el ID en `TARGET_CHANNEL_ID` en tu archivo `.env`.

### 5. 🔐 Generar Secret de Webhook

Genera un secret aleatorio para firmar los webhooks de GitHub:

```bash
# En Linux/MacOS
openssl rand -hex 32

# En Windows (PowerShell)
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

Guarda este secret en `GITHUB_WEBHOOK_SECRET` en tu archivo `.env`.

### 6. 🎣 Configurar Webhooks de GitHub

Para que GitHub envíe notificaciones a tu bot:

1. Ve a tu repositorio en GitHub.
2. Navega a "Settings" → "Webhooks" → "Add webhook".
3. Configura lo siguiente:
   - **Payload URL**: `http://tu-servidor-publico:8082/github-webhook`
   - **Content type**: `application/json`
   - **Secret**: El mismo valor que pusiste en `GITHUB_WEBHOOK_SECRET`
   - **Which events would you like to trigger this webhook?**: Selecciona "Let me select individual events" y marca:
     - Pull requests
     - Issue comments
     - Pull request review comments
     - Workflow runs
4. Haz clic en "Add webhook".

### 7. 🧪 Configurar ngrok para Pruebas Locales

Para pruebas locales, puedes usar [ngrok](https://ngrok.com/download) para exponer tu servidor (puerto 8082) a internet:

1. Descarga e instala ngrok.
2. Autentica tu cliente de ngrok (solo se hace una vez):
   ```bash
   ngrok config add-authtoken TU_TOKEN_DE_NGROK
   ```
3. Inicia tu bot (`python main.py`) para que el servidor web esté corriendo en el puerto 8082.
4. En otra terminal, ejecuta ngrok:
   ```bash
   ngrok http 8082
   ```
5. Ngrok te dará una URL pública (ej. `https://abc123.ngrok.io`).
6. Usa esta URL en la configuración de tu Webhook de GitHub:
   `https://abc123.ngrok.io/github-webhook`

**Nota**: Cada vez que reinicies ngrok, la URL cambiará, por lo que deberás actualizarla en GitHub.

## 🐳 Despliegue con Coolify (Docker)

El repositorio incluye un `Dockerfile` listo para producción (Python 3.12 slim, usuario no-root, logs sin buffer y `HEALTHCHECK` sobre `/health`).

1. En Coolify: **+ New Resource → Private/Public Repository** y selecciona este repositorio y la rama `main`.
2. **Build Pack**: `Dockerfile`.
3. **Ports Exposes**: `8082`.
4. **Domains**: asigna un dominio (ej. `https://github-bot.tu-dominio.com`). Coolify (Traefik) genera el certificado HTTPS automáticamente.
5. **Environment Variables**: añade las mismas variables que en `.env` (no subas el `.env` al repositorio):
   - `DISCORD_TOKEN`
   - `GITHUB_WEBHOOK_SECRET`
   - `TARGET_CHANNEL_ID`
6. **Deploy**. En los logs deberías ver que el bot se conecta a Discord y que el servidor de webhooks arranca en el puerto 8082.
7. Actualiza el webhook en GitHub (Settings → Webhooks → Payload URL) con la nueva URL: `https://github-bot.tu-dominio.com/github-webhook`.

**Comprobación**: `curl https://github-bot.tu-dominio.com/health` debe devolver `200`.

**Notas**:
- El puerto se puede cambiar con la variable `PORT` (por defecto `8082`). Si la cambias, actualiza también *Ports Exposes*.
- El bot no guarda estado en disco, así que no necesita volúmenes persistentes.
- Activa **Auto Deploy** en Coolify para redesplegar en cada push a `main`.

## 🏗️ Arquitectura

El bot opera con dos componentes principales que se ejecutan concurrentemente:

1. **Bot de Discord (discord.py)**: Se conecta a Discord, carga el Cog de webhooks (`cogs/github_webhooks.py`) y mantiene la conexión con Discord.
2. **Servidor Web (aiohttp)**: Recibe los webhooks de GitHub en la ruta `/github-webhook` y envía notificaciones al canal de Discord configurado.

### Estructura del Proyecto

```
bot-discord-github/
│
├── cogs/
│   ├── __init__.py
│   └── github_webhooks.py    # Maneja webhooks y notificaciones
│
├── config.py                  # Carga variables de entorno
├── main.py                    # Punto de entrada del bot
├── requirements.txt           # Dependencias del proyecto
├── .env                       # Variables de entorno (no incluido en git)
└── README.md                  # Este archivo
```

## 📊 Tipos de Notificaciones

### Pull Requests

**PR Abierto** (Azul 🔵):
- Título del PR con enlace
- Autor con avatar
- Branch de origen
- Número de commits

**PR Merged** (Morado 🟣):
- Título del PR con enlace
- Usuario que hizo el merge con avatar
- Branch merged y branch destino
- Número de commits
- Autor original del PR

### Workflows

**Workflow Exitoso** (Verde 🟢):
- Nombre del workflow
- Branch ejecutado
- Actor que ejecutó el workflow
- Enlace al PR relacionado (si existe)

**Workflow Fallido** (Rojo 🔴):
- Nombre del workflow
- Branch ejecutado
- Actor que ejecutó el workflow
- Enlace al PR relacionado (si existe)

### Comentarios

**Comentario en PR** (Naranja 🟠):
- Título del PR
- Contenido del comentario (truncado si es muy largo)
- Autor del comentario con avatar

**Comentario de Revisión** (Naranja 🟠):
- Título del PR
- Contenido del comentario
- Archivo y línea comentada
- Autor del comentario con avatar

## 🛠️ Troubleshooting

- **Bot no se conecta a Discord**: Verifica que `DISCORD_TOKEN` en tu `.env` sea correcto y que el bot esté invitado al servidor.
- **No se reciben notificaciones de GitHub**:
  - Verifica que la URL del webhook en GitHub sea correcta y esté accesible desde internet.
  - Asegúrate de que `GITHUB_WEBHOOK_SECRET` coincida en GitHub y en tu `.env`.
  - Revisa que el puerto 8082 esté abierto y accesible.
  - Verifica que `TARGET_CHANNEL_ID` sea correcto.
- **Error de firma inválida**: El secret en GitHub y en tu `.env` deben coincidir exactamente.
- **Bot no tiene permisos**: Asegúrate de que el bot tenga permisos de "Send Messages" y "Embed Links" en el canal configurado.

## 🔒 Seguridad

- El archivo `.env` contiene información sensible y no debe ser compartido ni subido a repositorios públicos. Está incluido en `.gitignore` por defecto.
- Todos los webhooks de GitHub son validados mediante firma HMAC-SHA256 para garantizar su autenticidad.
- Nunca compartas tu `DISCORD_TOKEN` ni tu `GITHUB_WEBHOOK_SECRET`.

## 📝 Personalización

### Cambiar Puerto del Servidor

Define la variable de entorno `PORT` (por defecto `8082`):

```env
PORT=9000
```

### Cambiar Colores de Embeds

Edita las constantes de color en `cogs/github_webhooks.py`:

```python
COLOR_PR_OPEN = discord.Color.blue()
COLOR_PR_MERGED = discord.Color.purple()
COLOR_TEST_SUCCESS = discord.Color.green()
COLOR_TEST_FAILURE = discord.Color.red()
COLOR_COMMENT = discord.Color.orange()
```

### Agregar Nuevos Eventos

Para manejar eventos adicionales de GitHub:

1. Añade el evento en la configuración del webhook de GitHub.
2. Crea un nuevo método `handle_<event_name>` en `cogs/github_webhooks.py`.
3. Añade el enrutamiento en el método `_webhook_handler()`.

## 📜 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 👤 Autor

**R4F405**

- GitHub: [@R4F405](https://github.com/R4F405)

## 🙏 Agradecimientos

- [discord.py](https://github.com/Rapptz/discord.py) - Librería de Discord para Python
- [aiohttp](https://github.com/aio-libs/aiohttp) - Cliente/Servidor HTTP asíncrono
- [GitHub Webhooks Documentation](https://docs.github.com/en/developers/webhooks-and-events/webhooks) - Documentación oficial de webhooks