from mailersend import emails
import os
from dotenv import load_dotenv
from datetime import datetime
import locale

locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

load_dotenv()

mailer = emails.NewEmail(os.getenv('API_KEY_MAILSENDER'))

async def send_notification(users, essay_id, essay_date, essay_shift) -> bool:
    try:
        # Formatear la fecha en español
        fecha_formateada = essay_date.strftime('%d de %B de %Y') 

        # Formatear la hora por separado
        hora_formateada = essay_date.strftime('%H:%M:%S')
        
        subject = f"Ensaye #{essay_id}, {fecha_formateada}. Ya disponible."
        
        text = f"""
        Estimado Supervisor,

        Nos complace informarle que el ensayo realizado el {fecha_formateada} en el turno {essay_shift} ha sido subido exitosamente al sistema. 
        Los resultados están ahora disponibles para su análisis.
        """

        # Cuerpo del correo en HTML
        html = f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: 'Arial', sans-serif;
                        margin: 0;
                        padding: 0;
                        background-color: #f5f5f5;
                    }}
                    .email-container {{
                        width: 100%;
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #ffffff;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        text-align: center;
                        padding-bottom: 20px;
                    }}
                    .header img {{
                        width: 120px;
                        height: auto;
                    }}
                    .content {{
                        font-size: 16px;
                        line-height: 1.6;
                        color: #333;
                        padding-bottom: 20px;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #0D21A1;
                        color: #FFFFFF;
                        padding: 12px 20px;
                        text-align: center;
                        text-decoration: none;
                        border-radius: 5px;
                        font-size: 16px;
                        margin-top: 20px;
                        transition: background-color 0.3s;
                    }}
                    .button:hover {{
                        background-color: #011638;
                    }}
                    .footer {{
                        text-align: center;
                        font-size: 12px;
                        color: #777;
                        padding-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="header">
                        <!-- Aquí va el logo de la app -->
                        <img src="https://www.tuapp.com/logo.png" alt="Logo de la App" />
                    </div>
                    <div class="content">
                        <p>Estimado Supervisor,</p>
                        <p>Nos complace informarle que el ensayo realizado el <strong>{fecha_formateada}</strong> a las <strong>{hora_formateada}</strong> en el turno <strong>{essay_shift}</strong> ha sido subido exitosamente al sistema. Los resultados están ahora disponibles para su análisis.</p>
                        <p>Puede acceder a los resultados a través de la plataforma en cualquier momento.</p>
                        <a href="https://www.tuapp.com/login" class="button">Acceder a la Plataforma</a>
                    </div>
                    <div class="footer">
                        <p>Este es un correo automático, por favor no responda a este mensaje.</p>
                    </div>
                </div>
            </body>
        </html>
        """

        mail_from = {
            "name": "Equipo de Análisis",
            "email": os.getenv('SENDER_EMAIL'),
        }
        
        # Enviar el correo a cada usuario en la lista
        responses = []
        for user in users:
            # Definir los destinatarios
            recipients = [
                {
                    "name": user.name,
                    "email": user.email,
                }
            ]
            
            # Crear el diccionario de cuerpo del correo
            mail_body = {}

            # Configurar el correo
            mailer.set_mail_from(mail_from, mail_body)
            mailer.set_mail_to(recipients, mail_body)
            mailer.set_subject(subject, mail_body)
            mailer.set_html_content(html, mail_body)
            mailer.set_plaintext_content(text, mail_body)
            
            # Enviar el correo
            response = mailer.send(mail_body)
            responses.append(response)
            print(responses)
        
        return True
    except Exception as e:
        print(f"Error simulado al enviar email: {e}")
        return False # Simula fallo
