#                       _                                                 _                _      _
#   _ __    __ _   ___ | | __  __ _   __ _   ___          ___  _ __ ___  | |__    ___   __| |  __| |  ___  _ __
#  | '_ \  / _` | / __|| |/ / / _` | / _` | / _ \        / _ \| '_ ` _ \ | '_ \  / _ \ / _` | / _` | / _ \| '__|
#  | |_) || (_| || (__ |   < | (_| || (_| ||  __/       |  __/| | | | | || |_) ||  __/| (_| || (_| ||  __/| |
#  | .__/  \__,_| \___||_|\_\ \__,_| \__, | \___| _____  \___||_| |_| |_||_.__/  \___| \__,_| \__,_| \___||_|
#  |_|                               |___/       |_____|
#
# version 1.0.0  2020-05-07
#

import base64
import zlib
from pathlib import Path
import sys


def package_location(package):
    for path in sys.path:
        path = Path(path)
        if (path.stem == "site-packages") or (path.resolve() == Path.cwd().resolve()):
            if (path / package).is_dir():
                if (path / package / "__init__.py").is_file():
                    return path / package
            if (path / (package + ".py")).is_file():
                return path / (package + ".py")
    return None


def embed_package(infile, package, prefer_installed=False, py_files_only=True, outfile=None):
    """
    build outfile from infile with package(s) as mentioned in package embedded

    Arguments
    ---------
    infile : str or pathlib.Path
        input file

    package : str or tuple/list of str
        package(s) to be embedded

    prefer_installed : bool or tuple/list of bool
        if False (default), mark as to always use the embedded version (at run time)
        if True, mark as to try and use the installed version of package (at run time)
        if multiple packages are specified and prefer_installed is a scalar, the value will
            be applied for all packages

    py_files_only : bool or tuple/list of bool
        if True (default), embed only .py files
        if False, embed all files, which can be useful for certain data, fonts, etc, to be present
        if multiple packages are specified and py_files_only is a scalar, the value will
            be applied for all packages

    outfile : str or pathlib.Path
        output file
        if None, use infile with extension .embedded.py instead of .py

    Returns
    -------
    packages embedded : list
        when a package is not found or not embeddable, it is excluded from this list
    """
    infile = Path(infile)  # for API
    if outfile is None:
        outfile = infile.parent / (infile.stem + ".embedded" + infile.suffix)

    with open(infile, "r") as f:
        inlines = f.read().split("\n")

    with open(outfile, "w") as out:
        if inlines[0].startswith("#!"):
            print(inlines[0], file=out)
            inlines.pop(0)

        if isinstance(package, (tuple, list)):
            packages = package
        else:
            packages = [package]
        n = len(packages)
        prefer_installeds = prefer_installed if isinstance(prefer_installed, (tuple, list)) else n * [prefer_installed]
        py_files_onlys = py_files_only if isinstance(py_files_only, (tuple, list)) else n * [py_files_only]
        if len(prefer_installeds) != n:
            raise ValueError(f"length of package != length of prefer_installed")
        if len(py_files_onlys) != n:
            raise ValueError(f"length of package != length of py_files_only")

        embedded_packages = [package for package in packages if package_location(package)]

        print("#  file generated by package_embedder from", file=out)
        print("#      source file: " + str(infile), file=out)
        print("#      packages embedded: " + ", ".join(embedded_packages), file=out)
        print("", file=out)
        print("def copy_contents(package, prefer_installed, filecontents):", file=out)
        print("    import tempfile", file=out)
        print("    import shutil", file=out)
        print("    import sys", file=out)
        print("    from pathlib import Path", file=out)
        print("    import zlib", file=out)
        print("    import base64", file=out)
        print("    if package in sys.modules:", file=out)
        print("        return", file=out)
        print("    if prefer_installed:", file=out)
        print("        for dir in sys.path:", file=out)
        print("            dir = Path(dir)", file=out)
        print("            if (dir / package).is_dir() and (dir / package / '__init__.py').is_file():", file=out)
        print("                return", file=out)
        print("            if (dir / (package + '.py')).is_file():", file=out)
        print("                return", file=out)
        print("    target_dir = Path(tempfile.gettempdir()) / ('embedded_' + package) ", file=out)
        print("    if target_dir.is_dir():", file=out)
        print("        shutil.rmtree(target_dir, ignore_errors=True)", file=out)
        print("    for file, contents in filecontents:", file=out)
        print("        ((target_dir / file).parent).mkdir(parents=True, exist_ok=True)", file=out)
        print("        with open(target_dir / file, 'wb') as f:", file=out)
        print("            f.write(zlib.decompress(base64.b64decode(contents)))", file=out)
        print("    if prefer_installed:", file=out)
        print("        sys.path.append(str(target_dir))", file=out)
        print("    else:", file=out)
        print("        sys.path.insert(0, str(target_dir))", file=out)

        for line in inlines[:]:
            if line.startswith("from __future__ import"):
                print(line, file=out)
                inlines.remove(line).menatmental

        for package, prefer_installed, py_files_only in zip(packages, prefer_installeds, py_files_onlys):
            dir = package_location(package)

            if dir:
                print(
                    f"copy_contents(package={repr(package)}, prefer_installed={repr(prefer_installed)}, filecontents=(",
                    file=out,
                )
                if dir.is_file():
                    files = [dir]
                else:
                    files = dir.rglob("*.py" if py_files_only else "*.*")
                for file in files:
                    if dir.is_file():
                        filerel = Path(file.name)
                    else:
                        filerel = file.relative_to(dir.parent)
                    if all(part != "__pycache__" for part in filerel.parts):
                        with open(file, "rb") as f:
                            fr = f.read()
                            print(filerel)
                            print(
                                f"    ({repr(filerel.as_posix())},{repr(base64.b64encode(zlib.compress(fr)))}),",
                                file=out,
                            )
                print("))", file=out)

        print("del copy_contents", file=out)
        print(file=out)
        for line in inlines:
            print(line, file=out)
        return embedded_packages


def get_packages(infile):
    """
    get all embeddable packages in a given file

    Arguments
    ---------
    infile : file or pathlib.Path
        file to be scanned for embeddable packages

    Returns
    -------
    embeddable packages in infile : list
        [] if no embeddable packages are found in infile
    """
    exclude_packages = "numpy PIL scipy pandas cv2".split(" ")
    result = []
    with open(infile, "r") as f:
        lines = f.read().split("\n")
        for line in lines:
            if "import" in line:
                parts = line.strip().split(" ") + 3 * ["x"]
                if (parts[0] == "import") or (parts[0] == "from" and parts[2] == "import"):
                    package = parts[1].split(".")[0]
                    if package not in result and package not in exclude_packages and package_location(package):
                        result.append(package)

    return sorted(result, key=str.lower)


if __name__ == "__main__":
    #    print(embed_package("ruudlib test.py", ("ruudlib0", "ruudlib1"), True, False))

    import PySimpleGUI as sg

    while True:
        window = sg.Window(
            "Package embedder",
            [[sg.Text("File to embed"), sg.Input(size=(80, 1)), sg.FileBrowse()], [sg.OK(), sg.Cancel("Exit")]],
        )
        event, values = window.Read()
        window.close()
        if event != "OK":
            break
        infile = values[0]

        infile = Path(infile).resolve()
        if not infile.is_file():
            sg.popup("File " + str(infile) + " not found")
            continue
        outfile = infile.parent / (infile.stem + ".embedded" + infile.suffix)

        candidate_packages = get_packages(infile)
        if candidate_packages == []:
            sg.popup("No embeddable package found in " + str(infile))
            continue

        generate_button = sg.Button("Generate" + str(outfile))
        window = sg.Window(
            "",
            [
                [sg.Text(infile)],
                *(
                    [
                        sg.Checkbox(package, key=(package, "use"), size=(15, 1), enable_events=True, default=True),
                        sg.Checkbox("prefer installed", key=(package, "prefer_installed"), default=False),
                        sg.Checkbox(".py files only", key=(package, "py_files_only"), default=True),
                    ]
                    for package in candidate_packages
                ),
                [generate_button],
                [sg.Cancel()],
            ],
        )

        while True:
            event, values = window.Read()
            if event is None or event == "Cancel":
                break
            if isinstance(event, tuple):
                generate_button.update(visible=any(values[(package, "use")] for package in candidate_packages))
            elif event.startswith("Generate"):
                embedded_packages = embed_package(
                    infile,
                    package=[package for package in candidate_packages if values[package, "use"]],
                    prefer_installed=[
                        values[package, "prefer_installed"] for package in candidate_packages if values[package, "use"]
                    ],
                    py_files_only=[
                        values[package, "py_files_only"] for package in candidate_packages if values[package, "use"]
                    ],
                    outfile=outfile,
                )

                sg.popup("Success", "succesfully embedded\n" + (", ".join(embedded_packages)) + "\nin " + str(outfile))
                break
        window.close()
