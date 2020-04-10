# setup.py
# created: January 15, 2020
#
# Uses the CMake (https://cmake.org) tools to generate the platform-specific rhino3dm projects
# See related scripts in this folder for other steps in the process.
#
# This script is inspired by - but deviates from - the "Scripts To Rule Them All" pattern:
# https://github.com/github/scripts-to-rule-them-all

import subprocess
import sys
import os
import argparse
from sys import platform as _platform
from subprocess import Popen, PIPE
import shlex
import shutil
if sys.version_info[0] < 3:
    import imp
else:
    from importlib.machinery import SourceFileLoader
import time

# ---------------------------------------------------- Globals ---------------------------------------------------------

xcode_logging = False
verbose = False
overwrite = False
valid_platform_args = ["js", "ios", "macos", "android", "windows"]
platform_full_names = {'js': 'JavaScript', 'ios': 'iOS', 'macos': 'macOS', 'android': 'Android', 'windows':'Windows'}
script_folder = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
src_folder = os.path.abspath(os.path.join(script_folder, "..", "src"))
build_folder = os.path.abspath(os.path.join(src_folder, "build"))
librhino3dm_native_folder = os.path.abspath(os.path.join(src_folder, "librhino3dm_native"))

if sys.version_info[0] < 3:
    bootstrap = imp.load_source('bootstrap', os.path.join(script_folder, "bootstrap.py"))
else:
    bootstrap = SourceFileLoader('bootstrap', os.path.join(script_folder, "bootstrap.py")).load_module()

# ---------------------------------------------------- Logging ---------------------------------------------------------
# colors for terminal reporting
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_warning_message(warning_message):
    warning_prefix = " warning: "
    if xcode_logging:
        print(warning_prefix + warning_message)
    else:
        print(bcolors.BOLD + bcolors.FAIL + warning_prefix.upper() + bcolors.ENDC + bcolors.FAIL + warning_message +
              bcolors.ENDC)


def print_error_message(error_message):
    error_prefix = " error: "
    if xcode_logging:
        print(error_prefix + error_message)
    else:
        print(bcolors.BOLD + bcolors.FAIL + error_prefix.upper() + bcolors.ENDC + bcolors.FAIL + error_message +
              bcolors.ENDC)


def print_ok_message(ok_message):
    ok_prefix = " ok: "
    if xcode_logging:
        print(ok_prefix + ok_message)
    else:
        print(bcolors.BOLD + bcolors.OKBLUE + ok_prefix.upper() + bcolors.ENDC + bcolors.OKBLUE + ok_message +
              bcolors.ENDC)


# ------------------------------------------------ Command Runner ------------------------------------------------------

def run_command(command, suppress_errors=False):
    verbose = True #we don't yet have a command-line switch for this, if we ever need one.
    if suppress_errors == True:                
        dev_null = open(os.devnull, 'w')
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=dev_null)
    else:
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)    
    
    while True:
        line = process.stdout.readline()               
        if process.poll() is not None:
            break   
        if line:
            if sys.version_info[0] < 3:
                if verbose:
                    print(line.strip())
            else:
                if verbose:
                    line = line.decode('utf-8').strip()
                    print(line)
        elif suppress_errors == False:
            error = process.stderr.readline()                
            if error:
                if sys.version_info[0] < 3:
                    print_error_message(error.strip())
                    sys.exit(1)
                else:
                    error = error.decode('utf-8').strip()
                    print_error_message(error)
                    sys.exit(1)
            else:
                continue

    rc = process.poll()
    return rc


# ---------------------------------------------- Platform Setup --------------------------------------------------------
def print_platform_preamble(platform_target_name):
    print("")
    if xcode_logging:
        print("Setting up " + platform_target_name + "...")
    else:
        print(bcolors.BOLD + "Setting up " + platform_target_name + "..." + bcolors.ENDC)


def check_or_create_path(target_path):
    try:
        if not os.path.exists(target_path):
            os.mkdir(target_path)
    except:
        return ''
    
    return target_path


def overwrite_check(item_to_check):
    if os.path.exists(item_to_check):
        if not overwrite:
            print_warning_message("A configuration already appears in " + item_to_check + 
                                  ". Use --overwrite to replace.")
            return False
        if overwrite:
            if os.path.isfile(item_to_check):
                os.remove(item_to_check)
            if os.path.isdir(item_to_check):
                shutil.rmtree(item_to_check)
                time.sleep(2) # avoid any race-conditions with large folders
            return True
    else:
        return True


def setup_did_succeed(item_to_check):
    if os.path.exists(item_to_check):
        print_ok_message("successfully wrote: " + item_to_check)
        return True
    else:
        print_error_message("failed to configure and generate " + item_to_check)
        return False


def build_methodgen():
    if xcode_logging:
        print(" Building MethodGen...")
    else:
        print(bcolors.BOLD + " Building MethodGen..." + bcolors.ENDC)

    path_to_methodgen_csproj = os.path.abspath(os.path.join(src_folder, 'methodgen', 'methodgen.csproj'))
    msbuild_path = 'msbuild'
    # On Windows, call bootstrap to get msbuild's path and flip the path separators to appease run_command()
    if _platform == "win32" or _platform == "win64":
        build_tools = bootstrap.read_required_versions()
        msbuild_path = bootstrap.check_msbuild(build_tools["msbuild"]).replace('\\', '//')
        path_to_methodgen_csproj = path_to_methodgen_csproj.replace('\\', '//')
    
    command = msbuild_path + ' ' + path_to_methodgen_csproj +' /p:Configuration=Release'
    run_command(command)

    # Check to see if the MethodGen.exe was written...
    item_to_check = os.path.abspath(os.path.join(src_folder, 'MethodGen.exe'))
    if os.path.exists(item_to_check):
        print_ok_message("successfully built: " + item_to_check)
    else:
        print_error_message("failed to build " + item_to_check + " for macOS build")
        return False

    return True


def run_methodgen():
    if xcode_logging:
        print(" Running MethodGen...")
    else:
        print(bcolors.BOLD + " Running MethodGen..." + bcolors.ENDC)

    path_to_methodgen_exe = os.path.abspath(os.path.join(src_folder, "MethodGen.exe"))
    # On Windows, we need to flip the path separators to appease run_command()
    if _platform == "win32" or _platform == "win64":
        path_to_methodgen_exe = path_to_methodgen_exe.replace('\\', '//')

    if not os.path.exists(path_to_methodgen_exe):
        print_error_message("MethodGen.exe not found.")
        return False

    command = ''
    if _platform == "darwin":
        command = command + 'mono '

    path_to_cpp = librhino3dm_native_folder
    path_to_cs = os.path.abspath(os.path.join(src_folder, 'dotnet'))
    # On Windows, we need to flip the path separators to appease run_command()
    if _platform == "win32" or _platform == "win64":
        path_to_cpp = path_to_cpp.replace('\\', '//')
        path_to_cs = path_to_cs.replace('\\', '//')     
    path_to_replace = '../lib/opennurbs'
    item_to_check = os.path.abspath(os.path.join(path_to_cs, 'AutoNativeMethods.cs'))

    # remove any older file there...
    if os.path.exists(item_to_check):
        os.remove(item_to_check)

    command = command + path_to_methodgen_exe + " " + path_to_cpp + " " + path_to_cs + " " + path_to_replace + " rhino3dm"
    run_command(command)

    # Check to see if methodgen succeeded
    if os.path.exists(item_to_check):
        print_ok_message("successfully generated: " + item_to_check)
    else:
        print_error_message("failed to generate " + item_to_check + " for macOS build")
        return False


def setup_macos():
    if _platform != "darwin":
        print_error_message("Generating project file for macOS requires that you run this script on macOS")
        return False

    target_path = check_or_create_path(os.path.join(build_folder, platform_full_names.get("macos").lower()))
    target_file_name = "librhino3dm_native.xcodeproj"

    item_to_check = os.path.abspath(os.path.join(target_path, target_file_name))
    if not overwrite_check(item_to_check):
        return False
    
    os.chdir(target_path)

    # generate the project files
    print("")
    if xcode_logging:
        print("Generating xcodeproj files for macOS...")
    else:
        print(bcolors.BOLD + "Generating xcodeproj files for macOS..." + bcolors.ENDC)

    command = "cmake -G \"Xcode\" -DMACOS_BUILD=1 " + librhino3dm_native_folder
    run_command(command)
    
    # methogen
    build_methodgen()
    run_methodgen()

    return setup_did_succeed(item_to_check)


def setup_ios():
    if _platform != "darwin":
        print_error_message("Generating project file for iOS requires that you run this script on macOS")
        return False

    target_path = check_or_create_path(os.path.join(build_folder, platform_full_names.get("ios").lower()))
    target_file_name = "librhino3dm_native.xcodeproj"

    item_to_check = os.path.abspath(os.path.join(target_path, target_file_name))
    if not overwrite_check(item_to_check):
        return False

    os.chdir(target_path)

    # generate the project files
    print("")
    if xcode_logging:
        print("Generating xcodeproj files for iOS...")
    else:
        print(bcolors.BOLD + "Generating xcodeproj files for iOS..." + bcolors.ENDC)
    command = ("cmake -G \"Xcode\" -DCMAKE_TOOLCHAIN_FILE=../../src/ios.toolchain.cmake -DPLATFORM=OS64COMBINED " + 
               "-DDEPLOYMENT_TARGET=9.3 " + librhino3dm_native_folder)
    run_command(command)

    # methogen
    build_methodgen()
    run_methodgen()

    return setup_did_succeed(item_to_check)     


def setup_js():
    target_path = check_or_create_path(os.path.join(build_folder, platform_full_names.get("js").lower()))
    item_to_check = os.path.abspath(os.path.join(target_path, "Makefile"))

    if not overwrite_check(item_to_check):
        return False
    
    os.chdir(target_path)

    command = "emcmake cmake -DCMAKE_CXX_FLAGS=\"-s MODULARIZE=1 -s 'EXPORT_NAME=\\\"rhino3dm\\\"'\" " + src_folder
    try:
        p = subprocess.Popen(shlex.split(command), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    except OSError:
        print_error_message("could not find emcmake command.  Run the bootstrap.py --check emscripten")
        return False

    if sys.version_info[0] < 3:
        output = p.communicate()[0]
        if output:
            if verbose:
                print(output)
        else:
            print_error_message("failed to run emcmake cmake.")
    else:
        output, err = p.communicate()
        output = output.decode('utf-8')
        err = err.decode('utf-8')
        if output:
            if verbose:
                print(output)
        elif err:
            print_error_message(err)

    return setup_did_succeed(item_to_check)


def setup_android():
    # https://developer.android.com/ndk/guides/cmake.html
    # The Android toolchain file is in: <NDK>/build/cmake/android.toolchain.cmake
    # We need to call the bootstrap script to figure out which ndk is currently in use, in order
    # to set the ndk path
    build_tools = bootstrap.read_required_versions()
    android_ndk_path = bootstrap.check_ndk(build_tools["ndk"])
    android_toolchain_path = os.path.join(android_ndk_path, "build", "cmake", "android.toolchain.cmake")

    # construct the android build folder if we don't already have it.  since we'll be generating CMake projects to 
    # subfolders for each app_abi, this is different the other platforms we support...
    target_path = check_or_create_path(os.path.join(build_folder, platform_full_names.get("android").lower()))

    # CMake builds for a single target per build. To target more than one Android ABI, you must build once per ABI. 
    # It is recommended to use different build directories for each ABI to avoid collisions between builds.
    app_abis = ['armeabi-v7a', 'arm64-v8a', 'x86_64', 'x86']
    for app_abi in app_abis:
        # setup the build folders and clean previous builds if necessary...
        abi_target_path = check_or_create_path(os.path.join(target_path, app_abi))
        item_to_check = os.path.abspath(os.path.join(abi_target_path, "Makefile"))

        if not overwrite_check(item_to_check):
            return False

        os.chdir(abi_target_path)

        print("")
        if xcode_logging:
            print("Generating Makefile for Android (" + app_abi + ")...")
        else:
            print(bcolors.BOLD + "Generating Makefile Android (" + app_abi + ")..." + bcolors.ENDC)
    
        command = ("cmake -DCMAKE_TOOLCHAIN_FILE=" + android_toolchain_path + " -DANDROID_ABI=" + app_abi + 
                   " -DANDROID_PLATFORM=android-24 -DCMAKE_ANDROID_STL_TYPE=c++_shared " + librhino3dm_native_folder)
        run_command(command)

        time.sleep(2) # there can be a race-condition when generating the files on Android
        
        if not setup_did_succeed(item_to_check):
            break

    # methogen
    build_methodgen()
    run_methodgen()


def setup_windows():
    if _platform != "win32" and _platform != "win64":
        print_error_message("Generating project file for Windows requires that you run this script on Windows")
        return False
    
    target_path = check_or_create_path(os.path.join(build_folder, platform_full_names.get("windows").lower()))
    target_file_name = "librhino3dm_native.vcxproj"

    item_to_check = os.path.abspath(os.path.join(target_path, target_file_name))
    if not overwrite_check(item_to_check):
        return False

    os.chdir(target_path)

    # generate the project files
    print("")
    if xcode_logging:
        print("Generating vcxproj files for Windows native build...")
    else:
        print(bcolors.BOLD + "Generating vcxproj files for Windows native build" + bcolors.ENDC)
    global librhino3dm_native_folder
    librhino3dm_native_folder = librhino3dm_native_folder.replace('\\', '//')
    command = ("cmake -G \"Visual Studio 15 2017\" " + librhino3dm_native_folder)
    run_command(command)

    # methogen
    build_methodgen()
    run_methodgen()

    return setup_did_succeed(item_to_check)
    

def setup_handler(platform_target):
    if not os.path.exists(build_folder):
        os.mkdir(build_folder)

    if platform_target == "all":
        for target in valid_platform_args:
            print_platform_preamble(platform_full_names.get(target))
            getattr(sys.modules[__name__], 'setup_' + target)()
    else:
        print_platform_preamble(platform_full_names.get(platform_target))
        getattr(sys.modules[__name__], 'setup_' + platform_target)()


def delete_cache_file():
    # delete the bootstrapc cache file
    path_to_bootstrapc_file = os.path.join(script_folder, "bootstrap.pyc")
    if os.path.exists(path_to_bootstrapc_file):
        os.remove(path_to_bootstrapc_file)


# --------------------------------------------------- Main -------------------------------------------------------------
def main():
    global valid_platform_args

    # cli metadata
    description = "generate the project files for rhino3dm"
    epilog = "supported platforms: " + ", ".join(valid_platform_args)

    # Parse arguments
    parser = argparse.ArgumentParser(description=description, epilog=epilog)
    parser.add_argument('--platform', '-p', metavar='<platform>', nargs='+',
                        help="generates the project files for the platform(s) specified. valid arguments: all, "
                             + ", ".join(valid_platform_args) + ".")
    parser.add_argument('--verbose', '-v', action='store_true',
                        help="show verbose logging messages")
    parser.add_argument('--overwrite', '-o', action='store_true',
                        help="overwrite existing configurations (if found)")
    parser.add_argument('--xcodelog', '-x', action='store_true',
                        help="generate Xcode-compatible log messages (no colors or other Terminal-friendly gimmicks)")
    args = parser.parse_args()

    # User has not entered any arguments...
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    global xcode_logging
    xcode_logging = args.xcodelog

    if _platform == "win32":
        xcode_logging = True

    global verbose
    verbose = args.verbose

    global overwrite
    overwrite = args.overwrite

    os.chdir(script_folder)

    # setup platform(s)
    if args.platform is not None:
        for platform_target in args.platform:
            if (platform_target != "all") and (platform_target not in valid_platform_args):
                print_error_message(platform_target + " is not a valid platform argument. valid tool arguments: all, "
                                    + ", ".join(valid_platform_args) + ".")
                sys.exit(1)
            setup_handler(platform_target)

    delete_cache_file()


if __name__ == "__main__":
    main()


