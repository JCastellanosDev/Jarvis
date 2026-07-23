"""Interfaces abstractas para integraciones externas: los intents dependen
de estos contratos (`ControlVersiones`, `Mensajeria`), no de la
implementación concreta de hoy (git + API pública de GitHub; WhatsApp
Desktop automatizado por AppleScript). Si GitHub cambia de API, si WhatsApp
Desktop cambia de interfaz y hay que reescribir la automatización, o si el
día de mañana se agrega otro canal (Telegram, iMessage), solo hace falta
una implementación nueva del contrato correspondiente — los intents que ya
lo usan no se tocan.

`Protocol` (no `ABC`) a propósito: es estructural, no hace falta heredar
explícitamente. Las clases de abajo son envolturas delgadas sobre las
funciones que YA existen en skills/ — no se les tocó el código, ni su
lógica ni (en el caso de whatsapp.py) su historial de bugs ya resueltos
documentado ahí mismo."""

from typing import Callable, Optional, Protocol, runtime_checkable

from skills.git_automation import subir_cambios_github
from skills.github_sync import sincronizar_repos
from skills.whatsapp import enviar_whatsapp


@runtime_checkable
class ControlVersiones(Protocol):
    def sincronizar(self) -> str:
        """Trae/actualiza el código de referencia. Devuelve un resumen para hablar."""
        ...

    def subir_cambios(self, ruta_repo: str, pedir_mensaje: Callable[[str], Optional[str]]) -> str:
        """git add + commit (mensaje pedido por voz) + push de `ruta_repo`."""
        ...


@runtime_checkable
class Mensajeria(Protocol):
    def enviar(self, destinatario: str, texto: str) -> str:
        """Manda `texto` a `destinatario`. Devuelve un resumen para hablar."""
        ...


class GitHubGit:
    """Implementación de hoy: API pública de GitHub para sincronizar repos
    (sin token, son públicos) + `git` de línea de comandos para subir
    cambios del repo local. Delega 100% en skills/github_sync.py y
    skills/git_automation.py, ya probados por separado."""

    def sincronizar(self) -> str:
        return sincronizar_repos()

    def subir_cambios(self, ruta_repo: str, pedir_mensaje: Callable[[str], Optional[str]]) -> str:
        return subir_cambios_github(ruta_repo, pedir_mensaje)


class WhatsAppDesktop:
    """Implementación de hoy: WhatsApp Desktop automatizado por
    AppleScript/Accesibilidad — ver skills/whatsapp.py para el porqué de
    cada decisión (documenta 5 iteraciones de bugs ya resueltos). Frágil a
    propósito documentado; esta envoltura no le cambia nada."""

    def enviar(self, destinatario: str, texto: str) -> str:
        return enviar_whatsapp(destinatario, texto)
