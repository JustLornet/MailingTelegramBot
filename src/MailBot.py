import smtplib
from email.mime.multipart import MIMEMultipart
import time
from threading import Thread, Event
from smtplib import SMTPRecipientsRefused, SMTPServerDisconnected, SMTPDataError, SMTPSenderRefused


class MailBot(object):
    def __init__(self, dest_mail: str):
        self.__mail_bot_container = {}
        self.__dest_mail = dest_mail

    async def login_mails(self, mails):
        for mail in mails:
            msg = MIMEMultipart()
            msg['Subject'] = 'From EthermailBot'
            msg['From'] = mail[1]
            msg['To'] = self.__dest_mail
            mail_bot = self.handle_mail(mail[1])
            mail_bot.login(msg['From'], mail[2])
            event = Event()
            self.__mail_bot_container.update({
                # e-mail name: mime message, smtp connection, token for canceling thread, e-mail password
                mail[1]: (msg, mail_bot, event, mail[2])
            })

    def handle_mail(self, mail: str):
        if mail.__contains__('mail.ru'):
            return smtplib.SMTP_SSL('smtp.mail.ru', 465)
        elif mail.__contains__('yandex.ru'):
            return smtplib.SMTP_SSL('smtp.yandex.ru', 465)
        elif mail.__contains__('gmail.com'):
            return smtplib.SMTP_SSL('smtp.gmail.com', 465)

    async def add_dest_mail(self, mail):
        """TODO: доделать присвоение почты от ethermail"""
        pass

    async def start_bot(self):
        def mail_cycle(cur_mail_bot, cur_mime_msg, cur_event):
            counter = 0
            while True:
                try:
                    is_stop = cur_event.is_set()
                    if is_stop:
                        break
                    cur_mail_bot.sendmail(cur_mime_msg['From'], cur_mime_msg['To'], cur_mime_msg.as_string())
                    counter += 1
                    print(f'{counter} messages sent from {cur_mime_msg["From"]}')
                    time.sleep(7)
                except SMTPRecipientsRefused:
                    print(f'SMTPRecipientsRefused to {cur_mime_msg["From"]}')
                    time.sleep(45*60)
                except SMTPServerDisconnected:
                    print(f'SMTPServerDisconnected to {cur_mime_msg["From"]}')
                    time.sleep(15 * 60)
                    self.restart_bot(cur_mail_bot, cur_mime_msg, cur_event)
                except SMTPDataError:
                    print(f"SMTPDataError, ${cur_mime_msg['From']} was stopped for 24 hours")
                    time.sleep(2 * 60 * 60)
                    self.restart_bot(cur_mail_bot, cur_mime_msg, cur_event)
                except SMTPSenderRefused:
                    print(f'SMTPSenderRefused to {cur_mime_msg["From"]}')
                    time.sleep(15 * 60)
                    self.restart_bot(cur_mail_bot, cur_mime_msg, cur_event)
        for key in self.__mail_bot_container:
            mime_msg = self.__mail_bot_container[key][0]
            mail_bot = self.__mail_bot_container[key][1]
            event = self.__mail_bot_container[key][2]
            thread = Thread(target=mail_cycle, args=(mail_bot, mime_msg, event, ))
            print(f'Bot for {mime_msg["From"]} has started')
            thread.start()

    def restart_bot(self, cur_mail_bot, cur_mime_msg, cur_event):
        mail = cur_mime_msg['From']
        cur_mail_bot = self.handle_mail(mail)
        cur_mail_bot.login(mail, self.__mail_bot_container[mail][3])

    async def stop_bot(self):
        for key in self.__mail_bot_container:
            event = self.__mail_bot_container[key][2]
            event.set()
            mail_bot = self.__mail_bot_container[key][1]
            mail_bot.quit()
