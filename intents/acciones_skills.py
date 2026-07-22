"""Envuelve el router de skills previamente existente (dev_entorno,
git_automation, melo_db, habitos, entretenimiento, equipo) como un intent más
de la cadena, para no duplicar esa lógica de enrutamiento por palabra clave."""

from skills.router import enrutar_comando

from .base import Intent


class AccionesSkillsIntent(Intent):
    def manejar(self, texto, ctx):
        return enrutar_comando(texto, ctx.ctx_skills)
