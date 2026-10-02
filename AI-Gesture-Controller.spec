# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files
import os

block_cipher = None

# Collect mediapipe data files (tflite models, etc.)
mediapipe_datas = collect_data_files('mediapipe')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=mediapipe_datas,
    hiddenimports=[
        'camera',
        'camera.camera_manager',
        'vision',
        'vision.hand_tracker',
        'vision.landmark_processor',
        'gestures',
        'gestures.gesture_detector',
        'gestures.gesture_state',
        'gestures.steering_controller',
        'input',
        'input.keyboard_controller',
        'ui',
        'ui.main_window',
        'utils',
        'utils.logger',
        'utils.smoothing',
        'PIL._tkinter_finder'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI-Gesture-Controller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Set to False to hide terminal window in production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI-Gesture-Controller',
)
