from PySide6.QtCore import QSettings


def app_settings():
    return QSettings("MyHR", "MyHR")


def company_name(default="MyHR"):
    return app_settings().value("company/name", default)


def company_subtitle(default="Employee Management"):
    return app_settings().value("company/subtitle", default)
