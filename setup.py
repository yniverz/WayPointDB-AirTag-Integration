from setuptools import setup

APP = ['AirTag-grabber.py']
OPTIONS = {
    'iconfile': 'favicon.png', 
    'argv_emulation': False,
    'plist': {
        'LSUIElement': True   # or 'NSUIElement': True to run without a full Dock icon,
    },
}

setup(
    app=APP,
    name='WayPointDB AirTags',
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
