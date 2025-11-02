import sys
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt
from panel import Ui_MainWindow
from qasync import QEventLoop, asyncSlot
from func import telegram_panel
from code_dialog import CodeDialog, AsyncMessageBox
from pyrogram import (Client,errors,enums)
import os, random, shutil, sqlite3, traceback , time , json , re
from datetime import datetime

os.makedirs('data', exist_ok=True)
os.makedirs('account', exist_ok=True)
os.makedirs('masssages', exist_ok=True)
os.makedirs('delete', exist_ok=True)


Status = False
Extract = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        
        self.ui.setupUi(self)
        self.setFixedSize(self.size())
        self.acclistupdate()
        self.update_list_channel_remove()
        self.ui.add_account.clicked.connect(self.add_account_proc)
        self.ui.remove_account_bot.clicked.connect(self.remove_account)
        self.ui.update_number_bot.clicked.connect(self.acclistupdate)
        self.ui.extract_bot.clicked.connect(self.extract_channel)
        self.ui.stop_extract.clicked.connect(self.disable_extract_channel)
        self.ui.rem_extract_bot.clicked.connect(self.remove_extract_channel)
        self.ui.tab_account.currentChanged.connect(self.update_list_tab)

    
    
    
    def update_list_tab(self, index):
        if index == 0:
            r = telegram_panel.list_accounts()
            self.ui.list_account_ac.clear()
            self.ui.list_account_ac.addItems(r)
            self.ui.lcdNumber.display(len(r))
        if index == 1:
            r = telegram_panel.list_channel()
            self.ui.list_channel_rem.clear()
            self.ui.list_channel_rem.addItems(r)
            r = telegram_panel.list_accounts()
            self.ui.accselect.clear()
            self.ui.accselect.addItems(r)
        return
    
    
    
    @asyncSlot()
    async def ask_code_dialog(self, title, label):
        dlg = CodeDialog(title, label, self)
        dlg.setModal(True)
        dlg.show()
        while dlg.result() == 0:  # QDialog.DialogCode.Rejected = 0, Accepted = 1
            await asyncio.sleep(0.1)

        if dlg.result() == 1:
            return dlg.get_value(), True
        else:
            return "", False
    
    
    @asyncSlot()
    async def show_async_message(self, title, message, icon=QMessageBox.Icon.Information):
        dlg = AsyncMessageBox(title, message, icon, self)
        dlg.show()

        while dlg.result is None:
            await asyncio.sleep(0.05)

        return dlg


    def do_long_task(self):
        dlg = QProgressDialog("Processing ...", None, 0, 0, self)
        dlg.setWindowTitle("Please wait.")
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setMinimumDuration(0)
        dlg.show()
        return dlg


    @asyncSlot()
    async def add_account_proc(self):
        phone = self.ui.account_input_add.text().strip()

        if len(phone) < 4:
            # QMessageBox.critical(self, "Wrong", "Phone number is too short.")
            await self.show_async_message("Wrong", "Phone number is too short.", icon=QMessageBox.Icon.Critical)

            return

        if not phone.startswith("+") or not phone[1:].isdigit():
            # QMessageBox.critical(self, "Wrong", "Phone number must start with '+' and contain only digits after it.")
            await self.show_async_message("Wrong", "Phone number must start with '+' and contain only digits after it.", icon=QMessageBox.Icon.Critical)
            return

        if phone == "+123456789":
            # QMessageBox.critical(self, "Wrong", "Sample phone number is not allowed.")
            await self.show_async_message("Wrong", "Sample phone number is not allowed.", icon=QMessageBox.Icon.Critical)
            return

        dlg = self.do_long_task()
        r = await telegram_panel.add_account(phone)
        dlg.close()

        if not r["status"]:
            # QMessageBox.critical(self, "Error", r["message"])
            await self.show_async_message("Error", str(r["message"]), icon=QMessageBox.Icon.Critical)
            return

        # ورود کد
        for _ in range(3):
            # text, ok = QInputDialog.getText(self, "Account login code", "Enter the 5-digit code:")
            text, ok = await self.ask_code_dialog( "Account login code", "Enter the 5-digit code:")
            for _ in range(10):
                if not ok:
                    break
                if text.isdigit() and len(text) == 5:
                    break
                else:
                    # text, ok = QInputDialog.getText(self, "Account login code", "Enter the 5-digit code:")
                    text, ok = await self.ask_code_dialog( "Account login code", "Enter the 5-digit code:")

            if not ok:
                await telegram_panel.cancel_acc(r["cli"], r["phone"])
                # QMessageBox.critical(self, "Error", "Canceled by user.")
                await self.show_async_message("Error", "Canceled by user.", icon=QMessageBox.Icon.Critical)
                return

            dlg = self.do_long_task()
            rs = await telegram_panel.get_code(r["cli"], r["phone"], r["code_hash"], text)
            dlg.close()

            if rs["status"]:
                # QMessageBox.information(self, "Success", rs["message"])
                await self.show_async_message("Success", rs["message"], icon=QMessageBox.Icon.Information)
                telegram_panel.make_json_data(r["phone"], r["api_id"], r["api_hash"], r["proxy"], "")
                return

            if rs["message"] == "invalid_code":
                # QMessageBox.critical(self, "Error", "Invalid code.")
                await self.show_async_message("Error", "Invalid code.", icon=QMessageBox.Icon.Critical)
                continue

            if rs["message"] == "FA2":
                for _ in range(3):
                    # text, ok = QInputDialog.getText(self, "Account password", "Enter the password:")
                    text, ok = await self.ask_code_dialog("Account password", "Enter the password:")
                    if not ok:
                        await telegram_panel.cancel_acc(r["cli"], r["phone"])
                        # QMessageBox.critical(self, "Error", "Canceled by user.")
                        await self.show_async_message("Error", "Canceled by user.", icon=QMessageBox.Icon.Critical)
                        return

                    dlg = self.do_long_task()
                    rsp = await telegram_panel.get_password(r["cli"], r["phone"], text)
                    dlg.close()

                    if rsp["status"]:
                        # QMessageBox.information(self, "Success", rsp["message"])
                        await self.show_async_message("Success", rsp["message"], icon=QMessageBox.Icon.Information)
                        telegram_panel.make_json_data(r["phone"], r["api_id"], r["api_hash"], r["proxy"], text)
                        return

                    if rsp["message"] == "invalid_password":
                        # QMessageBox.critical(self, "Error", "Invalid password.")
                        await self.show_async_message("Error", "Invalid password.", icon=QMessageBox.Icon.Critical)
                        continue
                    else:
                        # QMessageBox.critical(self, "Error", rsp["message"])
                        await self.show_async_message("Error", rsp["message"], icon=QMessageBox.Icon.Critical)
                        return

            if rs["message"]:
                # QMessageBox.critical(self, "Error", rs["message"])
                await self.show_async_message("Error", rs["message"], icon=QMessageBox.Icon.Critical)
                return

        try:await telegram_panel.cancel_acc(r["cli"], r["phone"])
        except:pass
        # QMessageBox.critical(self, "Error", "Canceled by user.")
        await self.show_async_message("Error", "Canceled by user.", icon=QMessageBox.Icon.Critical)
        return

    def remove_account(self):
        phone = self.ui.remove_account_input.text().strip()
        if phone in telegram_panel.list_accounts():
            telegram_panel.remove_account(phone)
            QMessageBox.information(self, "Success", "Account removed.")
        else:
            QMessageBox.critical(self, "Error", "Account not found.")
        return
    

    def acclistupdate(self,log=True):
        r = telegram_panel.list_accounts()
        self.ui.list_account_ac.clear()
        self.ui.list_account_ac.addItems(r)
        self.ui.lcdNumber.display(len(r))
        if not log:
            QMessageBox.information(self, "Success", "Account list updated.")
        return
    
    
    def update_list_channel_remove(self):
        self.ui.list_channel_rem.clear()
        self.ui.list_channel_rem.addItems(telegram_panel.list_channel())
        return
    
    
    @asyncSlot()
    async def disable_extract_channel(self):
        global Extract
        if Extract:
            Extract = False
            self.ui.status_extract.setText("Status: Inactive")
            # QMessageBox.information(self, "Success", "Extraction stopped.")
            await self.show_async_message("Success", "Extraction stopped.", icon=QMessageBox.Icon.Information)
        else:
            # QMessageBox.critical(self, "Error", "Extraction is not active.")
            await self.show_async_message("Error", "Extraction is not active.", icon=QMessageBox.Icon.Critical)
        return
        
    
    @asyncSlot()
    async def extract_channel(self):
        global Extract
        
        self.ui.log_extract.clear()
        self.ui.log_extract.setReadOnly(True)
        
        if len(telegram_panel.list_accounts()) == 0:
            # QMessageBox.critical(self, "Error", "No accounts found.")
            await self.show_async_message("Error", "No accounts found.", icon=QMessageBox.Icon.Critical)
            return
        if Extract:
            # QMessageBox.critical(self, "Error", "Already extracting.")
            await self.show_async_message("Error", "Already extracting.", icon=QMessageBox.Icon.Critical)
            return
        
        phone = self.ui.accselect.currentText()
        
        link = self.ui.channel_extracct_input.text().strip()
        if telegram_panel.is_valid_telegram_link(link) or link.startswith("-100") and link.replace("-100","").isdigit():
            Extract = True
            self.ui.status_extract.setText("Status: Active")
            asyncio.create_task(self.extract_proc(phone,link))
        else:
            # QMessageBox.critical(self, "Error", "Invalid Telegram link.")
            await self.show_async_message("Error", "Invalid Telegram link.", icon=QMessageBox.Icon.Critical)
        return
    
    
    async def extract_proc(self,phone , link):
        global Extract
        
        
        self.ui.log_extract.appendPlainText("Extracting {}...".format(phone))
        data = telegram_panel.get_json_data(phone)
        proxy = await telegram_panel.get_proxy(data["proxy"])
        cli = Client('account/{}'.format(phone), data["api_id"], data["api_hash"], proxy=proxy[0])
        await asyncio.wait_for(cli.connect() , 15)
        self.ui.log_extract.appendPlainText("Connected to {}.".format(phone))
        if link.startswith("-100") :
            chtd = int(link)
            join = await telegram_panel.get_chat(cli,chtd)
        else:
            join = await telegram_panel.Join(cli,link)
        if len(join) != 3:
            Extract = False
            try:await cli.disconnect()
            except:pass
            # QMessageBox.critical(self, "Error", "Failed to join the channel.")
            self.ui.log_extract.appendPlainText("Failed to join the channel.\n{}".format(join[0]))
            await self.show_async_message("Error", "Failed to join the channel.", icon=QMessageBox.Icon.Critical)
            return
        chat= await cli.get_chat(join[0])
        # count = chat.members_count
        async for messagae in cli.get_chat_history(chat_id=chat.id,limit=1):
            ofss = messagae.id
            countmsg = messagae.id
        ana_count = 0
        massagesx = []
        self.ui.log_extract.appendPlainText("Number of chat messages: {}".format(countmsg))
        for _ in range(10):
            if Extract == False:break
            try:
                async for messagae in cli.get_chat_history(chat_id=chat.id,max_id=ofss,limit=countmsg):
                    if Extract == False:break
                    ofss = messagae.id
                    ana_count += 1
                    massagesx.append(json.loads(str(messagae)))
                    self.ui.lcdNumber_member_extract.display(len(massagesx))
                    self.ui.lcdNumber_member_extract.display(len(massagesx))
                    self.ui.log_extract.appendPlainText("[{}] {}".format(len(massagesx),messagae.id))
                    await asyncio.sleep(0.05)
            except errors.FloodWait as e:
                self.ui.log_extract.appendPlainText("FloodWait: {}".format(e.value))
                await asyncio.sleep(e.value + random.randint(10, 35))    
            except Exception as e:
                self.ui.log_extract.appendPlainText("Error: {}".format(e))
                break
                
        Extract = False
        self.ui.status_extract.setText("Status: Disactive")
        await cli.disconnect()
        self.ui.log_extract.appendPlainText("Disconnected from {}.".format(phone))
        if len(massagesx) != 0:
            name = '{} - msg - {} - {} .json'.format(link.split('/')[-1] if not link.startswith("@") else link[1:],len(massagesx),int(time.time()))
            with open("masssages/"+self.safe_filename(name),'w',encoding='utf-8') as f:
                json.dump(massagesx,f,ensure_ascii=False,indent=2)
        self.ui.log_extract.appendPlainText("Extracted {} Massages.".format(len(massagesx)))
        await self.show_async_message("Success", "Extracted {} Massages.".format(len(massagesx)), icon=QMessageBox.Icon.Information)
        try:self.update_list_channel_remove()
        except:pass
        del massagesx
        return
    
    def safe_filename(slef, name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        name = name.strip().replace(' ', '_')
        return name or 'file'

    
    def remove_extract_channel(self):
        try:
            os.remove('masssages/{}.json'.format(self.ui.list_channel_rem.currentText()))
            self.update_list_channel_remove()
            QMessageBox.information(self, "Success", "Extracted channel removed.")
        except:
            QMessageBox.critical(self, "Error", "Extracted channel not found.")
        return
    
    
                
                
if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()
