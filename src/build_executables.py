import os
import shutil
import subprocess
import sys

project_src:str = os.path.abspath(os.path.dirname(__file__))
project_root:str = os.path.abspath(os.path.join(project_src, ".."))
project_dist:str = os.path.join(project_root, "dist")
project_resources:str = os.path.join(project_root, "resources")
project_build:str = os.path.join(project_root, "build")
project_tmp:str = os.path.join(project_root, "tmp")

def build_all():
    """ OLD method, using bash script - ideally don't use this. """
    print("Building all with old bash script...")
    subprocess.run(["multi-build/build-clients.sh"], check=True)

def build_source():
    """ Zip all the source files and java .jar's into one archive. """
    top_level_dir:str = "dwh_upload_client"
    gui_build_dir = os.path.join(project_tmp, top_level_dir)
    os.path.exists(gui_build_dir) or os.makedirs(gui_build_dir)
    shutil.copytree(os.path.join(project_root, "multi-build", "gui-client-scripts"), os.path.join(gui_build_dir, ""), dirs_exist_ok=True)
    shutil.copytree(project_src, os.path.join(gui_build_dir, "src"), dirs_exist_ok=True)
    shutil.copytree(project_resources, os.path.join(gui_build_dir, "resources"), dirs_exist_ok=True)
    shutil.copy2(os.path.join(project_dist, "README.html"), gui_build_dir)

    ## Build the archive
    os.chdir(project_tmp)
    try:
        ## Remove old archive
        os.remove(os.path.join(project_dist, "client-source.zip"))
    except OSError:
        pass
    ## Remove other unwanted files before creating new archive
    try:
        shutil.rmtree(os.path.join(top_level_dir, "src", "__pycache__"))
        shutil.rmtree(os.path.join(top_level_dir, "src", "i2b2_upload_client", "__pycache__"))
        shutil.rmtree(os.path.join(top_level_dir, "src", "i2b2_upload_client", "gui", "__pycache__"))
        shutil.rmtree(os.path.join(top_level_dir, "src", "i2b2_upload_client", "logic", "__pycache__"))
    except OSError:
        pass
    try:
        os.remove(os.path.join(top_level_dir, "src", "test.py"))
        os.remove(os.path.join(top_level_dir, "src", "build_executables.py"))
    except OSError:
        pass
    ## Make archive including {top_level_dir} as top-level directory
    shutil.make_archive(os.path.join(project_dist, "client-source"), 'zip', ".")


def build_system_binaries():
    """ Use pyinstaller to build binary applications for linux and windows. """
    print("Building binaries with pyinstaller...")
    subprocess.run(["uv", "run", "pyinstaller", "dwh_client.spec"], check=True)
    ## Use wine to build the windows .exe
    subprocess.run(["uv", "run", "wine", "pyinstaller", "dwh_client.spec"], check=True)
    ## Rename the resulting files for clearer differentiation
    os.rename(os.path.join(project_dist, "dwh_client"), os.path.join(project_dist, "dwh_client_linux"))
    os.rename(os.path.join(project_dist, "dwh_client.exe"), os.path.join(project_dist, "dwh_client_windows.exe"))

def build_package():
    """ Use python packaging standards to build the source (sdist) and binary (wheel) distributions of the 'i2b2_upload_client' package (see also pyproject.toml). """
    print("Building package with uv...")
    subprocess.run(["uv", "build"], check=True)

def compile_gui():
    """ GUI window is designed in QT Designer which produces a .ui file, we convert it to python here. """
    print("Compiling GUI from .ui to .py with pyside-uic...")
    out_file = os.path.join(project_src, "i2b2_upload_client", "gui", "ui_mainwindow.py")
    subprocess.run(["uv", "run", "--dev", "pyside6-uic", os.path.join(project_src, "i2b2_upload_client", "gui", "mainWindow.ui"), "-o", out_file], check=True)

def convert_readme():
    """ Provide more user-friendly format of the README.md """
    subprocess.run(["pandoc", os.path.join(project_root, "README.md"), "-o", os.path.join(project_dist, "README.html")], check=True)

def convert_icon():
    """ This shouldn't need doing regularly, could just be done manually when needed. """
    print("Converting .webp image to .ico")
    subprocess.run(["magick", os.path.join(project_resources, "DzlLogoSymmetric.webp"), "-resize x64", "-gravity center", "-crop 64x64+0+0", "-flatten", "-colors 256", "-background transparent", os.path.join(project_resources, "DzlLogoSymmetric.ico")], check=True)

def update_version_file():
    """ For the system binary, we need access to a version file. """
    print("Updating version file for system binary usage")
    import toml
    my_pyproject = toml.load(os.path.join(project_root, 'pyproject.toml'))
    version = my_pyproject['project']['version']
    print('Setting version: ', version)
    open(os.path.join(project_build, 'version.txt'), 'w').write(version)

def main():
    """ Run through all the functions to build up each component. """
    update_version_file()
    # convert_icon()
    convert_readme()
    compile_gui()
    build_package()
    build_system_binaries()
    build_source()
    # build_all()
    try:
        ## Remove tmp dir where we build new archive
        shutil.rmtree(project_tmp)
    except OSError:
        pass

if __name__ == "__main__":
    main()
