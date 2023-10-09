"""
iFR - A simple yet powerful Flashrom GUI
By Jazzzny. Copyright (c) 2023
Licensed under the GNU GPL v2 license.
"""

import wx
import logging
import subprocess
import itertools
import os
import tempfile
import shutil

class Constants():
    def __init__(self):
        self.version = "1.0.0-devel"
        self.flashrom_version = self._get_flashrom_version()
        self.programmer = ""
        self.tempdir = self.CreateTemporaryDirectory()

    def _get_flashrom_version(self):
        ver = subprocess.Popen(["flashrom", "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for stdout_line in iter(ver.stdout.readline, ""):
            if "flashrom" in stdout_line:
                return stdout_line.split(" ")[1].strip()
    
    def CreateTemporaryDirectory(self):
        return tempfile.mkdtemp()

class Support():
    """
    Support class for iFR - Provides functions for padding and removing padding from ROM dumps
    """

    def RemovePadding(file_path):
        with open(file_path, 'rb') as file:
            padding_size = 0
            while True:
                # Read a byte from the end of the file
                file.seek(-1 - padding_size, 2)  # Seek from the end
                byte = file.read(1)

                if byte == b'':  # Reached the beginning of the file
                    break

                if byte == b'\xFF':
                    padding_size += 1
                else:
                    # Stop when non-padding content is encountered
                    break
                
            os.truncate(file_path, os.path.getsize(file_path) - padding_size)
            return padding_size

    def AddPadding(file_path, result_size):
        with open(file_path, 'ab') as file:
            file.seek(0, 2) # Seek to the end of the file
            current_size = file.tell()
            padding_size = result_size - current_size
            file.write(b'\xFF' * padding_size)
        return padding_size

class AboutDialog(wx.Dialog):
    """
    Displays information about the app
    """

    def __init__(self, parent, constants):
        self.constants = constants
        wx.Dialog.__init__(self, parent, title="")

        title = wx.StaticText(self, label="iFR")

        version = wx.StaticText(self, label=f"Version {constants.version}")

        description = wx.StaticText(self, label="A simple yet powerful Flashrom GUI")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(title, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.TOP|wx.LEFT|wx.RIGHT, 20)
        sizer.Add(version, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.TOP|wx.LEFT|wx.RIGHT, 10)
        sizer.Add(description, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.TOP|wx.LEFT|wx.RIGHT, 10)
        sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 10)

        self.SetSizer(sizer)
        self.Fit()

class GeneralPage(wx.StockPreferencesPage):
    def CreateWindow(self, parent):
        panel = wx.Panel(parent)
        panel.SetMinSize((380, 200))
        return panel

class AdvancedPage(wx.StockPreferencesPage):
    def CreateWindow(self, parent):
        panel = wx.Panel(parent)
        panel.SetMinSize((380, 200))
        return panel

class PreferencesDialog(wx.PreferencesEditor):
    def __init__(self):
        super().__init__()
        self.AddPage(GeneralPage(0))
        self.AddPage(AdvancedPage(1))

class PageRead(wx.Panel):
    """
    Generates the Read ROM page
    """

    def __init__(self, parent, constants):
        self.constants = constants
        wx.Panel.__init__(self, parent)

        self.filepicker_title = wx.StaticText(self, label="Save ROM to:")
        self.filepicker = wx.FilePickerCtrl(self, message="", wildcard="*.bin", style=wx.FLP_SAVE|wx.FLP_USE_TEXTCTRL)
        self.chip_dropdown_title = wx.StaticText(self, label="Select Chip:")
        self.chip_dropdown = wx.Choice(self)
        self.chip_autodetect = wx.Button(self, label="Auto Detect", size=(100, -1))
        self.chip_autodetect.Bind(wx.EVT_BUTTON, self.OnAutoDetect)
        self.chip_dropdown.Disable()
        self.show_upon_completion = wx.CheckBox(self, label="Reveal upon completion")
        self.remove_padding = wx.CheckBox(self, label="Remove padding from ROM dump")

        self.save_button = wx.Button(self, label="Read ROM", size=(150, -1))
        self.save_button.Bind(wx.EVT_BUTTON, self.OnSave)

        sizer = wx.BoxSizer(wx.VERTICAL)
        chip_sizer = wx.BoxSizer(wx.HORIZONTAL)
        chip_sizer.Add(self.chip_dropdown, 1, wx.EXPAND)
        chip_sizer.Add(self.chip_autodetect, 0, wx.LEFT, 5)
        
        sizer.Add(self.filepicker_title, 0, wx.ALIGN_CENTER | wx.TOP|wx.BOTTOM, 10)
        sizer.Add(self.filepicker, 0, wx.EXPAND | wx.LEFT|wx.RIGHT, 20)
        sizer.Add(self.chip_dropdown_title, 0, wx.ALIGN_CENTER | wx.TOP|wx.BOTTOM, 10)
        sizer.Add(chip_sizer, 0, wx.EXPAND | wx.LEFT|wx.RIGHT, 20)
        sizer.Add(self.show_upon_completion, 0, wx.ALIGN_CENTER | wx.TOP, 20)
        sizer.Add(self.remove_padding, 0, wx.ALIGN_CENTER | wx.TOP, 20)
        sizer.Add(self.save_button, 0, wx.ALIGN_CENTER | wx.TOP, 24)
        self.SetSizer(sizer)
    
    def OnSave(self, event):
        filepath = self.filepicker.GetPath()
        if filepath == "":
            logging.info("Please select a file to save to.")
            return
        if len(self.chip_dropdown.GetItems()) == 0:
            logging.info("Please run Auto Detect to determine your chip type.")
            return
        
        result = subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "-r", filepath, "--chip", self.chip_dropdown.GetStringSelection()], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for stdout_line in iter(result.stdout.readline, ""):
            logging.info(stdout_line.strip())
        if self.show_upon_completion.GetValue() and os.path.isfile(filepath):
            subprocess.Popen(["open", "-R", filepath])
        
        if self.remove_padding.GetValue() and os.path.isfile(filepath):
            logging.info("Removing padding from ROM dump...")
            result = Support.RemovePadding(filepath)
            logging.info(f"Removed {result} bytes of padding from ROM dump.")

        if not os.path.isfile(filepath):
            logging.info("ERROR: ROM dump was not saved. Please check the output above for more information.")
    
    def OnAutoDetect(self, event):
        if self.constants.programmer == "":
            logging.info("Please select a programmer.")
            return
        chips_raw = subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "--flash-name"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for stdout_line in iter(chips_raw.stdout.readline, ""):
            if "Found" in stdout_line:                
                logging.info("Found ROM chip: " + stdout_line.strip().split('"')[1]) # Cannot use f-string unless we use Python 3.12
                self.chip_dropdown.Append(stdout_line.strip().split('"')[1])
        if len(self.chip_dropdown.GetItems()) > 1:
            logging.info("WARNING: More than 1 possible chip detected. Please select the correct chip from the dropdown.")
            dlg = wx.MessageDialog(self, "More than 1 possible chip detected. Please select the correct chip from the dropdown.", "Warning", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            self.chip_dropdown.Enable()
        elif len(self.chip_dropdown.GetItems()) == 0:
            logging.info("No ROM chip detected. Please check your programmer connection.")
                 
class PageWrite(wx.Panel):
    """
    Generates the Write ROM page
    """

    def __init__(self, parent, constants):
        self.constants = constants
        wx.Panel.__init__(self, parent)

        self.filepicker_title = wx.StaticText(self, label="File to Flash:")
        self.filepicker = wx.FilePickerCtrl(self, message="", wildcard="ROM and BIN files (*.rom;*.bin)|*.rom;*.bin", style=wx.FLP_USE_TEXTCTRL)
        self.chip_dropdown_title = wx.StaticText(self, label="Select Chip:")
        self.chip_dropdown = wx.Choice(self)
        self.chip_autodetect = wx.Button(self, label="Auto Detect", size=(100, -1))
        self.chip_autodetect.Bind(wx.EVT_BUTTON, self.OnAutoDetect)
        self.chip_dropdown.Disable()
        self.pad_file = wx.CheckBox(self, label="Pad file to match chip size")

        self.save_button = wx.Button(self, label="Write ROM", size=(150, -1))
        self.save_button.Bind(wx.EVT_BUTTON, self.OnWrite)

        sizer = wx.BoxSizer(wx.VERTICAL)
        chip_sizer = wx.BoxSizer(wx.HORIZONTAL)
        chip_sizer.Add(self.chip_dropdown, 1, wx.EXPAND)
        chip_sizer.Add(self.chip_autodetect, 0, wx.LEFT, 5)
        
        sizer.Add(self.filepicker_title, 0, wx.ALIGN_CENTER | wx.TOP|wx.BOTTOM, 10)
        sizer.Add(self.filepicker, 0, wx.EXPAND | wx.LEFT|wx.RIGHT, 20)
        sizer.Add(self.chip_dropdown_title, 0, wx.ALIGN_CENTER | wx.TOP|wx.BOTTOM, 10)
        sizer.Add(chip_sizer, 0, wx.EXPAND | wx.LEFT|wx.RIGHT, 20)
        sizer.Add(self.pad_file, 0, wx.ALIGN_CENTER | wx.TOP|wx.BOTTOM, 20)
        sizer.Add(self.save_button, 0, wx.ALIGN_CENTER | wx.TOP, 40)
        self.SetSizer(sizer)

    def OnWrite(self, event):
        filepath = self.filepicker.GetPath()
        if filepath == "":
            logging.info("Please select a file to flash.")
            return
        if len(self.chip_dropdown.GetItems()) == 0:
            logging.info("Please run Auto Detect to determine your chip type.")
            return

        warndlg = wx.MessageDialog(self, "Are you sure you want to flash this ROM? This action cannot be undone. It is strongly recommmended to back up the ROM first!", "Warning", wx.YES_NO | wx.ICON_WARNING)
        if warndlg.ShowModal() == wx.ID_NO:
            return
        
        if self.pad_file.GetValue():
            logging.info("Padding temporary file to match chip size...")
            chipsize = subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "--chip", self.chip_dropdown.GetStringSelection(), "--flash-size"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.readlines()[-1].decode('utf-8').strip()
            filecopy = shutil.copy(filepath, self.constants.tempdir)
            padresult = Support.AddPadding(filecopy, int(chipsize))
            filepath = filecopy
            logging.info(f"Padded temporary file by {padresult} bytes.")
        result = subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "-w", filepath, "--chip", self.chip_dropdown.GetStringSelection()], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for stdout_line in iter(result.stdout.readline, ""):
            logging.info(stdout_line.strip())

    def OnAutoDetect(self, event):
        if self.constants.programmer == "":
            logging.info("Please select a programmer.")
            return
        chips_raw = subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "--flash-name"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for stdout_line in iter(chips_raw.stdout.readline, ""):
            if "Found" in stdout_line:                
                logging.info("Found ROM chip: " + stdout_line.strip().split('"')[1]) # Cannot use f-string unless we use Python 3.12
                self.chip_dropdown.Append(stdout_line.strip().split('"')[1])
        if len(self.chip_dropdown.GetItems()) > 1:
            logging.info("WARNING: More than 1 possible chip detected. Please select the correct chip from the dropdown.")
            dlg = wx.MessageDialog(self, "More than 1 possible chip detected. Please select the correct chip from the dropdown.", "Warning", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            self.chip_dropdown.Enable()
        elif len(self.chip_dropdown.GetItems()) == 0:
            logging.info("No ROM chip detected. Please check your programmer connection.")

class PageInfo(wx.Panel):
    """
    Generates the ROM Info page
    """

    def __init__(self, parent, constants):
        self.constants = constants
        wx.Panel.__init__(self, parent)

        self.chip_dropdown_title = wx.StaticText(self, label="Select Chip:")
        self.chip_dropdown = wx.Choice(self)
        self.chip_autodetect = wx.Button(self, label="Auto Detect", size=(100, -1))
        self.chip_autodetect.Bind(wx.EVT_BUTTON, self.OnAutoDetect)
        self.chip_dropdown.Disable()
        self.read_chip = wx.Button(self, label="Read Chip Information", size=(150, -1))
        self.read_chip.Bind(wx.EVT_BUTTON, self.GetChipInfo)

        self.list = wx.ListCtrl(self,style=wx.LC_REPORT|wx.LC_NO_HEADER)

        # Add some columns
        self.list.InsertColumn(0, "Name")
        self.list.InsertColumn(1, "Value")

        data = [
        ("Model", ""),
        ("Vendor", ""),
        ("Size", ""),
        ("Space Used", ""),
        ("Write Protection", "")
        ]

        # Add the rows
        for item in data:
            index = self.list.InsertItem(self.list.GetItemCount(), item[0])
            for col, text in enumerate(item[1:]):
                self.list.SetItem(index, col+1, text)

        # Set the width of the columns
        self.list.SetColumnWidth(0, 140)
        self.list.SetColumnWidth(1, 270)

        sizer = wx.BoxSizer(wx.VERTICAL)
        chip_sizer = wx.BoxSizer(wx.HORIZONTAL)
        chip_sizer.Add(self.chip_dropdown, 1, wx.EXPAND)
        chip_sizer.Add(self.chip_autodetect, 0, wx.LEFT, 5)
        sizer.Add(self.chip_dropdown_title, 0, wx.ALIGN_CENTER | wx.TOP|wx.BOTTOM, 5)
        sizer.Add(chip_sizer, 0, wx.EXPAND | wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        sizer.Add(self.read_chip, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT|wx.RIGHT, 0)
        self.SetSizer(sizer)
    
    def OnAutoDetect(self, event):
        if self.constants.programmer == "":
            logging.info("Please select a programmer.")
            return
        chips_raw = subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "--flash-name"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for stdout_line in iter(chips_raw.stdout.readline, ""):
            if "Found" in stdout_line:                
                logging.info("Found ROM chip: " + stdout_line.strip().split('"')[1]) # Cannot use f-string unless we use Python 3.12
                self.chip_dropdown.Append(stdout_line.strip().split('"')[1])
        if len(self.chip_dropdown.GetItems()) > 1:
            logging.info("WARNING: More than 1 possible chip detected. Please select the correct chip from the dropdown.")
            dlg = wx.MessageDialog(self, "More than 1 possible chip detected. Please select the correct chip from the dropdown.", "Warning", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            self.chip_dropdown.Enable()
        elif len(self.chip_dropdown.GetItems()) == 0:
            logging.info("No ROM chip detected. Please check your programmer connection.")
    
    def GetChipInfo(self, event):
        if len(self.chip_dropdown.GetItems()) == 0:
            logging.info("Please run Auto Detect to determine your chip type.")
            return
        result = subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "--chip", self.chip_dropdown.GetStringSelection(), "--flash-name"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result.wait()
        result = result.stdout.readlines()[-1].decode('utf-8').strip()
        
        vendor = result.split('"')[1]

        model = result.split('"')[3]
        size = subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "--chip", self.chip_dropdown.GetStringSelection(), "--flash-size"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        size.wait()
        size = int(size.stdout.readlines()[-1].decode('utf-8').strip())
        subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "-r", f"{self.constants.tempdir}/temp.bin", "--chip", self.chip_dropdown.GetStringSelection()], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).wait()
        if os.path.isfile(f"{self.constants.tempdir}/temp.bin"):
            space_used = size - Support.RemovePadding(f"{self.constants.tempdir}/temp.bin")
        write_protection = subprocess.Popen(["flashrom", "--programmer", self.constants.programmer, "--chip", self.chip_dropdown.GetStringSelection(), "--wp-status"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.readlines()[-1].decode('utf-8').strip()
        self.list.SetItem(0, 1, model)
        self.list.SetItem(1, 1, vendor)
        self.list.SetItem(2, 1, str(round(size/1024,1)) + " kB")
        if space_used:
            self.list.SetItem(3, 1, str(round(space_used/1024,1)) + " kB")
        else:
            self.list.SetItem(3, 1, "N/A")
        self.list.SetItem(4, 1, write_protection)

class wxLogHandler(logging.Handler):
    """
    Provides a logging handler for wxPython
    """

    def __init__(self, handler: wx.TextCtrl):
        logging.Handler.__init__(self)
        self.handler = handler
    def emit(self, record):
        wx.CallAfter(self.handler.AppendText, self.format(record) + '\n')

class iFR(wx.Frame):
    """
    Main iFR window
    """

    def __init__(self, parent, title):
        wx.SystemOptions.SetOption(u"osx.openfiledialog.always-show-types","1")
        super(iFR, self).__init__(parent, title=title, size=(450, 500))
        self.InitUI()

    def InitUI(self):
        self.constants = Constants()

        menubar = wx.MenuBar()
        fileMenu = wx.Menu()

        aboutItem = fileMenu.Append(wx.ID_ABOUT, "&About iFR")
#        settingsItem = fileMenu.Append(wx.ID_PREFERENCES)

        menubar.Append(fileMenu, "&Help")

        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)
#        self.Bind(wx.EVT_MENU, self.on_settings, id=wx.ID_PREFERENCES)

        panel = wx.Panel(self)
        self.toolbar = self.CreateToolBar(wx.TB_TEXT) 
                    
        rtool = self.toolbar.AddTool(14, 'Tools', wx.ArtProvider.GetBitmap(wx.ART_EXECUTABLE_FILE, wx.ART_TOOLBAR), shortHelp ="Radio Tool")
        self.toolbar.EnableTool(14, False)

        self.programmer_combo = wx.ComboBox(self.toolbar, choices=[], size=(125,30))
        self.programmer_combo.Bind(wx.EVT_COMBOBOX, self.OnProgrammerSelect)
        self.toolbar.AddControl(self.programmer_combo, "Select Programmer")
        self.toolbar.Realize() 
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(panel)
        self.notebook.AddPage(PageRead(self.notebook, self.constants), "Read ROM")
        self.notebook.AddPage(PageWrite(self.notebook, self.constants), "Write ROM")
        self.notebook.AddPage(PageInfo(self.notebook, self.constants), "ROM Info")
        self.consoletitle = wx.StaticText(panel, label="Output")
        self.textctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        self.textctrl.SetFont(wx.Font(12, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 2, wx.EXPAND | wx.ALL, 10)
        rectbox = wx.StaticBox(panel, -1)
        rectsizer = wx.StaticBoxSizer(rectbox, wx.VERTICAL)
        rectsizer.Add(self.consoletitle, 0, wx.ALIGN_CENTRE | wx.BOTTOM, 5)
        rectsizer.Add(self.textctrl, 1, wx.EXPAND | wx.ALL, 0)
        sizer.Add(rectsizer, 1, wx.EXPAND | wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        panel.SetSizer(sizer)
        self.Centre()
        self.SetSize((450, 500))
        self.SetMinSize((450, 500))
        self.Show()

        logObj = logging.getLogger()
        logObj.addHandler(wxLogHandler(self.textctrl))
        logObj.setLevel(logging.INFO)
        logging.info(f"Welcome to iFR {self.constants.version}\nA simple yet powerful Flashrom GUI\n\nFlashrom version: {self.constants.flashrom_version}\n")
        self.PopulateAvailableProgrammers()

    def PopulateAvailableProgrammers(self):
        output = subprocess.Popen(["flashrom"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output_lines = output.stdout.readlines()
        options_start = output_lines.index(b'Valid choices are:\n')
        options = [line.decode('utf-8').strip() for line in output_lines[options_start+1:]]
        programmers = list(itertools.chain.from_iterable([line.replace(".", "").replace(",", "").split() for line in options]))
        
        for programmer in programmers:
            self.programmer_combo.Append(programmer)
    
    def OnProgrammerSelect(self, event):
        self.constants.programmer = self.programmer_combo.GetValue()
        logging.info(f"Programmer set to {self.constants.programmer}")
    
    def on_about(self, event):
        dialog = AboutDialog(self, self.constants)
        dialog.Centre()
        dialog.ShowModal()
        dialog.Destroy()
    
#    def on_settings(self, event):
#        dialog = PreferencesDialog()
#        dialog.Show(self)

if __name__ == '__main__':
    app = wx.App()
    iFR(None, title='iFR')
    app.MainLoop()
