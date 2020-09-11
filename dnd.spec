# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['dnd.py'],
             pathex=['Y:\\Project Notes\\Do Not Disturb Light'],
             binaries=[],
             datas=[('dndon.ico', '.'), ('dndoff.ico', '.'), ('dndunknown.ico', '.'), ('light_addresses.json', '.'), ('credentials.json', '.'), ('C:/Users/mark.bremer/.virtualenvs/do-not-disturb-light-I7ovfz7D/Lib/site-packages/google_api_python_client-1.11.0.dist-info/*', 'google_api_python_client-1.11.0.dist-info')],
             hiddenimports=['pystray._win32', 'google-api-python-client'],
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
