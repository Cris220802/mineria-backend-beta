from mailersend import emails
import os
from dotenv import load_dotenv
from datetime import datetime
from  babel.dates import format_datetime

load_dotenv()

mailer = emails.NewEmail(os.getenv('API_KEY_MAILSENDER'))

async def send_notification(users, essay_id, essay_date, essay_shift) -> bool:
    try:
        fecha_formateada = format_datetime(essay_date, "d 'de' MMMM 'de' yyyy", locale='es_ES')

        subject = f"Ensaye #{essay_id}, {fecha_formateada}. Ya disponible."

        text = f"""
        Estimado Supervisor,

        Nos complace informarle que el ensayo realizado el {fecha_formateada} en el turno {essay_shift} ha sido subido exitosamente al sistema.
        Los resultados están ahora disponibles para su análisis.
        """

        # Cuerpo del correo en HTML
        html = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                <title>Notificación de Ensayo</title>
                <style type="text/css">
                    /* Estilos generales que algunos clientes respetan */
                    body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
                    table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
                    img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
                    body {{ height: 100% !important; margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: #f5f5f5; }}

                    /* Ocultar preheader */
                    .preheader {{
                        display: none !important;
                        visibility: hidden;
                        opacity: 0;
                        color: transparent;
                        height: 0;
                        width: 0;
                    }}

                    /* Estilos para el botón que algunos clientes pueden usar */
                    .button-td a:hover {{
                        background-color: #011638 !important;
                    }}
                </style>
            </head>
            <body style="margin: 0 !important; padding: 0 !important; background-color: #f5f5f5;">

                <div class="preheader" style="display: none; max-height: 0; max-width: 0; opacity: 0; overflow: hidden; mso-hide: all; font-size: 1px; line-height: 1px; color: #fff;">
                    Resultados del ensayo del {fecha_formateada} disponibles.
                </div>

                <table border="0" cellpadding="0" cellspacing="0" width="100%">
                    <tr>
                        <td align="center" style="background-color: #f5f5f5; padding: 20px 0;">
                            <table border="0" cellpadding="0" cellspacing="0" width="600" style="width: 100%; max-width: 600px;">
                                <tr>
                                    <td align="left" style="background-color: #ffffff; padding: 20px 30px;">
                                        <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                            <tr>
                                                <td style="font-family: Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #333333;">
                                                    <p style="margin: 0 0 15px 0;">Estimado Supervisor,</p>
                                                    <p style="margin: 0 0 15px 0;">Nos complace informarle que el ensayo realizado el <strong>{fecha_formateada}</strong> en el turno <strong>{essay_shift}</strong> ha sido subido exitosamente al sistema. Los resultados están ahora disponibles para su análisis.</p>
                                                    <p style="margin: 0 0 25px 0;">Puede acceder a los resultados a través de la plataforma en cualquier momento.</p>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td align="center" class="button-td">
                                                    <a href="https://www.mineriapp.com/login" target="_blank" style="display: inline-block; background-color: #0D21A1; color: #FFFFFF !important; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; text-decoration: none; padding: 12px 25px; border-radius: 5px;">Acceder a la Plataforma</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="background-color: #ffffff; padding: 30px; border-radius: 0 0 10px 10px;">
                                        <p style="margin: 0; font-family: Arial, sans-serif; font-size: 12px; line-height: 1.5; color: #777777;">
                                            Este es un correo automático, por favor no responda a este mensaje.<br>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
        """

         # Define el remitente una sola vez
        mail_from = {
            "name": "Equipo de Análisis de MinerIA", # Un nombre más descriptivo
            "email": os.getenv('SENDER_EMAIL'),
        }

        all_successful = True

        # Crear el diccionario de cuerpo del correo
        mail_body = {}

        recipients = [
            {
                "name": "Cristopher Velazquez",
                "email": "isareach779@gmail.com",
            }
        ]
        # Configurar el correo
        mailer.set_mail_from(mail_from, mail_body)
        mailer.set_mail_to(recipients, mail_body)
        mailer.set_subject(subject, mail_body)
        mailer.set_html_content(html, mail_body)
        mailer.set_plaintext_content(text, mail_body)

        # Enviar el correo
        response = mailer.send(mail_body)
        print(response)
        # responses.append(response)
        # print(responses)

        # Enviar el correo a cada usuario en la lista
        # responses = []

        # for user in users:
        #     # Definir los destinatarios
        #     recipients = [
        #         {
        #             "name": user.name,
        #             "email": user.email,
        #         }
        #     ]

        #     # Crear el diccionario de cuerpo del correo
        #     mail_body = {}

        #     # Configurar el correo
        #     mailer.set_mail_from(mail_from, mail_body)
        #     mailer.set_mail_to(recipients, mail_body)
        #     mailer.set_subject(subject, mail_body)
        #     mailer.set_html_content(html, mail_body)
        #     mailer.set_plaintext_content(text, mail_body)

        #     # Enviar el correo
        #     response = mailer.send(mail_body)
        #     responses.append(response)
        #     print(responses)
        # if response == 202 or response == "202":
        return True
        # else:
        #     return False

    except Exception as e:
        print(f"Error simulado al enviar email: {e}")
        return False # Simula fallo
