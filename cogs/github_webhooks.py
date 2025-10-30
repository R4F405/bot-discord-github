import discord
from discord.ext import commands
from aiohttp import web
import hmac
import hashlib
import config

COLOR_PR_OPEN = discord.Color.blue()
COLOR_PR_MERGED = discord.Color.purple()
COLOR_TEST_SUCCESS = discord.Color.green()
COLOR_TEST_FAILURE = discord.Color.red()
COLOR_COMMENT = discord.Color.orange()


class WebhookServerCog(commands.Cog):
    """Maneja la recepción y procesamiento de webhooks de GitHub mediante servidor aiohttp."""

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.web_server = None
        self.web_server_task = None
        self._target_channel = None
        self.web_server_task = self.bot.loop.create_task(self.start_web_server())

    async def get_target_channel(self) -> discord.TextChannel | None:
        """Obtiene y cachea el canal de destino configurado."""
        if self._target_channel is None:
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
        """Inicia el servidor web aiohttp en el puerto 8082."""
        app = web.Application()
        app.add_routes([web.post('/github-webhook', self._webhook_handler)])
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        port = 8082
        self.web_server = web.TCPSite(runner, '0.0.0.0', port)
        
        try:
            await self.web_server.start()
            print(f"Servidor de Webhooks iniciado en el puerto {port}...")
        except Exception as e:
            print(f"Error al iniciar el servidor web: {e}")

    async def _validate_signature(self, request: web.Request) -> bool:
        """Valida la firma HMAC de GitHub para verificar autenticidad del webhook."""
        signature_header = request.headers.get('X-Hub-Signature-256')
        if not signature_header:
            print("Petición de Webhook rechazada: Falta la cabecera X-Hub-Signature-256")
            return False

        body = await request.read()
        secret = config.GITHUB_WEBHOOK_SECRET.encode('utf-8')
        h = hmac.new(secret, body, hashlib.sha256)
        expected_signature = 'sha256=' + h.hexdigest()

        if not hmac.compare_digest(expected_signature, signature_header):
            print("Petición de Webhook rechazada: Firma inválida.")
            return False
            
        return True

    async def _webhook_handler(self, request: web.Request):
        """Procesa las peticiones webhook de GitHub y las enruta al manejador correspondiente."""
        if not await self._validate_signature(request):
            return web.Response(status=401, text="Invalid signature")

        event_type = request.headers.get('X-GitHub-Event')
        if not event_type:
            return web.Response(status=400, text="Missing X-GitHub-Event header")

        try:
            payload = await request.json()
        except Exception as e:
            print(f"Error al parsear JSON del webhook: {e}")
            return web.Response(status=400, text="Invalid JSON payload")

        print(f"Webhook recibido: {event_type}")
        if event_type == 'pull_request':
            await self.handle_pull_request(payload)
        elif event_type == 'workflow_run':
            await self.handle_workflow_run(payload)
        elif event_type == 'issue_comment':
            await self.handle_issue_comment(payload)
        elif event_type == 'pull_request_review_comment':
            await self.handle_pr_review_comment(payload)
        
        return web.Response(status=200, text="OK")

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

        if action == 'opened':
            embed = discord.Embed(
                title=f"New Pull Request: {pr['title']}",
                url=pr['html_url'],
                color=COLOR_PR_OPEN
            )
            embed.set_author(
                name=pr['user']['login'],
                icon_url=pr['user']['avatar_url'],
                url=pr['user']['html_url']
            )
            
            embed.add_field(name="Branch", value=f"`{pr['head']['ref']}`", inline=True)
            embed.add_field(name="Commits", value=str(pr['commits']), inline=True)
            embed.add_field(
                name="Author", 
                value=f"[{pr['user']['login']}]({pr['user']['html_url']})", 
                inline=True
            )
            
            embed.set_footer(text=f"PR #{payload.get('number')}")

        elif action == 'closed' and pr.get('merged') is True:
            embed = discord.Embed(
                title=f"Pull Request Merged: {pr['title']}",
                url=pr['html_url'],
                color=COLOR_PR_MERGED
            )
            
            merger = pr.get('merged_by')
            if merger:
                embed.set_author(
                    name=merger['login'],
                    icon_url=merger['avatar_url'],
                    url=merger['html_url']
                )
            
            embed.add_field(name="Branch Merged", value=f"`{pr['head']['ref']}`", inline=True)
            embed.add_field(name="To", value=f"`{pr['base']['ref']}`", inline=True)
            embed.add_field(name="Commits", value=str(pr['commits']), inline=True)
            embed.add_field(
                name="Author", 
                value=f"[{pr['user']['login']}]({pr['user']['html_url']})", 
                inline=True
            )

            embed.set_footer(text=f"PR #{payload.get('number')}")

        if embed:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(f"Error: El bot no tiene permisos para enviar mensajes en #{channel.name}")
            except Exception as e:
                print(f"Error al enviar embed: {e}")

    async def handle_issue_comment(self, payload: dict):
        """Procesa comentarios generales en pull requests."""
        action = payload.get('action')
        
        if action != 'created':
            return
        
        issue = payload.get('issue')
        if not issue or 'pull_request' not in issue:
            return
        
        comment = payload.get('comment')
        if not comment:
            return
        
        channel = await self.get_target_channel()
        if not channel:
            return
        
        comment_body = comment.get('body', '')
        if len(comment_body) > 1024:
            comment_body = comment_body[:1021] + "..."
        
        embed = discord.Embed(
            title=f"New Comment on PR: {issue['title']}",
            url=comment['html_url'],
            description=comment_body,
            color=COLOR_COMMENT
        )
        
        embed.set_author(
            name=comment['user']['login'],
            icon_url=comment['user']['avatar_url'],
            url=comment['user']['html_url']
        )
        
        embed.set_footer(text=f"PR #{issue['number']}")
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Error: El bot no tiene permisos para enviar mensajes en #{channel.name}")
        except Exception as e:
            print(f"Error al enviar embed: {e}")

    async def handle_pr_review_comment(self, payload: dict):
        """Procesa comentarios de revisión de código en pull requests."""
        action = payload.get('action')
        
        if action != 'created':
            return
        
        pull_request = payload.get('pull_request')
        comment = payload.get('comment')
        
        if not pull_request or not comment:
            return
        
        channel = await self.get_target_channel()
        if not channel:
            return
        
        comment_body = comment.get('body', '')
        if len(comment_body) > 1024:
            comment_body = comment_body[:1021] + "..."
        
        embed = discord.Embed(
            title=f"Review Comment on PR: {pull_request['title']}",
            url=comment['html_url'],
            description=comment_body,
            color=COLOR_COMMENT
        )
        
        embed.set_author(
            name=comment['user']['login'],
            icon_url=comment['user']['avatar_url'],
            url=comment['user']['html_url']
        )
        
        if comment.get('path'):
            embed.add_field(
                name="File",
                value=f"`{comment['path']}`",
                inline=True
            )
        
        if comment.get('line'):
            embed.add_field(
                name="Line",
                value=str(comment['line']),
                inline=True
            )
        
        embed.set_footer(text=f"PR #{pull_request['number']}")
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            print(f"Error: El bot no tiene permisos para enviar mensajes en #{channel.name}")
        except Exception as e:
            print(f"Error al enviar embed: {e}")

    async def handle_workflow_run(self, payload: dict):
        """Procesa eventos de ejecución de workflows de GitHub Actions."""
        action = payload.get('action')

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

        link_to_pr = ""
        if workflow_run.get('pull_requests') and len(workflow_run['pull_requests']) > 0:
            link_to_pr = workflow_run['pull_requests'][0].get('html_url')

        if not link_to_pr:
            link_to_pr = workflow_run.get('html_url', '#')

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


async def setup(bot: discord.Client):
    """Función de setup requerida por discord.py para cargar el cog."""
    await bot.add_cog(WebhookServerCog(bot))
