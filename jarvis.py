"""Punto de entrada de Jarvis: arma las dependencias (inyección de
dependencias) y ejecuta el bucle de voz. Toda la lógica vive en core/,
intents/, remoto/ y skills/ — este archivo solo los conecta."""

import os
import random
import socket
import subprocess
import threading
import time

from core.cerebro import CerebroOllama
from core.config import Settings, VOCES_DISPONIBLES
from core.contexto import IntentContext
from core.eco import es_eco_de_si_mismo
from core.hablante import Hablante
from core.memoria import MemoriaPersistente
from core.oyente import Oyente
from core.patrones import RegistradorPatrones
from core.wake_word import EscuchadorPalabraClave

from intents.acciones_skills import AccionesSkillsIntent
from intents.agregar_nota import AgregarNotaIntent
from intents.aplicaciones import AplicacionesIntent
from intents.apagado import ApagadoIntent
from intents.base import DetenerJarvis
from intents.buscar_codigo import BuscarCodigoIntent
from intents.busqueda_web import BusquedaWebIntent
from intents.cambio_voz import CambioVozIntent
from intents.chat_general import ChatGeneralIntent
from intents.descargas import DescargasIntent
from intents.enrutador import EnrutadorIntents
from intents.fecha_hora import FechaHoraIntent
from intents.github_sync import GithubSyncIntent
from intents.grafico_obsidian import GraficoObsidianIntent
from intents.instalador import InstaladorIntent
from intents.listar_voces import ListarVocesIntent
from intents.multimedia import MultimediaIntent
from intents.notificaciones import NotificacionesIntent
from intents.obsidian import ObsidianIntent
from intents.patrones import PatronesIntent
from intents.recordar import RecordarIntent
from intents.repetir import RepetirIntent

from skills.herramientas_agente import HERRAMIENTAS
from intents.video import VideoIntent
from intents.vision import VisionIntent
from intents.volumen import VolumenIntent
from intents.whatsapp import WhatsAppIntent

from remoto.servidor import iniciar_servidor_remoto

FRASES_SALUDO = [
    "Sistemas en línea. ¿Qué hacemos hoy?",
    "Listo para trabajar. Dime qué necesitas.",
    "Todo encendido por aquí. ¿En qué te ayudo?",
    "Jarvis activo. Adelante.",
    "De vuelta en línea. ¿Qué sigue?",
    "Aquí estoy. ¿Por dónde empezamos?",
]


def construir_enrutador():
    # Orden importa: los más específicos van primero, ChatGeneralIntent
    # siempre responde y cierra la cadena.
    return EnrutadorIntents([
        # RepetirIntent va primero: si está esperando la frase a repetir,
        # tiene que ganarle a CUALQUIER otro intent (incluido ApagadoIntent).
        RepetirIntent(),
        ApagadoIntent(),
        CambioVozIntent(VOCES_DISPONIBLES),
        ListarVocesIntent(VOCES_DISPONIBLES),
        FechaHoraIntent(),
        VisionIntent(),
        PatronesIntent(),
        RecordarIntent(),
        AgregarNotaIntent(),
        WhatsAppIntent(),
        DescargasIntent(),
        InstaladorIntent(),
        NotificacionesIntent(),
        VolumenIntent(),
        MultimediaIntent(),
        VideoIntent(),
        AccionesSkillsIntent(),
        # GraficoObsidianIntent va ANTES que AplicacionesIntent a propósito:
        # el patrón genérico "abre <app>" de AplicacionesIntent matchea
        # cualquier "abre ..." (incluido "abre el grafo de mis notas") y
        # trataba de abrir una app inexistente con ese nombre.
        GraficoObsidianIntent(),
        AplicacionesIntent(),
        GithubSyncIntent(),
        ObsidianIntent(),
        BuscarCodigoIntent(),
        BusquedaWebIntent(),
        ChatGeneralIntent(),
    ])


def crear_pedir_texto_por_voz(hablante, oyente):
    def pedir_texto_por_voz(pregunta):
        hablante.hablar(pregunta)
        return oyente.escuchar()
    return pedir_texto_por_voz


def _esperar_puerto_listo(puerto, intentos=30, espera=0.1):
    """Sondea el puerto en vez de dormir un tiempo fijo: abre en cuanto Flask
    esté realmente listo (normalmente en milisegundos), no siempre 0.8s."""
    for _ in range(intentos):
        try:
            with socket.create_connection(("127.0.0.1", puerto), timeout=0.2):
                return True
        except OSError:
            time.sleep(espera)
    return False


def abrir_panel_como_app(url, puerto):
    """Abre el panel en Brave. Si Brave está cerrado, lo abre en modo app
    (--app: sin barra de direcciones ni pestañas, se ve como una app nativa).
    Si Brave YA está corriendo, macOS ignora los argumentos de lanzamiento y
    solo activa la ventana existente sin abrir nada nuevo — en ese caso se
    abre una pestaña normal, que sí funciona siempre."""
    _esperar_puerto_listo(puerto)
    try:
        ya_corriendo = subprocess.run(
            ["pgrep", "-x", "Brave Browser"], capture_output=True
        ).returncode == 0

        if ya_corriendo:
            subprocess.Popen(["open", "-a", "Brave Browser", url])
        else:
            subprocess.Popen(["open", "-a", "Brave Browser", "--args", f"--app={url}"])
    except Exception as e:
        print(f"[Jarvis] No pude abrir el panel automáticamente: {e}")


def main():
    print("========================================")
    print("     SISTEMA JARVIS M2 INICIALIZADO     ")
    print("========================================")

    settings = Settings.desde_env()

    hablante = Hablante(
        settings.elevenlabs_api_key, settings.voice_id,
        forzar_voz_sistema=settings.forzar_voz_sistema,
    )
    oyente = Oyente()
    memoria = MemoriaPersistente(settings.memoria_file, settings.max_turnos_contexto)
    cerebro = CerebroOllama(
        settings.modelo_ollama, herramientas=HERRAMIENTAS, modelo_herramientas=settings.modelo_herramientas,
    )
    registrador_patrones = RegistradorPatrones()

    if memoria.historial_completo:
        print(
            f"[Jarvis] Memoria recuperada: {len(memoria.historial_completo) // 2} turno(s) "
            "desde que existo, retomando los más recientes."
        )
    if memoria.hechos:
        print(f"[Jarvis] {len(memoria.hechos)} dato(s) permanentes cargados.")

    ctx_skills = {
        "ruta_repo": os.path.dirname(os.path.abspath(__file__)),
        "pedir_texto_por_voz": crear_pedir_texto_por_voz(hablante, oyente),
        "puerto_remoto": settings.puerto_remoto,
    }
    ctx = IntentContext(
        hablante=hablante, memoria=memoria, cerebro=cerebro, ctx_skills=ctx_skills,
        registrador_patrones=registrador_patrones,
    )

    enrutador = construir_enrutador()

    # El servidor arranca PRIMERO: así el arrancador remoto (que solo sondea
    # este puerto) reporta "encendido" en cuanto Flask levanta, sin esperar
    # a que Ollama termine de calentar — eso es lo que hacía sentir lento el
    # encendido desde el celular.
    iniciar_servidor_remoto(enrutador, ctx, hablante, puerto=settings.puerto_remoto, token=settings.token_remoto)
    print(f"[Jarvis] Panel visual: http://localhost:{settings.puerto_remoto}/panel (ábrelo en un navegador de la Mac)")
    print(f"[Jarvis] Control remoto (celular, misma Wi-Fi): http://<IP-local-de-tu-Mac>:{settings.puerto_remoto}")
    print(f"[Jarvis] Control remoto (fuera de casa, vía Tailscale): http://100.122.133.65:{settings.puerto_remoto}")
    if settings.token_remoto:
        print("[Jarvis] Control remoto protegido con token (JARVIS_REMOTE_TOKEN).")

    threading.Thread(target=cerebro.calentar, daemon=True).start()

    url_panel = f"http://localhost:{settings.puerto_remoto}/panel"
    threading.Thread(target=abrir_panel_como_app, args=(url_panel, settings.puerto_remoto), daemon=True).start()

    escuchador_palabra_clave = None
    if settings.wake_word_activo:
        try:
            escuchador_palabra_clave = EscuchadorPalabraClave()
            print("[Jarvis] Wake word activo ('Hey Jarvis'): no proceso nada hasta que lo digas.")
        except Exception as e:
            print(f"[Jarvis] No pude activar el wake word ({e}). Sigo sin él: proceso todo lo que oiga.")

    hablante.hablar(random.choice(FRASES_SALUDO))

    try:
        while True:
            if escuchador_palabra_clave:
                print("[Jarvis] Esperando 'Hey Jarvis'...")
                try:
                    escuchador_palabra_clave.esperar()
                except Exception as e:
                    print(f"[Jarvis] Wake word falló en caliente ({e}). Sigo esta vez sin él.")
                else:
                    hablante.hablar("Dime.")

            texto_usuario = oyente.escuchar()
            if not texto_usuario:
                continue

            if es_eco_de_si_mismo(texto_usuario, hablante.ultimo_texto_hablado):
                print(f"[Jarvis] Ignorando eco de mi propia voz: '{texto_usuario}'")
                continue

            detener = False
            with ctx.lock:
                try:
                    respuesta = enrutador.procesar(texto_usuario, ctx)
                except DetenerJarvis as e:
                    hablante.hablar(e.mensaje_despedida)
                    detener = True
                else:
                    if respuesta:
                        hablante.hablar(respuesta)

            if detener:
                break
    finally:
        memoria.guardar()
        if escuchador_palabra_clave:
            escuchador_palabra_clave.cerrar()


if __name__ == '__main__':
    main()
