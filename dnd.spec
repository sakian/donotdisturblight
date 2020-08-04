# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['dnd.py'],
             pathex=['Y:\\Project Notes\\Do Not Disturb Light'],
             binaries=[],
             datas=[('dndon.ico', '.'), ('dndoff.ico', '.'), ('dndunknown.ico', '.'), ('light_addresses.json', '.')],
             hiddenimports=['plyer.platforms.win.notification'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='dnd',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='dndon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='dnd')
