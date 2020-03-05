#!/usr/bin/env python3

# CustomInstallHelper
# Version 1.0
# BY R-YaTian

from tkinter import (Tk, Frame, LabelFrame, PhotoImage, Button, Entry, Checkbutton, Radiobutton,
    Label, Toplevel, Scrollbar, Text, StringVar, IntVar, RIGHT, W, X, Y, DISABLED, NORMAL, SUNKEN,
    END)
from tkinter.messagebox import askokcancel, showerror, showinfo, WARNING
from tkinter.filedialog import askopenfilename, askdirectory
from ctypes import windll
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError
from sys import exit
from threading import Thread
from queue import Queue, Empty
from subprocess import Popen
from distutils.dir_util import _path_created
from shutil import move, rmtree, copyfile
import os

####################################################################################################
class ThreadSafeText(Text):
    def __init__(self, master, **options):
        Text.__init__(self, master, **options)
        self.queue = Queue()
        self.update_me()

    def write(self, line):
        self.queue.put(line)

    def update_me(self):
        try:
            while 1:
                self.insert(END, str(self.queue.get_nowait()) + '\n')
                self.see(END)
                self.update_idletasks()

        except Empty:
            pass

        self.after(500, self.update_me)

####################################################################################################
class Application(Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.update_mode = False
        self.pack() 

        # First row
        f1 = LabelFrame(self, text='选择从你机器导出的movable.sed文件', padx=10, pady=10)

        self.sedfile = StringVar()
        self.sedfile1 = ""
        Entry(f1, textvariable=self.sedfile, state='readonly', width=40).pack(side='left')

        Button(f1, text='浏览', command=self.choose_sed).pack(side='left')

        f1.pack(padx=10, pady=10, fill=X)

        # Second row
        f2 = LabelFrame(self, text='选择要安装的CIA文件存放路径', padx=10, pady=20)

        self.ciapath = StringVar()
        self.ciapath1 = ""
        Entry(f2, textvariable=self.ciapath, state='readonly', width=40).pack(side='left')

        Button(f2, text='浏览', command=self.choose_cia).pack(side='left')

        f2.pack(padx=10, pady=20, fill=X)

        # Third row
        f3 = Frame(self)

        self.start_button = Button(f3, text='开始安装', width=13, command=self.setup, state=DISABLED)
        self.start_button.pack(side='left', padx=(0, 5))

        Button(f3, text='更新库文件', command=self.update, width=13).pack(side='left', padx=(0, 0))
        Button(f3, text='退出', command=root.destroy, width=13).pack(side='left', padx=(5, 0))

        f3.pack(pady=(10, 30))

    ################################################################################################
    def choose_sed(self):
        name = askopenfilename(filetypes=( ( 'movable.sed', '*.sed' ), ))
        self.sedfile.set(name)
        if name != '':
            self.sedfile1 = name
        else:
            self.sedfile1 = ''
            self.ciapath.set('')
            self.ciapath1 = ''
        self.start_button['state'] = (DISABLED if self.ciapath1 == '' else NORMAL)
        self.start_button['state'] = (NORMAL if self.sedfile1 != '' else DISABLED)
        self.start_button['state'] = (DISABLED if self.ciapath1 == '' else NORMAL)
    def choose_cia(self):
        name1 = askdirectory()
        self.ciapath.set(name1)
        if name1 != '':
            self.ciapath1 = name1
        else:
            self.ciapath1 = ''
            self.sedfile.set('')
            self.sedfile1 = ''
        self.start_button['state'] = (DISABLED if self.sedfile1 == '' else NORMAL)
        self.start_button['state'] = (NORMAL if self.ciapath1 != '' else DISABLED)
        self.start_button['state'] = (DISABLED if self.sedfile1 == '' else NORMAL)

    ################################################################################################
    def update(self):
        self.update_mode = True
        self.setup()
    def setup(self):
        if self.update_mode == False:
            showinfo('提示', '接下来请选择3DS存储卡根目录')
            self.sd_path = askdirectory()
            if self.sd_path == '':
                return
        dialog = Toplevel(self)
        # Open as dialog (parent disabled)
        dialog.grab_set()
        dialog.title('状态')
        # Disable maximizing
        dialog.resizable(0, 0)

        frame = Frame(dialog, bd=2, relief=SUNKEN)

        scrollbar = Scrollbar(frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.log = ThreadSafeText(frame, bd=0, width=52, height=20,
            yscrollcommand=scrollbar.set)
        self.log.pack()

        scrollbar.config(command=self.log.yview)

        frame.pack()

        Button(dialog, text='关闭', command=dialog.destroy, width=16).pack(pady=10)

        # Center in window
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        dialog.geometry('%dx%d+%d+%d' % (width, height, root.winfo_x() + (root.winfo_width() / 2) -
            (width / 2), root.winfo_y() + (root.winfo_height() / 2) - (height / 2)))
        if self.update_mode == False:
            Thread(target=self.check_bin).start()
        else:
            self.update_mode = False
            Thread(target=self.update_db).start()

    ################################################################################################
    def check_sed(self):
        self.log.write('检查movable.sed文件中...')
        try:
            with open(self.sedfile.get(), 'rb') as f:
                f.seek(0)
                seed = f.read(0x04)
                if seed == b'SEED':
                    self.log.write('movable.sed文件检查完毕')
                    Thread(target=self.check_cia).start()
                else:
                    self.log.write('错误: 请选择正确的movable.sed文件')
        except IOError as e:
            print(e)
            self.log.write('错误: 无法读取文件 ' +
                os.path.basename(self.sedfile.get()))
    def check_cia(self):
        self.log.write('检查CIA文件夹中...')
        filearray = []
        address = self.ciapath1
        f_list = os.listdir(address)
        for fileNAME in f_list:
            if os.path.splitext(fileNAME)[1] == '.cia':
                filearray.append(fileNAME )
        ge = len(filearray)
        if ge != 0:
            self.log.write("检测到%d个CIA文件" % len(filearray))
            self.log.write("所有检查均已通过,即将开始安装")
            Thread(target=self.install_db).start()
        else:
            self.log.write('错误: 选择的目录下没有CIA文件')
    def check_bin(self):
        if os.path.exists('boot9.bin'):
            self.log.write("检测到boot9.bin文件")
            Thread(target=self.check_dir).start()
        else:
            self.log.write('错误: 程序所在目录没有boot9.bin文件')
    def check_db(self):
        filename = 'seeddb.bin'
        if os.path.exists(filename):
            self.log.write("检测到库文件")
            Thread(target=self.check_sed).start()
        else:
            self.log.write('错误: 没有找到库文件,尝试下载...')
            try:
                self.log.write('正在下载最新的seeddb.bin库文件...')
                urlretrieve('https://github.com/ihaveamac/3DS-rom-tools/raw/master/seeddb/' + filename, filename)
                self.log.write('库文件下载成功')
                Thread(target=self.check_sed).start()
            except (URLError, IOError) as e:
                print(e)
                self.log.write('错误: 无法下载库文件\n你可以返回主菜单并点击“更新库文件”以重试')
    def check_dir(self):
        sd_dir = self.sd_path
        self.log.write("检查3DS存储卡路径中...")
        if os.path.exists(sd_dir + "\\" + "Nintendo 3DS"):
            self.log.write("3DS存储卡路径检查完毕...")
            Thread(target=self.check_db).start()
        else:
            self.log.write('错误: 请选择正确的3DS存储卡根目录')

    ################################################################################################
    def update_db(self):
        filename = 'seeddb.bin'
        try:
            self.log.write('正在下载最新的seeddb.bin库文件')
            urlretrieve('https://github.com/ihaveamac/3DS-rom-tools/raw/master/seeddb/' + filename, filename)
            self.log.write('更新完毕,请点击“关闭”返回主菜单')
        except (URLError, IOError) as e:
            print(e)
            self.log.write('错误: 无法下载库文件')
    def install_db(self):
        filename = 'seeddb.bin'
        temp = os.path.expanduser('~')
        try:
            self.log.write('安装库文件中...')
            if os.path.exists(temp + "\\" + "3ds"):
                rmtree(temp + "\\" + "3ds")
            os.makedirs(temp + "\\" + "3ds")
            copyfile(filename, temp + "\\" + "3ds" + "\\" + "seeddb.bin")
            self.log.write('库文件安装成功')
            Thread(target=self.install).start()
        except IOError as e:
            print(e)
            self.log.write('错误: 无法安装库文件')
    def install(self):
        self.log.write('正在安装CIA...')
        exe = 'custom-install'
        temp = os.path.expanduser('~')
        try:
            proc = Popen([ exe,'-b', 'boot9.bin', '-m',
                self.sedfile.get(), '--sd', self.sd_path, '-c', self.ciapath1 ])
            ret_val = proc.wait()
            if ret_val == 0:
                if os.path.exists(temp + "\\" + "3ds"):
                    self.log.write('卸载库文件中...')
                    rmtree(temp + "\\" + "3ds")
                    self.log.write('库文件卸载成功')
                self.log.write('完成!\n请弹出你的3DS存储卡,并装回到你的3DS上\n注意: 你还需要在3DS上完成最后的安装步骤')
            else:
                self.log.write('错误: 安装过程中发生了错误')
                if os.path.exists(temp + "\\" + "3ds"):
                    self.log.write('卸载库文件中...')
                    rmtree(temp + "\\" + "3ds")
                    self.log.write('库文件卸载成功')
        except OSError as e:
            print(e)
            self.log.write('错误: 无法运行 ' + exe)
            if os.path.exists(temp + "\\" + "3ds"):
                self.log.write('卸载库文件中...')
                rmtree(temp + "\\" + "3ds")
                self.log.write('库文件卸载成功')

####################################################################################################
root = Tk()

if windll.shell32.IsUserAnAdmin() == 0:
    root.withdraw()
    showerror('错误', '请以管理员权限运行本程序')
    root.destroy()
    exit(1)

root.title('CustomInstallHelperV1.0')
# Disable maximizing
root.resizable(0, 0)
# Center in window
root.eval('tk::PlaceWindow %s center' % root.winfo_toplevel())
app = Application(master=root)
app.mainloop()
