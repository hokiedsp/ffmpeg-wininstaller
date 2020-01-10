# Find the native FFMPEG includes and library
# This module defines
# FFMPEG_INCLUDE_DIR, where to find avcodec.h, avformat.h ...
# FFMPEG_LIBRARIES, the libraries to link against to use FFMPEG.
# FFMPEG_FOUND, If false, do not try to use FFMPEG.
# FFMPEG_ROOT, if this module use this path to find FFMPEG headers
# and libraries.

# %USER_PROFILE%/AppData/Local/Programs/<ffmpeg name>
# ~/Library/<ffmpeg name>/

# FFMPEG_DIR/FFMPEG_ROOT

import os
import sys
import requests
import urllib.parse as urlparse
import re
import tempfile
from tqdm import tqdm
import zipfile
import shutil
import subprocess

uninstallOld = True
force = False
baseUrl = 'https://ffmpeg.zeranoe.com/builds'
installDir = None
installDev = False
installShared = False
version = 'latest'  # 'nightly', 'x.x', 'x.x.x', 'yyyymmdd'

title = 'ffmpeg-installer'
envname = 'FFMPEG_PATH'
prbenvname = 'FFPROBE_PATH'

is64bits = sys.maxsize > 2**32
iswin = sys.platform == 'win32' or sys.platform == 'cygwin'
platform = 'win64' if iswin and is64bits else \
    'win32' if iswin and not is64bits else \
    None

# 'macos64' if sys.platform == 'darwin' and is64bits

if not platform:
    raise '{} does not support the specified operating system: {}'.format(
        title, sys.platform)

if not installDir:
    installDir = os.path.expanduser(os.sep.join(
        ["~", "AppData", "Local", "Programs", "ffmpeg"]))

installBinDir = os.path.join(installDir, 'bin')

curVer = ''
delOld = False
if os.path.exists(installDir):
    if os.path.exists(installBinDir):
        res = subprocess.run([os.path.join(
            installBinDir, "ffmpeg.exe"), "-version"], stdout=subprocess.PIPE)
        verStr = res.stdout.decode("utf-8")
        curVer = re.match(r'^ffmpeg version (\S+)', verStr).group(1)

    if uninstallOld:
        delOld = True
    elif not force:
        raise '{}: installDir already exists: {}'.format(title, installDir)

print("existing version: {}".format(curVer))

bintype = 'shared' if installShared else 'static'
releaseUrl = '/'.join((baseUrl, platform, bintype))

zipfmt = 'ffmpeg-{{}}-{}-{}.zip'.format(platform, bintype)

version = version.lower()
zipFile = zipfmt.format('latest') if (version == 'nightly') else \
    zipfmt.format(version) if version != 'latest' else \
    None

isNightlyBuild = bool(re.search(r'\d{8}', zipFile)) if zipFile else False
if not zipFile or isNightlyBuild:
    r = requests.get(releaseUrl)
    zipInfo = re.findall(
        r'<tr><td><a.+?>(.+?)</a></td><td>.+?</td><td>(.+?)</td></tr>', r.text)
    del zipInfo[0]  # remove "parent directory entry"

    if isNightlyBuild:
        zipre = zipfmt.format(r'{}-([\da-f]{{7}})'.format(version))
        zipFile = max(zipInfo, key=lambda info: info[1] if re.match(
            zipre, info[0]) else "0")[0]
        hash7 = re.match(zipre, zipFile).group(1)
        version = 'git-{}-{}-{}-{}'.format(
            version[0:4], version[4:6], version[6:8], hash7)
    else:
        zipre = zipfmt.format(r'(\d+\.\d+(?:\.\d+)?)')
        zipFile = max(zipInfo, key=lambda info: info[1] if re.match(
            zipre, info[0]) else "0")[0]
        version = re.match(zipre, zipFile).group(1)
        print('Latest version available: {}'.format(version))

zipUrl = '/'.join((releaseUrl, zipFile))

if curVer == version:
    print('Requested version already installed.')
else:
    with tempfile.TemporaryDirectory() as zipDir:
        zipPath = os.path.join(zipDir, zipFile)

        r = requests.get(zipUrl, stream=True)
        total_size = int(r.headers.get('content-length', 0))

        with open(zipPath, 'wb') as f:
            print('Downloading {}'.format(zipUrl))
            chunkSize = 32*1024
            pbar = tqdm(unit="B", total=int(
                r.headers['Content-Length']), unit_scale=True)
            for chunk in r.iter_content(chunk_size=chunkSize):
                if chunk:  # filter out keep-alive new chunks
                    pbar.update(len(chunk))
                    f.write(chunk)
            pbar.close()

        print("Unzipping...")
        with zipfile.ZipFile(zipPath, 'r') as zip_ref:
            zip_ref.extractall(zipDir)

        # successfully downloaded & unzipped, safe to delete old version
        if delOld:
            shutil.rmtree(installDir)

        # move the extracted file over to the final location
        d = os.listdir(zipDir)[0]
        print(os.path.join(zipDir, d))
        dest = shutil.move(os.path.join(zipDir, d), installDir,
                           copy_function=shutil.copytree)

# set environmental variable
updateEnv = not os.getenv(envname, False)
if not updateEnv and updateEnv != installDir:
    updateEnv = force

if updateEnv:
    print('Setting User Environmental Variable {}={}'.format(envname, installBinDir))
    batpath = os.path.join(os.path.dirname(__file__),'setenv.bat')
    subprocess.run([batpath, envname, installBinDir])
    subprocess.run([batpath, prbenvname, installBinDir])
    print('Done')
    
input("\nPress Enter to Exit...")
