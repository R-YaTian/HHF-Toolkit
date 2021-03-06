#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HiyaCFW Helper R
# Version 3.6.1R
# Author: R-YaTian
# Original Author: mondul <mondul@huyzona.com>

from tkinter import (Tk, Frame, LabelFrame, PhotoImage, Button, Entry, Checkbutton, Radiobutton,
    Label, Toplevel, Scrollbar, Text, StringVar, IntVar, RIGHT, W, X, Y, DISABLED, NORMAL, SUNKEN,
    END)
from tkinter.messagebox import askokcancel, showerror, showinfo, WARNING
from tkinter.filedialog import askopenfilename, askdirectory
from platform import system, architecture
from os import path, remove, chmod, listdir, rename, environ
from sys import exit
from threading import Thread
from queue import Queue, Empty
from hashlib import sha1
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError
from subprocess import Popen, PIPE
from struct import unpack_from
from shutil import rmtree, copyfile, copyfileobj
from distutils.dir_util import copy_tree, _path_created
from re import search
from appgen import agen
from locale import getlocale, getdefaultlocale, setlocale, LC_ALL
from inspect import isclass
import gettext
import ctypes
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

#Thread-Control
def _async_raise(tid, exctype):
    tid = ctypes.c_long(tid)
    if not isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("Invalid Thread ID")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc Failed")
def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


####################################################################################################
# Thread-safe text class

class ThreadSafeText(Text):
    def __init__(self, master, **options):
        Text.__init__(self, master, **options)
        self.queue = Queue()
        self.update_me()

    def write(self, line):
        self.wlog = open('Window.log', 'a')
        self.queue.put(line)
        self.wlog.write(line+'\n')
        self.wlog.close()

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
# Main application class

class Application(Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.pack()
        self.adv_mode = False
        self.nand_mode = False
        self.setup_select = False
        self.have_hiya = False
        self.is_tds = False
        self.have_menu = False
        self.finish = False

        # First row
        f1 = Frame(self) 

        self.bak_frame=LabelFrame(f1, text=_('含有No$GBA footer的NAND备份文件'), padx=10, pady=10)

        nand_icon = PhotoImage(data=('R0lGODlhEAAQAIMAAAAAADMzM2ZmZpmZmczMzP///wAAAAAAAAA'
            'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAMAAAYALAAAAAAQAB'
            'AAAARG0MhJaxU4Y2sECAEgikE1CAFRhGMwSMJwBsU6frIgnR/bv'
            'hTPrWUSDnGw3JGU2xmHrsvyU5xGO8ql6+S0AifPW8kCKpcpEQA7'))

        self.nand_button = Button(self.bak_frame, image=nand_icon, command=self.change_mode, state=DISABLED)
        self.nand_button.image = nand_icon

        self.nand_button.pack(side='left')

        self.nand_file = StringVar()
        self.nandfile = Entry(self.bak_frame, textvariable=self.nand_file, state='readonly', width=40)
        self.nandfile.pack(side='left')

        self.chb = Button(self.bak_frame, text='...', command=self.choose_nand)
        self.chb.pack(side='left')

        self.bak_frame.pack(fill=X)

        self.adv_frame=LabelFrame(f1, text=_('存储卡根目录'), padx=10, pady=10)

        self.sdp = StringVar()
        self.sdpath = Entry(self.adv_frame, textvariable=self.sdp, state='readonly', width=42)
        self.sdpath.pack(padx=4, side='left')

        self.chb1 = Button(self.adv_frame, text='...', command=self.choose_sdp)
        self.chb1.pack(side='left')

        f1.pack(padx=10, pady=10, fill=X)

        # Second row
        f2 = Frame(self)

        self.setup_frame = LabelFrame(f2, text=_('NAND解压选项'), padx=10, pady=10)

        self.setup_operation = IntVar()

        if fatcat is None:
            if _7z is not None:
                self.setup_operation.set(1)
            elif osfmount is not None:
                self.setup_operation.set(2)
        else:
            self.setup_operation.set(0)

        self.rb1 = Radiobutton(self.setup_frame, text=_('Fatcat(默认)'), variable=self.setup_operation, value=0)
        self.rb2 = Radiobutton(self.setup_frame, text='7-Zip', variable=self.setup_operation, value=1)
        self.rb3 = Radiobutton(self.setup_frame, text=_('OSFMount2(需要管理员权限)'), variable=self.setup_operation, value=2)

        if osfmount or _7z is not None:
            if fatcat is not None:
                self.rb1.pack(anchor=W)
            if _7z is not None:
                self.rb2.pack(anchor=W)
            if osfmount is not None:
                self.rb3.pack(anchor=W)
            if (fatcat is not None) or (osfmount and _7z is not None):
                self.setup_frame.pack(padx=10, pady=(0, 10), fill=X)
                self.setup_select = True

        # Check boxes
        self.checks_frame = Frame(f2)

        # Install TWiLight check
        self.twilight = IntVar()
        self.twilight.set(1)

        twl_chk = Checkbutton(self.checks_frame,
            text=_('同时安装TWiLightMenu++'), variable=self.twilight)

        twl_chk.pack(padx=10, anchor=W)

        self.appgen = IntVar()
        self.appgen.set(0)

        ag_chk = Checkbutton(self.checks_frame, text=_('使用AppGen'), variable=self.appgen)

        ag_chk.pack(padx=10, anchor=W)

        self.devkp = IntVar()
        self.devkp.set(0)

        dkp_chk = Checkbutton(self.checks_frame, text=_('启用系统设置-数据管理功能'), variable=self.devkp, command=self.usedevkp)

        dkp_chk.pack(padx=10, anchor=W)

        self.altdl = IntVar()
        self.altdl.set(0)

        adl_chk = Checkbutton(self.checks_frame, text='使用备用载点', variable=self.altdl, command=self.usealtdl)
        if loc == 'zh_CN':
            adl_chk.pack(padx=10, anchor=W)

        self.checks_frame.pack(fill=X)

        self.checks_frame1 = Frame(f2)

        self.ag1_chk = Checkbutton(self.checks_frame1, text=_('使用AppGen'), variable=self.appgen, state=DISABLED)

        self.ag1_chk.pack(padx=10, anchor=W)

        self.updatehiya = IntVar()
        self.updatehiya.set(0)

        self.uh_chk = Checkbutton(self.checks_frame1, text=_('更新HiyaCFW'), variable=self.updatehiya, state=DISABLED)

        self.uh_chk.pack(padx=10, anchor=W)

        self.dkp1_chk = Checkbutton(self.checks_frame1, text=_('启用系统设置-数据管理功能'), variable=self.devkp, command=self.usedevkp, state=DISABLED)

        self.dkp1_chk.pack(padx=10, anchor=W)

        adl1_chk = Checkbutton(self.checks_frame1, text='使用备用载点', variable=self.altdl, command=self.usealtdl)
        if loc == 'zh_CN':
            adl1_chk.pack(padx=10, anchor=W)

        # NAND operation frame
        self.nand_frame = LabelFrame(f2, text=_('NAND操作选项'), padx=10, pady=10)

        self.nand_operation = IntVar()
        self.nand_operation.set(0)

        rb0 = Radiobutton(self.nand_frame, text=_('安装或卸载最新版本的unlaunch(需要管理员权限)'),
            variable=self.nand_operation, value=2,
            command=lambda: self.enable_entries(False))
        if osfmount is not None:
            rb0.pack(anchor=W)
        Radiobutton(self.nand_frame, text=_('移除 No$GBA footer'), variable=self.nand_operation,
            value=0, command=lambda: self.enable_entries(False)).pack(anchor=W)

        Radiobutton(self.nand_frame, text=_('添加 No$GBA footer'), variable=self.nand_operation,
            value=1, command=lambda: self.enable_entries(True)).pack(anchor=W)

        fl = Frame(self.nand_frame)

        self.cid_label = Label(fl, text='eMMC CID', state=DISABLED)
        self.cid_label.pack(anchor=W, padx=(24, 0))

        self.cid = StringVar()
        self.cid_entry = Entry(fl, textvariable=self.cid, width=20, state=DISABLED)
        self.cid_entry.pack(anchor=W, padx=(24, 0))

        fl.pack(side='left')

        fr = Frame(self.nand_frame)

        self.console_id_label = Label(fr, text='Console ID', state=DISABLED)
        self.console_id_label.pack(anchor=W)

        self.console_id = StringVar()
        self.console_id_entry = Entry(fr, textvariable=self.console_id, width=20, state=DISABLED)
        self.console_id_entry.pack(anchor=W)

        fr.pack(side='right')

        f2.pack(fill=X)

        # Third row
        f3 = Frame(self)

        self.start_button = Button(f3, text=_('开始'), width=13, command=self.hiya, state=DISABLED)
        self.start_button.pack(side='left', padx=(0, 5))

        self.adv_button = Button(f3, text=_('高级'), command=self.change_mode1, width=13)
        self.back_button = Button(f3, text=_('返回'), command=self.change_mode, width=13)
        self.back1_button = Button(f3, text=_('返回'), command=self.change_mode1, width=13)
        self.adv_button.pack(side='left', padx=(0, 0))

        self.exit_button = Button(f3, text=_('退出'), command=root.destroy, width=13)
        self.exit_button.pack(side='left', padx=(5, 0))

        f3.pack(pady=(10, 20))

        self.folders = []
        self.files = []


    ################################################################################################
    def usealtdl(self):
        if self.altdl.get() == 1:
            if not askokcancel('警告', ('使用备用载点可能可以提高下载必要文件的速度，但备用载点服务器马上就要跑路，此功能或许只能使用到3月中旬'), icon=WARNING):
                self.altdl.set(0)
    def usedevkp(self):
        if self.devkp.get() == 1:
            if not askokcancel(_('提示'), (_('勾选此选项将会在CFW中开启系统设置中的数据管理功能，如果你已经在NAND中开启了此功能，则不需要勾选此选项'))):
                self.devkp.set(0)
    def change_mode(self):
        if (self.nand_mode):
            self.nand_operation.set(0)
            self.enable_entries(False)
            self.nand_frame.pack_forget()
            self.start_button.pack_forget()
            self.back_button.pack_forget()
            self.exit_button.pack_forget()
            if osfmount or _7z is not None:
                if fatcat is not None:
                    self.rb1.pack(anchor=W)
                if _7z is not None:
                    self.rb2.pack(anchor=W)
                if osfmount is not None:
                    self.rb3.pack(anchor=W)
                if (fatcat is not None) or (osfmount and _7z is not None):
                    self.setup_frame.pack(padx=10, pady=(0, 10), fill=X)
            self.checks_frame.pack(anchor=W)
            self.start_button.pack(side='left', padx=(0, 5))
            self.adv_button.pack(side='left', padx=(0, 0))
            self.exit_button.pack(side='left', padx=(5, 0))
            self.nand_mode = False
        else:
            if askokcancel(_('警告'), (_('你正要进入NAND操作模式, 请确认你知道自己在做什么, 继续吗?')), icon=WARNING):
                self.have_hiya = False
                self.is_tds = False
                self.have_menu = False
                if (self.setup_select):
                    self.setup_frame.pack_forget()
                self.setup_operation.set(0)
                self.checks_frame.pack_forget()
                self.start_button.pack_forget()
                self.adv_button.pack_forget()
                self.exit_button.pack_forget()
                self.nand_frame.pack(padx=10, pady=(0, 10), fill=X)
                self.start_button.pack(side='left', padx=(0, 5))
                self.back_button.pack(side='left', padx=(0, 0))
                self.exit_button.pack(side='left', padx=(5, 0))
                self.nand_mode = True
    def change_mode1(self):
        if (self.adv_mode):
            self.have_menu = False
            self.is_tds = False
            self.have_hiya = False
            if self.appgen.get() == 1:
                self.appgen.set(0)
            if self.devkp.get() == 1:
                self.devkp.set(0)
            if self.updatehiya.get() == 1:
                self.updatehiya.set(0)
            if self.sdp.get() != '':
                self.sdp.set('')
            self.adv_frame.pack_forget()
            self.checks_frame1.pack_forget()
            self.start_button.pack_forget()
            self.back1_button.pack_forget()
            self.exit_button.pack_forget()
            self.bak_frame.pack(fill=X)
            if osfmount or _7z is not None:
                if fatcat is not None:
                    self.rb1.pack(anchor=W)
                if _7z is not None:
                    self.rb2.pack(anchor=W)
                if osfmount is not None:
                    self.rb3.pack(anchor=W)
                if (fatcat is not None) or (osfmount and _7z is not None):
                    self.setup_frame.pack(padx=10, pady=(0, 10), fill=X)
            self.checks_frame.pack(anchor=W)
            self.start_button['state'] = DISABLED
            self.nand_button['state'] = DISABLED
            self.start_button.pack(side='left', padx=(0, 5))
            self.adv_button.pack(side='left', padx=(0, 0))
            self.exit_button.pack(side='left', padx=(5, 0))
            self.adv_mode = False
        else:
            if askokcancel(_('提示'), (_('高级模式提供了单独安装TWiLightMenu++等功能, 点击"确定"以进入'))):
                self.have_menu = False
                self.is_tds = False
                self.have_hiya = False
                if self.appgen.get() == 1:
                    self.appgen.set(0)
                if self.devkp.get() == 1:
                    self.devkp.set(0)
                if self.updatehiya.get() == 1:
                    self.updatehiya.set(0)
                if self.nand_file.get() != '':
                    self.nand_file.set('')
                self.bak_frame.pack_forget()
                if (self.setup_select):
                    self.setup_frame.pack_forget()
                self.checks_frame.pack_forget()
                self.start_button.pack_forget()
                self.adv_button.pack_forget()
                self.exit_button.pack_forget()
                self.adv_frame.pack(fill=X)
                self.checks_frame1.pack(anchor=W)
                self.uh_chk['state'] = DISABLED
                self.dkp1_chk['state'] = DISABLED
                self.ag1_chk['state'] = DISABLED
                self.start_button['state'] = DISABLED
                self.start_button.pack(side='left', padx=(0, 5))
                self.back1_button.pack(side='left', padx=(0, 0))
                self.exit_button.pack(side='left', padx=(5, 0))
                self.adv_mode = True


    ################################################################################################
    def enable_entries(self, status):
        self.cid_label['state'] = (NORMAL if status else DISABLED)
        self.cid_entry['state'] = (NORMAL if status else DISABLED)
        self.console_id_label['state'] = (NORMAL if status else DISABLED)
        self.console_id_entry['state'] = (NORMAL if status else DISABLED)
    def check_console(self, spath):
        tmenu = path.join(spath, '_nds', 'TWiLightMenu', 'main.srldr')
        if path.exists(tmenu):
            self.have_menu = True
        tds = path.join(spath, 'Nintendo 3DS')
        if path.exists(tds):
            self.is_tds = True
        else:
            hiyad = path.join(spath, 'hiya.dsi')
            hiyab = path.join(spath, 'hiya', 'bootloader.nds')
            hiyas = path.join(spath, 'sys', 'HWINFO_S.dat')
            if path.exists(hiyad) or path.exists(hiyab) or path.exists(hiyas):
                self.have_hiya = True


    ################################################################################################
    def choose_sdp(self):
        self.have_hiya = False
        self.is_tds = False
        self.have_menu = False
        showinfo(_('提示'), _('请选择机器的存储卡根目录'))
        self.sd_path1 = askdirectory()
        self.sdp.set(self.sd_path1)
        if self.appgen.get() == 1:
            self.appgen.set(0)
        if self.devkp.get() == 1:
            self.devkp.set(0)
        if self.updatehiya.get() == 1:
            self.updatehiya.set(0)
        self.start_button['state'] = (NORMAL if self.sd_path1 != '' else DISABLED)
        if self.sd_path1 == '':
            self.uh_chk['state'] = DISABLED
            self.dkp1_chk['state'] = DISABLED
            self.ag1_chk['state'] = DISABLED
            return
        self.check_console(self.sd_path1)
        if self.is_tds == True:
            self.uh_chk['state'] = DISABLED
            self.dkp1_chk['state'] = DISABLED
            self.ag1_chk['state'] = DISABLED
        elif self.have_hiya == True:
            self.uh_chk['state'] = NORMAL
            self.dkp1_chk['state'] = NORMAL
            self.ag1_chk['state'] = (DISABLED if self.have_menu == True else NORMAL)
        elif self.have_menu == True:
            self.uh_chk['state'] = DISABLED
            self.dkp1_chk['state'] = DISABLED
            self.ag1_chk['state'] = DISABLED
        else:
            self.uh_chk['state'] = DISABLED
            self.dkp1_chk['state'] = DISABLED
            self.ag1_chk['state'] = DISABLED
    def choose_nand(self):
        name = askopenfilename(filetypes=( ( 'nand.bin', '*.bin' ), ( 'DSi-1.mmc', '*.mmc' ) ))
        self.nand_file.set(name)
        self.nand_button['state'] = (NORMAL if name != '' else DISABLED)
        self.start_button['state'] = (NORMAL if name != '' else DISABLED)


    ################################################################################################
    def hiya(self):
        if not self.adv_mode:
            if self.setup_operation.get() == 2 or self.nand_operation.get() == 2:
                if ctypes.windll.shell32.IsUserAnAdmin() == 0:
                    root.withdraw()
                    showerror(_('错误'), _('此功能需要以管理员权限运行本工具'))
                    root.destroy()
                    exit(1)

        if not self.nand_mode:
            if not self.adv_mode:
                self.have_hiya = False
                self.is_tds = False
                self.have_menu = False
                showinfo(_('提示'), _('接下来请选择你用来安装自制系统的存储卡路径(或输出路径)\n为了避免 '
                    '启动错误 请确保目录下无任何文件'))
                self.sd_path = askdirectory()
                # Exit if no path was selected
                if self.sd_path == '':
                    return
                self.check_console(self.sd_path)
                if self.is_tds or self.have_hiya:
                    showerror(_('错误'), _('检测到CFW已安装，请转到高级模式，或选择一个空目录以继续'))
                    return

        # If adding a No$GBA footer, check if CID and ConsoleID values are OK
        elif self.nand_operation.get() == 1:
            cid = self.cid.get()
            console_id = self.console_id.get()

            # Check lengths
            if len(cid) != 32:
                showerror(_('错误'), 'Bad eMMC CID')
                return

            elif len(console_id) != 16:
                showerror(_('错误'), 'Bad Console ID')
                return

            # Parse strings to hex
            try:
                cid = bytearray.fromhex(cid)

            except ValueError:
                showerror(_('错误'), 'Bad eMMC CID')
                return

            try:
                console_id = bytearray(reversed(bytearray.fromhex(console_id)))

            except ValueError:
                showerror(_('错误'), 'Bad Console ID')
                return

        self.dialog = Toplevel()
        # Open as dialog (parent disabled)
        self.dialog.grab_set()
        self.dialog.title(_('状态'))
        # Disable maximizing
        self.dialog.resizable(0, 0)
        self.dialog.protocol("WM_DELETE_WINDOW", self.closethread)

        frame = Frame(self.dialog, bd=2, relief=SUNKEN)

        scrollbar = Scrollbar(frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.log = ThreadSafeText(frame, bd=0, width=52, height=20,
            yscrollcommand=scrollbar.set)
        self.log.pack()

        scrollbar.config(command=self.log.yview)

        frame.pack()

        Button(self.dialog, text=_('关闭'), command=self.closethread, width=16).pack(pady=10)

        # Center in window
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        self.dialog.geometry('%dx%d+%d+%d' % (width, height, root.winfo_x() + (root.winfo_width() / 2) -
            (width / 2), root.winfo_y() + (root.winfo_height() / 2) - (height / 2)))

        self.finish = False
        # Check if we'll be adding a No$GBA footer
        if self.nand_mode and self.nand_operation.get() == 1:
            self.TThread = Thread(target=self.add_footer, args=(cid, console_id))
            self.TThread.start()
        elif self.adv_mode:
            if self.updatehiya.get() == 1:
                self.TThread = Thread(target=self.get_latest_hiyacfw)
                self.TThread.start()
            else:
                self.TThread = Thread(target=self.get_latest_twilight)
                self.TThread.start()
        else:
            self.TThread = Thread(target=self.check_nand)
            self.TThread.start()


    ################################################################################################
    def closethread(self):
        if self.finish == True:
            self.dialog.destroy()
            self.finish = False
            return
        try:
            stop_thread(self.TThread)
            self.proc.kill()
        except:
            pass

        if self.setup_operation.get() == 2 or self.nand_operation.get() == 2:
            self.unmount_nand1()
        else:
            self.clean(True,)

        self.dialog.destroy()
        print(_('\n用户终止操作'))
    def check_nand(self):
        self.log.write(_('正在检查NAND文件...'))

        # Read the NAND file
        try:
            with open(self.nand_file.get(), 'rb') as f:
                # Go to the No$GBA footer offset
                f.seek(-64, 2)
                # Read the footer's header :-)
                bstr = f.read(0x10)

                if bstr == b'DSi eMMC CID/CPU':
                    # Read the CID
                    bstr = f.read(0x10)
                    self.cid.set(bstr.hex().upper())
                    self.log.write('- eMMC CID: ' + self.cid.get())

                    # Read the console ID
                    bstr = f.read(8)
                    self.console_id.set(bytearray(reversed(bstr)).hex().upper())
                    self.log.write('- Console ID: ' + self.console_id.get())

                    if self.nand_mode:
                        if self.nand_operation.get() == 2:
                            self.TThread = Thread(target=self.decrypt_nand)
                            self.TThread.start()
                        else:
                            self.TThread = Thread(target=self.remove_footer)
                            self.TThread.start()
                    else:
                        self.TThread = Thread(target=self.get_latest_hiyacfw)
                        self.TThread.start()

                else:
                    self.log.write(_('错误: 没有检测到No$GBA footer'))

        except IOError as e:
            print(e)
            self.log.write(_('错误: 无法打开文件 ') +
                path.basename(self.nand_file.get()))


    ################################################################################################
    def get_latest_hiyacfw(self):
        filename = 'HiyaCFW.7z'
        #filename = 'hiyaCFW.7z'
        self.files.append(filename)
        self.folders.append('for PC')
        self.folders.append('for SDNAND SD card')

        try:
            if not path.isfile(filename):
                self.log.write(_('\n正在下载最新版本的HiyaCFW...'))
                if self.altdl.get() == 1:
                    with urlopen('https://spblog.tk/somefiles/' + filename) as src, open(filename, 'wb') as dst:
                        copyfileobj(src, dst)
                else:
                    with urlopen('https://github.com/RocketRobz/hiyaCFW/releases/latest/download/' +
                        filename) as src, open(filename, 'wb') as dst:
                        copyfileobj(src, dst)

            self.log.write(_('- 正在解压 HiyaCFW 压缩包...'))

            if self.adv_mode and self.updatehiya.get() == 1:
                self.proc = Popen([ _7za, 'x', '-bso0', '-y', filename, 'for SDNAND SD card' ])
            else:
                self.proc = Popen([ _7za, 'x', '-bso0', '-y', filename, 'for PC', 'for SDNAND SD card' ])

            ret_val = self.proc.wait()

            if ret_val == 0:
                if self.adv_mode and self.updatehiya.get() == 1:
                    self.TThread = Thread(target=self.update_hiyacfw)
                    self.TThread.start()
                else:
                    self.TThread = Thread(target=self.decrypt_nand if path.isfile('bootloader.nds')
                        else self.extract_bios)
                    self.TThread.start()

            else:
                self.log.write(_('错误: 解压失败'))
                Thread(target=self.clean, args=(True,)).start()

        except (URLError, IOError) as e:
            print(e)
            self.log.write(_('错误: 无法下载HiyaCFW'))

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)


    ################################################################################################
    def extract_bios(self):
        self.files.append('arm7.bin')
        self.files.append('arm9.bin')
        self.log.write(_('\n正在从NAND中解压 ARM7/ARM9 BIOS...'))

        try:
            self.proc = Popen([ twltool, 'boot2', '--in', self.nand_file.get() ])

            ret_val = self.proc.wait()

            if ret_val == 0:
                # Hash arm7.bin
                sha1_hash = sha1()

                with open('arm7.bin', 'rb') as f:
                    sha1_hash.update(f.read())

                self.log.write('- arm7.bin SHA1:\n  ' +
                    sha1_hash.digest().hex().upper())

                # Hash arm9.bin
                sha1_hash = sha1()

                with open('arm9.bin', 'rb') as f:
                    sha1_hash.update(f.read())

                self.log.write('- arm9.bin SHA1:\n  ' +
                    sha1_hash.digest().hex().upper())


                self.TThread = Thread(target=self.patch_bios)
                self.TThread.start()

            else:
                self.log.write(_('错误: 解压失败'))
                Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def patch_bios(self):
        self.log.write('\nPatching ARM7/ARM9 BIOS...')

        try:
            self.patcher(path.join('for PC', 'bootloader files', 'bootloader arm7 patch.ips'),
                'arm7.bin')

            self.patcher(path.join('for PC', 'bootloader files', 'bootloader arm9 patch.ips'),
                'arm9.bin')

            # Hash arm7.bin
            sha1_hash = sha1()

            with open('arm7.bin', 'rb') as f:
                sha1_hash.update(f.read())

            self.log.write('- Patched arm7.bin SHA1:\n  ' +
                sha1_hash.digest().hex().upper())

            # Hash arm9.bin
            sha1_hash = sha1()

            with open('arm9.bin', 'rb') as f:
                sha1_hash.update(f.read())

            self.log.write('- Patched arm9.bin SHA1:\n  ' +
                sha1_hash.digest().hex().upper())

            self.TThread = Thread(target=self.arm9_prepend)
            self.TThread.start()

        except IOError as e:
            print(e)
            self.log.write(_('错误: 无法完成 patch BIOS'))
            Thread(target=self.clean, args=(True,)).start()

        except Exception as e:
            print(e)
            self.log.write(_('错误: 无效的 patch header'))
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def arm9_prepend(self):
        self.log.write(_('\n正在预载数据到 ARM9 BIOS...'))

        try:
            with open('arm9.bin', 'rb') as f:
                data = f.read()

            with open('arm9.bin', 'wb') as f:
                with open(path.join('for PC', 'bootloader files',
                    'bootloader arm9 append to start.bin'), 'rb') as pre:
                    f.write(pre.read())

                f.write(data)

            # Hash arm9.bin
            sha1_hash = sha1()

            with open('arm9.bin', 'rb') as f:
                sha1_hash.update(f.read())

            self.log.write('- Prepended arm9.bin SHA1:\n  ' +
                sha1_hash.digest().hex().upper())

            self.TThread = Thread(target=self.make_bootloader)
            self.TThread.start()

        except IOError as e:
            print(e)
            self.log.write(_('错误: 无法预载数据到 ARM9 BIOS'))
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def make_bootloader(self):
        self.log.write(_('\n正在生成 bootloader...'))

        exe = (path.join('for PC', 'bootloader files', 'ndstool.exe') if sysname == 'Windows' else
            path.join(sysname, 'ndsblc'))

        try:
            self.proc = Popen([ exe, '-c', 'bootloader.nds', '-9', 'arm9.bin', '-7', 'arm7.bin', '-t',
                path.join('for PC', 'bootloader files', 'banner.bin'), '-h',
                path.join('for PC', 'bootloader files', 'header.bin') ])

            ret_val = self.proc.wait()

            if ret_val == 0:

                # Hash bootloader.nds
                sha1_hash = sha1()

                with open('bootloader.nds', 'rb') as f:
                    sha1_hash.update(f.read())

                self.log.write('- bootloader.nds SHA1:\n  ' +
                    sha1_hash.digest().hex().upper())

                self.TThread = Thread(target=self.decrypt_nand)
                self.TThread.start()

            else:
                self.log.write(_('错误: 生成失败'))
                Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def decrypt_nand(self):
        if not self.nand_mode:
            self.files.append(self.console_id.get() + '.img')
        self.log.write(_('\n正在解密 NAND...'))

        try:
            self.proc = Popen([ twltool, 'nandcrypt', '--in', self.nand_file.get(), '--out',
                self.console_id.get() + '.img' ])

            ret_val = self.proc.wait()
            print("\n")

            if ret_val == 0:
                if self.nand_operation.get() == 2 or self.setup_operation.get() == 2:
                    self.TThread = Thread(target=self.mount_nand)
                    self.TThread.start()
                else:
                    self.TThread = Thread(target=self.extract_nand1 if (sysname == 'Windows' and self.setup_operation.get() == 1)
                        else self.extract_nand)
                    self.TThread.start()
            else:
                self.log.write(_('错误: 解密失败'))
                Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def extract_nand1(self):
        self.files.append('0.fat')
        self.log.write(_('\n正在从NAND中解压文件...'))

        try:
            self.proc = Popen([ _7z, 'x', '-bso0', '-y', self.console_id.get() + '.img', '0.fat' ])

            ret_val = self.proc.wait()

            if ret_val == 0:

                self.proc = Popen([ _7z, 'x', '-bso0', '-y', '-o' + self.sd_path, '0.fat' ])

                ret_val = self.proc.wait()

                if ret_val == 0:
                    self.TThread = Thread(target=self.get_launcher)
                    self.TThread.start()

                else:
                    self.log.write(_('错误: 解压失败'))

                    if path.exists(fatcat):
                        self.log.write(_('\n尝试使用fatcat...'))
                        self.TThread = Thread(target=self.extract_nand)
                        self.TThread.start()

                    else:
                        Thread(target=self.clean, args=(True,)).start()

            else:
                self.log.write(_('错误: 解压失败'))

                if path.exists(fatcat):
                    self.log.write(_('\n尝试使用fatcat...'))
                    self.TThread = Thread(target=self.extract_nand)
                    self.TThread.start()

                else:
                    Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)

            if path.exists(fatcat):
                self.log.write(_('\n尝试使用fatcat...'))
                self.TThread = Thread(target=self.extract_nand)
                self.TThread.start()

            else:
                Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def mount_nand(self):
        self.log.write(_('\n挂载解密的NAND镜像中...'))

        try:
            exe = osfmount

            cmd = [ osfmount, '-a', '-t', 'file', '-f', self.console_id.get() + '.img', '-m',
                '#:', '-o', 'ro,rem' ]

            if self.nand_mode:
                cmd[-1] = 'rw,rem'

            self.proc = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

            outs, errs = self.proc.communicate()

            if self.proc.returncode == 0:
                self.mounted = search(r'[a-zA-Z]:\s', outs.decode('utf-8')).group(0).strip()
                self.log.write(_('- 挂载到驱动器 ') + self.mounted)

            else:
                self.log.write(_('错误: 挂载失败'))
                Thread(target=self.clean, args=(True,)).start()
                return

            if self.nand_mode:
                self.TThread = Thread(target=self.unlaunch_proc)
                self.TThread.start()
            else:
                self.TThread = Thread(target=self.extract_nand2)
                self.TThread.start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def extract_nand(self):
        self.log.write(_('\n正在从NAND中解压文件...'))

        try:
            # DSi first partition offset: 0010EE00h
            self.proc = Popen([ fatcat, '-O', '1109504', '-x', self.sd_path,
                self.console_id.get() + '.img' ])

            ret_val = self.proc.wait()

            if ret_val == 0:
                self.TThread = Thread(target=self.get_launcher)
                self.TThread.start()

            else:
                self.log.write(_('错误: 解压失败'))
                Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def extract_nand2(self):
        self.log.write(_('\n正在从NAND中复制文件...'))
        # Reset copied files cache
        _path_created.clear()
        try:
            copy_tree(self.mounted, self.sd_path, preserve_mode=0, update=1)
            self.TThread = Thread(target=self.unmount_nand)
            self.TThread.start()
        except:
            self.log.write(_('错误: 复制失败'))
            self.TThread = Thread(target=self.unmount_nand1)
            self.TThread.start()


    ################################################################################################
    def get_launcher(self):
        app = self.detect_region()

        # Stop if no supported region was found
        if not app:
            Thread(target=self.clean, args=(True,)).start()
            return

        # Delete contents of the launcher folder as it will be replaced by the one from HiyaCFW
        launcher_folder = path.join(self.sd_path, 'title', '00030017', app, 'content')

        # Walk through all files in the launcher content folder
        for file in listdir(launcher_folder):
            file = path.join(launcher_folder, file)

            if _7z is not None:
                if self.setup_operation.get() == 1:
                    chmod(file, 438)
            remove(file)

        try:
            if not path.isfile(self.launcher_region):
                self.log.write(_('\n正在下载 ') + self.launcher_region + ' Launcher...')
                if self.altdl.get() == 1:
                    with urlopen('https://spblog.tk/somefiles/launchers/' + self.launcher_region) as src, open(self.launcher_region, 'wb') as dst:
                        copyfileobj(src, dst)
                else:
                    with urlopen('https://raw.githubusercontent.com'
                        '/R-YaTian/HHF-Toolkit/HiyaCFW-Helper-R3/launchers/' +
                        self.launcher_region) as src, open(self.launcher_region, 'wb') as dst:
                        copyfileobj(src, dst)

            self.log.write(_('- 正在解压Launcher...'))

            if self.launcher_region in ('CHN', 'KOR'):
                launcher_app = '00000000.app'
            elif self.launcher_region == 'USA-dev':
                launcher_app = '7412e50d.app'
                self.files.append('title.tmd')
            else:
                launcher_app = '00000002.app'

            self.files.append(launcher_app)

            # Prepare decryption params
            params = [ _7za, 'x', '-bso0', '-y', '-p' + app.lower(), self.launcher_region,
                launcher_app ]

            if launcher_app == '7412e50d.app':
                params.append('title.tmd')

            self.proc = Popen(params)

            ret_val = self.proc.wait()

            if ret_val == 0:

                # Hash launcher app
                sha1_hash = sha1()

                with open(launcher_app, 'rb') as f:
                    sha1_hash.update(f.read())

                self.log.write('- Patched Launcher SHA1:\n  ' +
                    sha1_hash.digest().hex().upper())

                self.TThread = Thread(target=self.install_hiyacfw, args=(launcher_app, launcher_folder, app))
                self.TThread.start()

            else:
                self.log.write(_('错误: 解压失败'))
                Thread(target=self.clean, args=(True,)).start()

        except IOError as e:
            print(e)
            self.log.write(_('错误: 无法下载 ') + self.launcher_region + ' Launcher')
            Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def install_hiyacfw(self, launcher_app, launcher_folder, app):
        self.log.write(_('\n正在复制HiyaCFW相关文件...'))

        # Reset copied files cache
        _path_created.clear()

        copy_tree(path.join('for SDNAND SD card', 'hiya'), path.join(self.sd_path, 'hiya'))
        copy_tree(path.join('for SDNAND SD card', 'photo'), path.join(self.sd_path, 'photo'))
        copyfile(path.join('for SDNAND SD card', 'hiya.dsi'), path.join(self.sd_path, 'hiya.dsi'))
        copyfile('bootloader.nds', path.join(self.sd_path, 'hiya', 'bootloader.nds'))
        copyfile(launcher_app, path.join(launcher_folder, launcher_app))

        tmd_src = path.join('for SDNAND SD card', 'title', '00030017', app, 'content', 'title.tmd')
        if launcher_app == '7412e50d.app':
            copyfile('title.tmd', path.join(launcher_folder, 'title.tmd'))
        else:
            copyfile(tmd_src, path.join(launcher_folder, 'title.tmd'))

        if self.devkp.get() == 1:
            dekp = path.join(self.sd_path, 'sys', 'dev.kp')
            if not path.exists(dekp):
                with open(dekp, 'wb+') as f:
                    f.seek(0,0)
                    f.read(0x04)
                    f.write(b'DUMMY')
                    f.close()
                self.log.write(_('"系统设置-数据管理"功能启用成功'))

        self.TThread = Thread(target=self.get_latest_twilight if self.twilight.get() == 1 else self.clean)
        self.TThread.start()
    def update_hiyacfw(self):
        self.log.write(_('\n正在更新HiyaCFW...'))

        # Reset copied files cache
        _path_created.clear()

        copyfile(path.join('for SDNAND SD card', 'hiya.dsi'), path.join(self.sd_path1, 'hiya.dsi'))

        self.TThread = Thread(target=self.get_latest_twilight)
        self.TThread.start()


    ################################################################################################
    def get_latest_twilight(self):
        filename = 'TWiLightMenu-DSi.7z' if self.is_tds == False else 'TWiLightMenu-3DS.7z'
        self.files.append(filename)
        self.files.append('BOOT.NDS')
        self.files.append('snemul.cfg')
        self.folders.append('_nds')
        self.folders.append('roms')
        self.folders.append('title')
        self.folders.append('hiya')

        try:
            if not path.isfile(filename):
                self.log.write(_('\n正在下载最新版本的TWiLightMenu++...'))
                if self.altdl.get() == 1:
                    with urlopen('https://spblog.tk/somefiles/' + filename) as src, open(filename, 'wb') as dst:
                        copyfileobj(src, dst)
                else:
                    with urlopen('https://github.com/DS-Homebrew/TWiLightMenu/releases/latest/download/' +
                        filename) as src, open(filename, 'wb') as dst:
                        copyfileobj(src, dst)

            self.log.write(_('- 正在解压 ') + filename[:-3] + _(' 压缩包...'))

            self.proc = Popen([ _7za, 'x', '-bso0', '-y', filename, '_nds', 'title',
                'hiya', 'roms', 'BOOT.NDS', 'snemul.cfg'])

            ret_val = self.proc.wait()

            if ret_val == 0:
                self.TThread = Thread(target=self.install_twilight, args=(filename[:-3],))
                self.TThread.start()

            else:
                self.log.write(_('错误: 解压失败'))
                Thread(target=self.clean, args=(True,)).start()

        except (URLError, IOError) as e:
            print(e)
            self.log.write(_('错误: 无法下载TWiLightMenu++'))
            Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def install_twilight(self, name):
        self.log.write(_('\n正在复制 ') + name + _(' 相关文件...'))

        if not self.adv_mode:
            copy_tree('_nds', path.join(self.sd_path, '_nds'), update=1)
            copy_tree('title', path.join(self.sd_path, 'title'), update=1)
            copy_tree('hiya', path.join(self.sd_path, 'hiya'), update=1)
            copy_tree('roms', path.join(self.sd_path, 'roms'), update=1)
            copyfile('BOOT.NDS', path.join(self.sd_path, 'BOOT.NDS'))
            copyfile('snemul.cfg', path.join(self.sd_path, 'snemul.cfg'))
        else:
            if self.updatehiya.get() == 1:
                copy_tree('title', path.join(self.sd_path, 'title'), update=1)
                copy_tree('hiya', path.join(self.sd_path, 'hiya'), update=1)
            copy_tree('_nds', path.join(self.sd_path1, '_nds'), update=1)
            copy_tree('roms', path.join(self.sd_path1, 'roms'))
            copyfile('BOOT.NDS', path.join(self.sd_path1, 'BOOT.NDS'))
            copyfile('snemul.cfg', path.join(self.sd_path1, 'snemul.cfg'))
        if self.appgen.get() == 1:
            if not self.adv_mode:
                agen(path.join(self.sd_path, 'title' , '00030004'), path.join(self.sd_path, 'roms'))
            else:
                agen(path.join(self.sd_path1, 'title' , '00030004'), path.join(self.sd_path1, 'roms'))
        if self.adv_mode and self.devkp.get() == 1:
            dekp = path.join(self.sd_path1, 'sys', 'dev.kp')
            if not path.exists(dekp):
                with open(dekp, 'wb+') as f:
                    f.seek(0,0)
                    f.read(0x04)
                    f.write(b'DUMMY')
                    f.close()
                self.log.write(_('"系统设置-数据管理"功能启用成功'))

        Thread(target=self.clean).start()


    ################################################################################################
    def clean(self, err=False):
        self.finish = True
        self.log.write(_('\n清理中...'))

        while len(self.folders) > 0:
            rmtree(self.folders.pop(), ignore_errors=True)

        while len(self.files) > 0:
            try:
                remove(self.files.pop())
            except:
                pass

        if err:
            if self.nand_mode:
                try:
                    remove(self.console_id.get() + '.img')
                except:
                    pass
            self.log.write(_('操作过程发生错误, 已终止\n'))
            return

        if self.nand_mode:
            file = self.console_id.get() + self.suffix + '.bin'
            try:
                rename(self.console_id.get() + '.img', file)
                self.log.write(_('\n完成!\n修改后的NAND已保存为') + file + '\n')
            except FileExistsError:
                remove(self.console_id.get() + '.img')
                self.log.write(_('\n操作终止!\n目标文件已存在于程序运行目录下, \n无法覆盖原文件\n'))
            return

        self.log.write(_('完成!\n弹出你的存储卡并插回到机器中\n'))
        if self.adv_mode and self.is_tds:
            self.log.write(_('对于3DS设备, 你还需要在机器上使用FBI完成Title的安装\n'))


    ################################################################################################
    def patcher(self, patchpath, filepath):
        patch_size = path.getsize(patchpath)

        patchfile = open(patchpath, 'rb')

        if patchfile.read(5) != b'PATCH':
            patchfile.close()
            raise Exception()

        target = open(filepath, 'r+b')

        # Read First Record
        r = patchfile.read(3)

        while patchfile.tell() not in [ patch_size, patch_size - 3 ]:
            # Unpack 3-byte pointers.
            offset = self.unpack_int(r)
            # Read size of data chunk
            r = patchfile.read(2)
            size = self.unpack_int(r)

            if size == 0:  # RLE Record
                r = patchfile.read(2)
                rle_size = self.unpack_int(r)
                data = patchfile.read(1) * rle_size

            else:
                data = patchfile.read(size)

            # Write to file
            target.seek(offset)
            target.write(data)
            # Read Next Record
            r = patchfile.read(3)

        if patch_size - 3 == patchfile.tell():
            trim_size = self.unpack_int(patchfile.read(3))
            target.truncate(trim_size)

        # Cleanup
        target.close()
        patchfile.close()


    ################################################################################################
    def unpack_int(self, bstr):
        # Read an n-byte big-endian integer from a byte string
        ( ret_val, ) = unpack_from('>I', b'\x00' * (4 - len(bstr)) + bstr)
        return ret_val


    ################################################################################################
    def detect_region(self):
        REGION_CODES = {
            '484e4143': 'CHN',
            '484e4145': 'USA',
            '484e414a': 'JAP',
            '484e414b': 'KOR',
            '484e4150': 'EUR',
            '484e4155': 'AUS'
        }
        REGION_CODES_DEV = {
            '484e4145': 'USA-dev',
        }
        base = self.mounted if self.nand_mode else self.sd_path
        # Autodetect console region
        try:
            for app in listdir(path.join(base, 'title', '00030017')):
                for file in listdir(path.join(base, 'title', '00030017', app, 'content')):
                    if file.endswith('.app'):
                        try:
                            if file.startswith("0000000"):
                                self.log.write(_('- 检测到 ') + REGION_CODES[app.lower()] +
                                     ' Launcher')
                                if not self.nand_mode:
                                    self.launcher_region = REGION_CODES[app.lower()]
                            else:
                                if self.nand_mode:
                                    self.log.write(_('- 检测到 ') + REGION_CODES[app.lower()] +
                                         '-dev Launcher')
                                else:
                                    self.log.write(_('- 检测到 ') + REGION_CODES_DEV[app.lower()] +
                                         ' Launcher')
                                    self.launcher_region = REGION_CODES_DEV[app.lower()]
                            return app

                        except KeyError:
                            self.log.write(_('错误: 在NAND中找不到受支持的Launcher'))
                            return False

            self.log.write(_('错误: 无法检测系统区域'))

        except OSError as e:
            self.log.write(_('错误: ') + e.strerror + ': ' + e.filename)

        return False


    ################################################################################################
    def unlaunch_proc(self):
        self.files.append('unlaunch.zip')
        self.files.append('UNLAUNCH.DSI')
        self.log.write(_('\n检查unlaunch状态中...'))

        app = self.detect_region()

        if not app:
            self.TThread = Thread(target=self.unmount_nand1)
            self.TThread.start()
            return

        tmd = path.join(self.mounted, 'title', '00030017', app, 'content', 'title.tmd')

        tmd_size = path.getsize(tmd)

        if tmd_size == 520:
            self.log.write(_('- 未安装,下载中...'))

            try:
                if not path.exists('unlaunch.zip'):
                    try:
                        filename = urlretrieve('http://problemkaputt.de/unlaunch.zip')[0]
                    except:
                        if loc == 'zh_CN':
                            filename = urlretrieve('http://spblog.tk/somefiles/unlaunch.zip')[0]
                        else:
                            raise IOError
                else:
                    filename = 'unlaunch.zip'

                exe = path.join(sysname, '7za')

                self.proc = Popen([ exe, 'x', '-bso0', '-y', filename, 'UNLAUNCH.DSI' ])

                ret_val = self.proc.wait()

                if ret_val == 0:

                    self.log.write(_('- 正在安装unlaunch...'))

                    self.suffix = '-unlaunch'

                    with open(tmd, 'ab') as f:
                        with open('UNLAUNCH.DSI', 'rb') as unl:
                            f.write(unl.read())

                    dekp = path.join(self.mounted, 'sys', 'dev.kp')
                    if not path.exists(dekp):
                        with open(dekp, 'wb+') as f:
                            f.seek(0,0)
                            f.read(0x04)
                            f.write(b'DUMMY')
                            f.close()

                    # Set files as read-only
                    for file in listdir(path.join(self.mounted, 'title', '00030017', app,
                        'content')):
                        file = path.join(self.mounted, 'title', '00030017', app, 'content', file)
                        chmod(file, 292)

                else:
                    self.log.write(_('错误: 解压失败'))
                    self.TThread = Thread(target=self.unmount_nand1)
                    self.TThread.start()
                    return

            except IOError as e:
                print(e)
                self.log.write(_('错误: 无法下载 unlaunch'))
                self.TThread = Thread(target=self.unmount_nand1)
                self.TThread.start()
                return

            except OSError as e:
                print(e)
                self.log.write(_('错误: 无法运行 ') + exe)
                self.TThread = Thread(target=self.unmount_nand1)
                self.TThread.start()
                return

        else:
            self.log.write(_('- 已安装, 卸载中...'))

            self.suffix = '-no-unlaunch'

            # Set files as read-write
            for file in listdir(path.join(self.mounted, 'title', '00030017', app, 'content')):
                file = path.join(self.mounted, 'title', '00030017', app, 'content', file)
                chmod(file, 438)

            with open(tmd, 'r+b') as f:
                f.truncate(520)

            dekp = path.join(self.mounted, 'sys', 'dev.kp')
            if not path.exists(dekp):
                with open(dekp, 'wb+') as f:
                    f.seek(0,0)
                    f.read(0x04)
                    f.write(b'DUMMY')
                    f.close()

        self.TThread = Thread(target=self.unmount_nand)
        self.TThread.start()


    ################################################################################################
    def unmount_nand(self):
        self.log.write(_('\n正在卸载NAND...'))

        try:
            exe = osfmount
            self.proc = Popen([ osfmount, '-D', '-m', self.mounted ])

            ret_val = self.proc.wait()

            if ret_val == 0:
                self.TThread = Thread(target=self.encrypt_nand if self.nand_mode else self.get_launcher)
                self.TThread.start()
            else:
                self.log.write(_('错误: 卸载失败'))
                Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()
    def unmount_nand1(self):
        self.log.write(_('\n正在卸载NAND...'))

        try:
            exe = osfmount
            self.proc = Popen([ osfmount, '-D', '-m', self.mounted ])

            ret_val = self.proc.wait()

            if ret_val == 0:
                Thread(target=self.clean, args=(True,)).start()

            else:
                self.log.write(_('错误: 卸载失败'))
                Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()

        except:
            pass
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def encrypt_nand(self):
        self.log.write(_('\n正在重加密NAND...'))

        try:
            self.proc = Popen([ twltool, 'nandcrypt', '--in', self.console_id.get() + '.img' ])

            ret_val = self.proc.wait()
            print("\n")

            if ret_val == 0:
                Thread(target=self.clean).start()

            else:
                self.log.write(_('错误: 加密失败'))
                Thread(target=self.clean, args=(True,)).start()

        except OSError as e:
            print(e)
            self.log.write(_('错误: 无法运行 ') + exe)
            Thread(target=self.clean, args=(True,)).start()


    ################################################################################################
    def remove_footer(self):
        self.log.write(_('\n正在移除No$GBA footer...'))

        file = self.console_id.get() + '-no-footer.bin'

        try:
            copyfile(self.nand_file.get(), file)

            # Back-up footer info
            with open(self.console_id.get() + '-info.txt', 'w') as f:
                f.write('eMMC CID: ' + self.cid.get() + '\r\n')
                f.write('Console ID: ' + self.console_id.get() + '\r\n')

            with open(file, 'r+b') as f:
                # Go to the No$GBA footer offset
                f.seek(-64, 2)
                # Remove footer
                f.truncate()
            self.finish = True
            self.log.write(_('\n完成!\n修改后的NAND已保存为\n') + file +
                _('\nfooter信息已保存到 ') + self.console_id.get() + '-info.txt\n')

        except IOError as e:
            print(e)
            self.log.write(_('错误: 无法打开 ') +
                path.basename(self.nand_file.get()))


    ################################################################################################
    def add_footer(self, cid, console_id):
        self.log.write(_('正在添加No$GBA footer...'))

        file = self.console_id.get() + '-footer.bin'

        try:
            copyfile(self.nand_file.get(), file)

            with open(file, 'r+b') as f:
                # Go to the No$GBA footer offset
                f.seek(-64, 2)
                # Read the footer's header :-)
                bstr = f.read(0x10)

                # Check if it already has a footer
                if bstr == b'DSi eMMC CID/CPU':
                    self.log.write(_('错误: 文件中已存在 No$GBA footer'))
                    f.close()
                    remove(file)
                    return

                # Go to the end of file
                f.seek(0, 2)
                # Write footer
                f.write(b'DSi eMMC CID/CPU')
                f.write(cid)
                f.write(console_id)
                f.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            self.finish = True
            self.log.write(_('\n完成!\n修改后的NAND已保存为\n') + file + '\n')

        except IOError as e:
            print(e)
            self.log.write(_('错误: 无法打开 ') +
                path.basename(self.nand_file.get()))


####################################################################################################
# Entry point

root = Tk()
sysname = system()

if sysname == 'Darwin':
    if getlocale()[0] is None:
        setlocale(LC_ALL, 'en_US.UTF-8')
    loc = getlocale()[0]
else:
    loc = getdefaultlocale()[0]
langs = path.join('i18n', loc, 'LC_MESSAGES', 'lang.mo')
lange = path.join('i18n', 'en_US', 'LC_MESSAGES', 'lang.mo')
langc = path.join('i18n', 'zh_CN', 'LC_MESSAGES', 'lang.mo')

if not path.exists(langc):
    root.withdraw()
    if loc == 'zh_CN':
        showerror('错误', '找不到程序默认语言文件')
    elif loc == 'zh_TW':
        showerror('錯誤', '找不到程式預設語言檔案')
    else:
        showerror('Error', 'The default language file not found')
    root.destroy()
    exit(1)

if loc != 'zh_CN':
    if path.exists(langs):
        lang = gettext.translation('lang', localedir='i18n', languages=[loc])
        lang.install()
    else:
        if loc == 'zh_TW' or loc == 'en_US':
            lang = gettext.translation('lang', localedir='i18n', languages=['zh_CN'])
            lang.install()
        elif path.exists(lange):
            lang = gettext.translation('lang', localedir='i18n', languages=['en_US'])
            lang.install()
        else:
            lang = gettext.translation('lang', localedir='i18n', languages=['zh_CN'])
            lang.install()
else:
    lang = gettext.translation('lang', localedir='i18n', languages=['zh_CN'])
    lang.install()

print(_('HiyaCFW Helper启动中...'))

fatcat = path.join(sysname, 'fatcat')
_7za = path.join(sysname, '7za')
twltool = path.join(sysname, 'twltool')
osfmount  = None
_7z = None

if sysname == 'Windows':
    fatcat += '.exe'
    _7za += '.exe'
    twltool += '.exe'

    pye = architecture()
    pybits = pye[0]

    if pybits == '64bit':
        osfmount = path.join(sysname, 'extras', 'OSFMount.com')
        if path.exists(osfmount):
            print(_('64位版本的OSFMount2模块已加载'))
        else:
            osfmount  = None
    else:
        try:
            if environ['PROGRAMFILES(X86)']:
                osfmount = path.join(sysname, 'extras', 'OSFMount.com')
                if path.exists(osfmount):
                    print(_('64位版本的OSFMount2模块已加载'))
                else:
                    osfmount  = None
        except KeyError:
            osfmount = path.join(sysname, 'extras', 'x86', 'OSFMount.com')
            if path.exists(osfmount):
                print(_('32位版本的OSFMount2模块已加载'))
            else:
                osfmount  = None

    _7z = path.join(sysname, '7z.exe')
    if path.exists(_7z):
        print(_('7-Zip模块已加载'))
    else:
         _7z = None

if not path.exists(fatcat):
    if osfmount or _7z is not None:
        fatcat = None
    else:
        root.withdraw()
        showerror(_('错误'), _('找不到Fatcat, 请确认此程序位于本工具目录的"{}"文件夹中').format(sysname))
        root.destroy()
        exit(1)

print(_('GUI初始化中...'))

root.title(_('HiyaCFW Helper V3.6.1R(BY天涯)'))
# Disable maximizing
root.resizable(0, 0)
# Center in window
root.eval('tk::PlaceWindow %s center' % root.winfo_toplevel())
app = Application(master=root)
app.mainloop()
