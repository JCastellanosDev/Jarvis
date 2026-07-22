"""Habilidad 6: avisos de estatus al equipo de universidad por correo (Gmail SMTP)."""

import os
import smtplib
from email.mime.text import MIMEText

# --- PERSONALIZA los correos reales ---
EQUIPO = {
    "angel": "angel@example.com",
    "chuy": "chuy@example.com",
    "samuel": "samuel@example.com",
    "jorge axel lares estrada": "jorge.lares@example.com",
}

# Requiere en tu .env:
#   GMAIL_REMITENTE=tu_correo@gmail.com
#   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (Contraseña de aplicación, no tu clave normal:
#   https://myaccount.google.com/apppasswords, necesita verificación en dos pasos activa)
REMITENTE = os.getenv("GMAIL_REMITENTE")
CLAVE_APP = os.getenv("GMAIL_APP_PASSWORD")

MENSAJE_POR_DEFECTO = "Terminé mi parte del proyecto, ya pueden continuar."


def avisar_equipo(mensaje=MENSAJE_POR_DEFECTO):
    if not REMITENTE or not CLAVE_APP:
        return "Falta configurar GMAIL_REMITENTE y GMAIL_APP_PASSWORD en el .env"

    destinatarios = list(EQUIPO.values())

    email = MIMEText(mensaje)
    email["Subject"] = "Actualización de estatus del proyecto"
    email["From"] = REMITENTE
    email["To"] = ", ".join(destinatarios)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(REMITENTE, CLAVE_APP)
            servidor.sendmail(REMITENTE, destinatarios, email.as_string())
        return f"Aviso enviado a {len(destinatarios)} compañeros."
    except Exception as e:
        return f"No pude enviar el aviso: {e}"
