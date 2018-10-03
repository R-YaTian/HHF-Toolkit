#!/usr/bin/python

from Tkinter import *
from tkMessageBox import showerror
from tkFileDialog import askopenfilename
from platform import system
import os
import ctypes
from sys import exit
from threading import Thread
from binascii import hexlify
import hashlib
from urllib import urlopen, urlretrieve
from json import loads as jsonify
from subprocess import Popen, PIPE
from struct import unpack_from
from re import search
from shutil import rmtree
from distutils.dir_util import copy_tree


####################################################################################################

class Application(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)

        self.pack()

        # First row
        f1 = LabelFrame(self, text='NAND file with No$GBA footer', padx=10, pady=10)

        self.nand_file = StringVar()
        Entry(f1, textvariable=self.nand_file, state='readonly', width=40).pack(side='left')

        Button(f1, text='...', command=self.choose_nand).pack(side='left')

        f1.pack(padx=10, pady=10)

        # Second row
        f2 = LabelFrame(self, text='Decrypted DSi system menu launcher app', padx=10, pady=10)

        self.launcher_file = StringVar()
        Entry(f2, textvariable=self.launcher_file, state='readonly', width=40).pack(side='left')

        Button(f2, text='...', command=self.choose_launcher).pack(side='left')

        f2.pack(padx=10, pady=10)

        self.start_button = Button(self, text='Start', width=16, command=self.hiya, state=DISABLED)
        self.start_button.pack()

        Button(self, text='Quit', command=root.destroy, width=16).pack(pady=10)


    ################################################################################################
    def choose_nand(self):
        name = askopenfilename(filetypes=( ( 'nand.bin', '*.bin' ), ( 'DSi-1.mmc', '*.mmc' ) ))
        self.nand_file.set(name)

        self.start_button['state'] = (NORMAL if self.nand_file.get() != ''
            and self.launcher_file.get() != '' else DISABLED)


    ################################################################################################
    def choose_launcher(self):
        name = askopenfilename(filetypes=( ( '00000002.app', '*.app' ), ))
        self.launcher_file.set(name)

        self.start_button['state'] = (NORMAL if self.nand_file.get() != ''
            and self.launcher_file.get() != '' else DISABLED)


    ################################################################################################
    def hiya(self):
        dialog = Toplevel(self)
        # Open as dialog (parent disabled)
        dialog.grab_set()
        dialog.title('Status')
        # Disable maximizing
        dialog.resizable(0, 0)

        frame = Frame(dialog, bd=2, relief=SUNKEN)

        scrollbar = Scrollbar(frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.log = Listbox(frame, selectmode=SINGLE, bd=0, width=50, height=20, yscrollcommand=scrollbar.set)
        self.log.pack()

        scrollbar.config(command=self.log.yview)

        frame.pack()

        Button(dialog, text='Close', command=dialog.destroy, width=16).pack(pady=10)

        # Center in window
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        dialog.geometry('%dx%d+%d+%d' % (width, height, root.winfo_x() + (root.winfo_width() / 2) -
            (width / 2), root.winfo_y() + (root.winfo_height() / 2) - (height / 2)))

        Thread(target=self.check_nand).start()


    ################################################################################################
    def check_nand(self):
        self.log.insert(END, 'Checking NAND file...')

        # Read the NAND file
        try:
            with open(self.nand_file.get(), 'rb') as f:
                # Go to the No$GBA footer offset
                f.seek(0xF000000)
                # Read the footer's header :-)
                bstr = f.read(0x10)

                if bstr == b'DSi eMMC CID/CPU':
                    # Read the CID
                    bstr = f.read(0x10)
                    self.log.insert(END, 'eMMC CID  : ' + hexlify(bstr).upper())

                    # Read the console ID
                    bstr = f.read(8)
                    self.console_id = hexlify(bytearray(reversed(bstr))).upper()
                    self.log.insert(END, 'Console ID: ' + self.console_id)

                    Thread(target=self.check_launcher).start()

                else:
                    self.log.insert(END, 'ERROR: No$GBA footer not found')

        except IOError:
            self.log.insert(END, 'ERROR: Could not open the file ' + os.path.basename(self.nand_file.get()))


    ################################################################################################
    def check_launcher(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Checking launcher file...')

        self.launcher_region = ''

        expected_sha1s = {
            'USA': '1339bd7457484839f1d71f27de2f8da8098834b4',
            'JAP': '69c422a1ab1f26344a3d2b294ec714db362f57f0',
            'EUR': 'c5a3507181489f5190976a905b2953799e421363',
            'AUS': '8f79c6c1442d3e33d211454ec92bbe42c94a599d'
        }

        sha1 = hashlib.sha1()

        # Read the launcher file
        try:
            with open(self.launcher_file.get(), 'rb') as f:
                sha1.update(f.read())

            sha1_hex = sha1.hexdigest()

            for region, expected_sha1 in expected_sha1s.items():
                if sha1_hex == expected_sha1:
                    self.launcher_region = region
                    break

            if (self.launcher_region == ''):
                self.log.insert(END, 'ERROR: Launcher is not v512 of AUS, USA, EUR or JAP')

            else:
                self.log.insert(END, 'Launcher region: ' + self.launcher_region)
                Thread(target=self.get_latest_hiyacfw).start()

        except IOError:
            self.log.insert(END, 'ERROR: Could not open the file 00000002.app')


    ################################################################################################
    def get_latest_hiyacfw(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Downloading and extracting latest HiyaCFW release...')

        try:
            txt = urlopen('https://api.github.com/repos/Robz8/hiyaCFW/releases/latest')
            latest = jsonify(txt.read())
            txt.close()

            urlretrieve(latest['assets'][0]['browser_download_url'], 'HiyaCFW.7z')

            exe = os.path.join(sysname, '7zDec')

            proc = Popen([ exe, 'x', 'HiyaCFW.7z' ])

            ret_val = proc.wait()

            if ret_val == 0:
                Thread(target=self.decrypt_launcher).start()

            else:
                self.log.insert(END, 'Extractor failed')

        except IOError:
            self.log.insert(END, 'ERROR: Could not get HiyaCFW')

        except OSError:
            self.log.insert(END, 'ERROR: Could not execute ' + exe)


    ################################################################################################
    def decrypt_launcher(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Decrypting launcher...')

        exe = os.path.join('for PC', 'twltool') if sysname == 'Windows' else os.path.join(sysname,
            'twltool')

        try:
            proc = Popen([ exe, 'modcrypt', '--in', self.launcher_file.get(), '--out',
                '00000002.app' ])

            ret_val = proc.wait()

            if ret_val == 0:
                Thread(target=self.patch_launcher).start()

            else:
                self.log.insert(END, 'Decryptor failed')

        except OSError:
            self.log.insert(END, 'ERROR: Could not execute ' + exe)


    ################################################################################################
    def patch_launcher(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Patching launcher...')

        patch = os.path.join('for PC', 'v1.4 Launcher (00000002.app)' +
            (' (JAP-KOR)' if self.launcher_region == 'JAP' else '') + ' patch.ips')

        try:
            self.patcher(patch, '00000002.app')

            Thread(target=self.extract_bios).start()

        except IOError:
            self.log.insert(END, 'ERROR: Could not patch BIOS')

        except Exception:
            self.log.insert(END, 'ERROR: Invalid patch header')


    ################################################################################################
    def extract_bios(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Extracting ARM7/ARM9 BIOS from NAND...')

        exe = os.path.join('for PC', 'twltool') if sysname == 'Windows' else os.path.join(sysname,
            'twltool')

        try:
            proc = Popen([ exe, 'boot2', '--in', self.nand_file.get() ])

            ret_val = proc.wait()

            if ret_val == 0:
                Thread(target=self.patch_bios).start()

            else:
                self.log.insert(END, 'Extractor failed')

        except OSError:
            self.log.insert(END, 'ERROR: Could not execute ' + exe)


    ################################################################################################
    def patch_bios(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Patching ARM7/ARM9 BIOS...')

        try:
            self.patcher(os.path.join('for PC', 'bootloader files', 'bootloader arm7 patch.ips'),
                'arm7.bin')

            self.patcher(os.path.join('for PC', 'bootloader files', 'bootloader arm9 patch.ips'),
                'arm9.bin')

            Thread(target=self.arm9_prepend).start()

        except IOError:
            self.log.insert(END, 'ERROR: Could not patch BIOS')

        except Exception:
            self.log.insert(END, 'ERROR: Invalid patch header')


    ################################################################################################
    def arm9_prepend(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Prepending data to ARM9 BIOS...')

        try:
            with open('arm9.bin', 'rb') as f:
                data = f.read()

            with open('arm9.bin', 'wb') as f:
                with open(os.path.join('for PC', 'bootloader files',
                    'bootloader arm9 append to start.bin'), 'rb') as pre:
                    f.write(pre.read())

                f.write(data)

            Thread(target=self.make_bootloader).start()

        except IOError:
            self.log.insert(END, 'ERROR: Could not prepend data to ARM9 BIOS')


    ################################################################################################
    def make_bootloader(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Generating new bootloader...')

        exe = (os.path.join('for PC', 'bootloader files', 'ndstool') if sysname == 'Windows' else
            os.path.join(sysname, 'ndsblc'))

        try:
            proc = Popen([ exe, '-c', 'bootloader.nds', '-9', 'arm9.bin', '-7', 'arm7.bin', '-t',
                os.path.join('for PC', 'bootloader files', 'banner.bin'), '-h',
                os.path.join('for PC', 'bootloader files', 'header.bin') ])

            ret_val = proc.wait()

            if ret_val == 0:
                Thread(target=self.decrypt_nand).start()

            else:
                self.log.insert(END, 'Generator failed')

        except OSError:
            self.log.insert(END, 'ERROR: Could not execute ' + exe)


    ################################################################################################
    def decrypt_nand(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Decrypting NAND...')

        exe = os.path.join('for PC', 'twltool') if sysname == 'Windows' else os.path.join(sysname,
            'twltool')

        try:
            proc = Popen([ exe, 'nandcrypt', '--in', self.nand_file.get(), '--out',
            	self.console_id + '.img' ])

            ret_val = proc.wait()

            if ret_val == 0:
                Thread(target=self.mount_nand).start()

            else:
                self.log.insert(END, 'Decryptor failed')

        except OSError:
            self.log.insert(END, 'ERROR: Could not execute ' + exe)


    ################################################################################################
    def mount_nand(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Mounting decrypted NAND...')

        try:
            if sysname == 'Windows':
                exe = osfmount

                proc = Popen([ osfmount, '-a', '-t', 'file', '-f', self.console_id + '.img', '-m',
                    '#:', '-o', 'ro,rem' ], stdin=PIPE, stdout=PIPE, stderr=PIPE)

                outs, errs = proc.communicate()

                if proc.returncode == 0:
                    self.mounted = re.search(r'[a-zA-Z]:\s', outs).group(0).strip()
                    self.log.insert(END, 'Mounted on drive ' + self.mounted)

                    Thread(target=self.extract_nand).start()

                else:
                    self.log.insert(END, 'Mounter failed')

            elif sysname == 'Darwin':
                exe = 'hdiutil'

                proc = Popen([ exe, 'attach', '-readonly', '-imagekey',
                    'diskimage-class=CRawDiskImage', '-nomount', self.console_id + '.img' ],
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)

                outs, errs = proc.communicate()

                if proc.returncode == 0:
                    self.raw_disk = re.search(r'^\/dev\/disk\d+', outs).group(0)
                    self.log.insert(END, 'Mounted raw disk on ' + self.raw_disk)

                    proc = Popen([ exe, 'mount', '-readonly', self.raw_disk + 's1' ], stdin=PIPE,
                        stdout=PIPE, stderr=PIPE)

                    outs, errs = proc.communicate()

                    if proc.returncode == 0:
                        self.mounted = re.search(r'\/Volumes\/.+', outs).group(0)
                        self.log.insert(END, 'Mounted volume on ' + self.mounted)

                        Thread(target=self.extract_nand).start()

                    else:
                        self.log.insert(END, 'Mounter failed')

                else:
                    self.log.insert(END, 'Mounter failed')

            else:  # Linux
                exe = 'losetup'

                proc = Popen([ exe, '-P', '-r', '-f', '--show', self.console_id + '.img' ],
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
                outs, errs = proc.communicate()

                if proc.returncode == 0:
                    self.loop_dev = re.search(r'\/dev\/loop\d+', outs).group(0)
                    self.log.insert(END, 'Mounted loop device on ' + self.loop_dev)

                    exe = 'mount'

                    self.mounted = '/mnt'

                    proc = Popen([ exe, '-r', '-t', 'vfat', self.loop_dev + 'p1', self.mounted ])

                    ret_val = proc.wait()

                    if ret_val == 0:
                        self.log.insert(END, 'Mounted partition on ' + self.mounted)

                        Thread(target=self.extract_nand).start()

                    else:
                        self.log.insert(END, 'Mounter failed')

                else:
                    self.log.insert(END, 'Mounter failed')

        except OSError:
            self.log.insert(END, 'ERROR: Could not execute ' + exe)


    ################################################################################################
    def extract_nand(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Extracting files from NAND...')

        rmtree('out', ignore_errors=True)
        copy_tree(self.mounted, 'out')

        Thread(target=self.unmount_nand).start()


    ################################################################################################
    def unmount_nand(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Unmounting NAND...')

        try:
            if sysname == 'Windows':
                exe = osfmount

                proc = Popen([ osfmount, '-D', '-m', self.mounted ])

            elif sysname == 'Darwin':
                exe = 'hdiutil'

                proc = Popen([ exe, 'detach', self.raw_disk ])

            else:  # Linux
                exe = 'umount'

                proc = Popen([ exe, self.mounted ])

                ret_val = proc.wait()

                if ret_val == 0:
                    exe = 'losetup'

                    proc = Popen([ exe, '-d', self.loop_dev ])

                else:
                    self.log.insert(END, 'Unmounter failed')
                    return

            ret_val = proc.wait()

            if ret_val == 0:
                Thread(target=self.install_hiyacfw).start()

            else:
                self.log.insert(END, 'Unmounter failed')

        except OSError:
            self.log.insert(END, 'ERROR: Could not execute ' + exe)


    ################################################################################################
    def install_hiyacfw(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Copying HiyaCFW files...')

        region_codes = {
            'USA': '45',
            'JAP': '4a',
            'EUR': '50',
            'AUS': '55'
        }

        copy_tree('for SDNAND SD card', 'out', update=1)
        os.rename('bootloader.nds', os.path.join('out', 'hiya', 'bootloader.nds'))
        os.rename('00000002.app', os.path.join('out', 'title', '00030017', '484e41' +
        	region_codes[self.launcher_region], 'content', '00000002.app'))

        Thread(target=self.clean).start()


    ################################################################################################
    def clean(self):
        self.log.insert(END, '')
        self.log.insert(END, 'Cleaning...')

        rmtree('for PC', ignore_errors=True)
        rmtree('for regularly used SD card', ignore_errors=True)
        rmtree('for SDNAND SD card', ignore_errors=True)
        os.remove(self.console_id + '.img')
        os.remove('arm7.bin')
        os.remove('arm9.bin')
        os.remove('HiyaCFW.7z')

        self.log.insert(END, '')
        self.log.insert(END, 'Done!')
        self.log.insert(END, 'Move the contents of the out')
        self.log.insert(END, "folder to your DSi's SD card")


    ################################################################################################
    def patcher(self, patchpath, filepath):
        patch_size = os.path.getsize(patchpath)

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


####################################################################################################

sysname = system()

root = Tk()

if sysname == 'Windows':
    osfmount = os.path.join(os.environ['PROGRAMFILES'], 'OSFMount', 'OSFMount.com')

    if not os.path.exists(osfmount):
        root.withdraw()
        showerror('Error', 'This script needs OSFMount to run. Please install it.')
        root.destroy()
        exit(1)

    elif ctypes.windll.shell32.IsUserAnAdmin() == 0:
        root.withdraw()
        showerror('Error', 'This script needs to be run with administrator privileges.')
        root.destroy()
        exit(1)

elif sysname == 'Linux' and os.getuid() != 0:
    root.withdraw()
    showerror('Error', 'This script needs to be run with sudo.')
    root.destroy()
    exit(1)

root.title('HiyaCFW Helper')
# Disable maximizing
root.resizable(0, 0)
# Center in window
root.eval('tk::PlaceWindow %s center' % root.winfo_toplevel())
app = Application(master=root)
app.mainloop()
