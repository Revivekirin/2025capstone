import argostranslate.package, argostranslate.translate

def install_argos_ko_en():
    from_code = "ko"
    to_code = "en"
    available_packages = argostranslate.package.get_available_packages()
    package_to_install = list(filter(
        lambda x: x.from_code == from_code and x.to_code == to_code, available_packages))[0]

    argostranslate.package.install_from_path(package_to_install.download())

if __name__ == "__main__":
    install_argos_ko_en()
