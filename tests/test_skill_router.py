"""skills/router.py es el router "legado" (dev_entorno, git_automation vía
ControlVersiones, melo_db, habitos, entretenimiento, equipo) envuelto como
AccionesSkillsIntent. Aquí solo se cubre el wiring de "sube los cambios a
github" hacia la interfaz ControlVersiones — el resto de comandos ya tenía
su propia cobertura indirecta a través de los skills individuales."""

from unittest.mock import MagicMock

from skills.router import enrutar_comando


def _ctx(control_versiones=None):
    return {
        "ruta_repo": "/ruta/falsa",
        "pedir_texto_por_voz": lambda pregunta: "arreglo bug",
        **({"control_versiones": control_versiones} if control_versiones else {}),
    }


def test_sube_cambios_usa_el_control_versiones_inyectado():
    control_falso = MagicMock()
    control_falso.subir_cambios.return_value = "Cambios subidos a GitHub."

    resultado = enrutar_comando("sube los cambios a github", _ctx(control_falso))

    assert resultado == "Cambios subidos a GitHub."
    args = control_falso.subir_cambios.call_args.args
    assert args[0] == "/ruta/falsa"
    assert args[1]("cualquier pregunta") == "arreglo bug"


def test_sube_cambios_sin_inyectar_nada_usa_la_implementacion_real_por_defecto():
    from core.integraciones import GitHubGit
    from skills.router import _CONTROL_VERSIONES_POR_DEFECTO
    assert isinstance(_CONTROL_VERSIONES_POR_DEFECTO, GitHubGit)


def test_variantes_de_frase_para_subir_cambios():
    control_falso = MagicMock()
    control_falso.subir_cambios.return_value = "listo"
    for frase in ["sube los cambios a git", "sube cambios a github", "sube el proyecto a github"]:
        assert enrutar_comando(frase, _ctx(control_falso)) == "listo"
