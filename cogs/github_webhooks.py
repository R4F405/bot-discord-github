import discord
from discord.ext import commands
from aiohttp import web
import hmac
import hashlib
import config  # Importamos nuestra config

# --- Constantes de Colores para Embeds ---
COLOR_PR_OPEN = discord.Color.blue()
COLOR_PR_MERGED = discord.Color.purple()
COLOR_TEST_SUCCESS = discord.Color.green()
COLOR_TEST_FAILURE = discord.Color.red()


class WebhookServerCog(commands.Cog):
    """
    Este Cog maneja la recepción y procesamiento de Webhooks de GitHub.
    Inicia un servidor web aiohttp para escuchar en un puerto específico.
    """

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.web_server = None
        self.web_server_task = None
        # Cacheamos el canal para no tener que buscarlo cada vez
        self._target_channel = None
        
        # Creamos una tarea en el loop del bot para iniciar el servidor web
        self.web_server_task = self.bot.loop.create_task(self.start_web_server())

    async def get_target_channel(self) -> discord.TextChannel | None:
        """Obtiene y cachea el objeto del canal de destino."""
        if self._target_channel is None:
            # Esperamos a que el bot esté listo antes de buscar el canal
            await self.bot.wait_until_ready()
            
            channel = self.bot.get_channel(config.TARGET_CHANNEL_ID)
            if channel is None:
                print(f"Error: No se pudo encontrar el canal con ID {config.TARGET_CHANNEL_ID}")
                return None
            if not isinstance(channel, discord.TextChannel):
                print(f"Error: El ID {config.TARGET_CHANNEL_ID} no es un canal de texto.")
                return None
            
            self._target_channel = channel
            print(f"Canal de notificaciones configurado: #{channel.name}")
            
        return self._target_channel

    async def cog_unload(self):
        """Limpia el servidor web cuando el Cog se descarga."""
        if self.web_server:
            await self.web_server.cleanup()
            print("Servidor web de webhooks detenido.")

    async def start_web_server(self):
        """Inicia el servidor web aiohttp."""
        app = web.Application()
        # Definimos la ruta que coincide con la URL del Webhook en GitHub
        app.add_routes([web.post('/github-webhook', self._webhook_handler)])
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        # El servidor escucha en todas las IPs ('0.0.0.0') en el puerto 8081
        # Puedes cambiar el puerto si es necesario.
        port = 8081
        self.web_server = web.TCPSite(runner, '0.0.0.0', port)
        
        try:
            await self.web_server.start()
            print(f"Servidor de Webhooks iniciado en el puerto {port}...")
        except Exception as e:
            print(f"Error al iniciar el servidor web: {e}")

    async def _validate_signature(self, request: web.Request) -> bool:
        """
        Valida la firma de GitHub para asegurar que la petición es legítima.
        """
        signature_header = request.headers.get('X-Hub-Signature-256')
        if not signature_header:
            print("Petición de Webhook rechazada: Falta la cabecera X-Hub-Signature-256")
            return False

        # Obtenemos el cuerpo de la petición en bytes
        body = await request.read()
        
        # Calculamos nuestro hash HMAC
        secret = config.GITHUB_WEBHOOK_SECRET.encode('utf-8')
        h = hmac.new(secret, body, hashlib.sha256)
        expected_signature = 'sha256=' + h.hexdigest()

        # Usamos hmac.compare_digest para una comparación segura
        if not hmac.compare_digest(expected_signature, signature_header):
            print("Petición de Webhook rechazada: Firma inválida.")
            return False
            
        return True

    async def _webhook_handler(self, request: web.Request):
        """
        Manejador principal para todas las peticiones POST a /github-webhook.
        """
        # 1. Validar la firma
        if not await self._validate_signature(request):
            return web.Response(status=401, text="Invalid signature")

        # 2. Obtener el tipo de evento
        event_type = request.headers.get('X-GitHub-Event')
        if not event_type:
            return web.Response(status=400, text="Missing X-GitHub-Event header")

        # 3. Obtener el payload JSON
        try:
            payload = await request.json()
        except Exception as e:
            print(f"Error al parsear JSON del webhook: {e}")
            return web.Response(status=400, text="Invalid JSON payload")

        # 4. Enrutar el evento al manejador correcto
        print(f"Webhook recibido: {event_type}")
        if event_type == 'pull_request':
            await self.handle_pull_request(payload)
        elif event_type == 'workflow_run':
            await self.handle_workflow_run(payload)
        
        # 5. Responder a GitHub que todo está OK
        return web.Response(status=200, text="OK")

    # --- Manejadores de Eventos Específicos ---


    async def handle_pull_request(self, payload: dict):
        """Procesa eventos de Pull Request."""
        action = payload.get('action')
        pr = payload.get('pull_request')
        if not pr:
            return

        channel = await self.get_target_channel()
        if not channel:
            return

        embed = None

        # Evento: Nuevo PR Abierto
        if action == 'opened':
            
            
            embed = discord.Embed(
                title=f"New Pull Request: {pr['title']}", # <-- Formato de la imagen
                url=pr['html_url'],
                color=COLOR_PR_OPEN
            )
            # Autor del embed: El usuario que abrió el PR
            embed.set_author(
                name=pr['user']['login'], # <-- Formato de la imagen
                icon_url=pr['user']['avatar_url'],
                url=pr['user']['html_url']
            )
            
            embed.add_field(name="Branch", value=f"`{pr['head']['ref']}`", inline=True)
            embed.add_field(name="Commits", value=str(pr['commits']), inline=True)

            # Este campo es redundante con set_author, pero es lo solicitado.
            embed.add_field(
                name="Author", 
                value=f"[{pr['user']['login']}]({pr['user']['html_url']})", 
                inline=True
            )
            
            embed.set_footer(text=f"PR #{payload.get('number')}") # <-- Formato de la imagen


        # Evento: PR Merged
        elif action == 'closed' and pr.get('merged') is True:
            
            
            embed = discord.Embed(
                title=f"Pull Request Merged: {pr['title']}",
                url=pr['html_url'],
                color=COLOR_PR_MERGED
            )
            
            merger = pr.get('merged_by')
            if merger:
                 # Autor del embed: El usuario que hizo el merge
                 embed.set_author(
                    name=merger['login'],
                    icon_url=merger['avatar_url'],
                    url=merger['html_url']
                )
            
            embed.add_field(name="Branch Merged", value=f"`{pr['head']['ref']}`", inline=True)
            embed.add_field(name="To", value=f"`{pr['base']['ref']}`", inline=True)
            embed.add_field(name="Commits", value=str(pr['commits']), inline=True)

            # Aquí añadimos al autor *original* del PR
            embed.add_field(
                name="Author", 
                value=f"[{pr['user']['login']}]({pr['user']['html_url']})", 
                inline=True
            )

            embed.set_footer(text=f"PR #{payload.get('number')}") # <-- Formato de la imagen

        # Si creamos un embed, lo enviamos
        if embed:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(f"Error: El bot no tiene permisos para enviar mensajes en #{channel.name}")
            except Exception as e:
                print(f"Error al enviar embed: {e}")

    async def handle_workflow_run(self, payload: dict):
        """Procesa eventos de Workflow Run."""
        action = payload.get('action')
        
        # Solo nos interesa cuando un workflow se completa
        if action != 'completed':
            return
            
        workflow_run = payload.get('workflow_run')
        workflow = payload.get('workflow')
        if not workflow_run or not workflow:
            return

        channel = await self.get_target_channel()
        if not channel:
            return
            
        conclusion = workflow_run.get('conclusion')
        
        # El link en tus ejemplos parece ser el del PR.
        # El payload de 'workflow_run' incluye los PRs asociados.
        link_to_pr = ""
        if workflow_run['pull_requests'] and len(workflow_run['pull_requests']) > 0:
            link_to_pr = workflow_run['pull_requests'][0]['html_url']
        else:
            # Si no hay PR, linkeamos a la propia ejecución del workflow
            link_to_pr = workflow_run['html_url']

        embed = None

        if conclusion == 'success':
            embed = discord.Embed(
                title=f"Workflow Run Succeeded: {workflow['name']}",
                url=link_to_pr,
                color=COLOR_TEST_SUCCESS
            )
            embed.add_field(name="Branch", value=f"`{workflow_run['head_branch']}`", inline=True)
            embed.add_field(name="Conclusion", value="✅ Success", inline=True)

        elif conclusion == 'failure':
            embed = discord.Embed(
                title=f"Workflow Run Failed: {workflow['name']}",
                url=link_to_pr,
                color=COLOR_TEST_FAILURE
            )
            embed.add_field(name="Branch", value=f"`{workflow_run['head_branch']}`", inline=True)
            embed.add_field(name="Conclusion", value="❌ Failure", inline=True)

        # Enviamos el embed si es 'success' o 'failure'
        if embed:
            embed.set_author(
                name=workflow_run['actor']['login'],
                icon_url=workflow_run['actor']['avatar_url'],
                url=workflow_run['actor']['html_url']
            )
            embed.set_footer(text=f"Workflow Run ID: {workflow_run['id']}")
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(f"Error: El bot no tiene permisos para enviar mensajes en #{channel.name}")
            except Exception as e:
                print(f"Error al enviar embed: {e}")


# Esta función 'setup' es la que discord.py busca al cargar una extensión
async def setup(bot: discord.Client):
    await bot.add_cog(WebhookServerCog(bot))