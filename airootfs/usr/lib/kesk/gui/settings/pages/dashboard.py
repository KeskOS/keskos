from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGridLayout, QLabel, QPushButton, QWidget

from .base import BasePage
from ..widgets import CardFrame, StatusLabel


class DashboardPage(BasePage):
    page_key = "dashboard"

    def __init__(self, controller) -> None:
        super().__init__(controller, "Dashboard", "LIGHTWEIGHT STATUS SNAPSHOT")
        self._loaded = False

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(14)

        self.system_fields = {}
        self.update_fields = {}
        self.health_fields = {}
        self.identity_fields = {}

        system_card = CardFrame("System State", "CURRENT BUILD, KERNEL, UPTIME, AND SESSION")
        system_form = QFormLayout()
        for key, label in (
            ("version", "KeskOS"),
            ("kernel", "Kernel"),
            ("uptime", "Uptime"),
            ("session", "Desktop"),
        ):
            value = QLabel("loading...")
            value.setWordWrap(True)
            self.system_fields[key] = value
            system_form.addRow(label, value)
        system_card.layout.addLayout(system_form)
        grid.addWidget(system_card, 0, 0)

        updates_card = CardFrame("Updates", "DETECTED UPDATE SOURCES")
        for key, label in (
            ("official", "Official repos"),
            ("aur", "AUR"),
            ("flatpak", "Flatpak"),
            ("firmware", "Firmware"),
        ):
            status = StatusLabel(f"{label.lower()}: waiting", "work")
            self.update_fields[key] = status
            updates_card.layout.addWidget(status)
        open_updates = QPushButton("OPEN UPDATER")
        open_updates.clicked.connect(lambda: self.controller.show_page("updates"))
        updates_card.layout.addWidget(open_updates)
        grid.addWidget(updates_card, 0, 1)

        health_card = CardFrame("System Health", "READ-ONLY INTEGRITY SIGNALS")
        for key, text in (
            ("doctor", "last doctor result: waiting"),
            ("failed_services", "failed services: waiting"),
            ("disk", "disk pressure: waiting"),
        ):
            status = StatusLabel(text, "work")
            self.health_fields[key] = status
            health_card.layout.addWidget(status)
        run_doctor = QPushButton("RUN DOCTOR")
        run_doctor.clicked.connect(lambda: self.controller.show_page("system_health"))
        health_card.layout.addWidget(run_doctor)
        grid.addWidget(health_card, 1, 0)

        identity_card = CardFrame("Desktop Identity", "THEME, LOGIN, AND BOOT STATUS")
        for key, text in (
            ("plasma", "Plasma theme: waiting"),
            ("sddm", "SDDM theme: waiting"),
            ("plymouth", "Plymouth theme: waiting"),
        ):
            status = StatusLabel(text, "work")
            self.identity_fields[key] = status
            identity_card.layout.addWidget(status)
        open_repair = QPushButton("OPEN REPAIR")
        open_repair.clicked.connect(lambda: self.controller.show_page("repair"))
        identity_card.layout.addWidget(open_repair)
        grid.addWidget(identity_card, 1, 1)

        self.root_layout.insertWidget(2, container)

    def on_activated(self) -> None:
        if not self._loaded or self.controller.prefs.dashboard_checks:
            self.refresh()

    def refresh(self) -> None:
        self._loaded = True
        self.controller.log("dashboard_refresh")
        about_rows = dict(self.controller.about_rows())
        self.system_fields["version"].setText(about_rows.get("KeskOS version", "unknown"))
        self.system_fields["kernel"].setText(about_rows.get("Kernel", "unknown"))
        self.system_fields["uptime"].setText(about_rows.get("Uptime", "unknown"))
        self.system_fields["session"].setText(about_rows.get("Current desktop", about_rows.get("Desktop session", "unknown")))

        self.controller.run_json_tool("upgrade", ["--check", "--json"], self._apply_updates, self.controller.surface_error)
        self.controller.run_json_tool("doctor", ["--json"], self._apply_doctor, self.controller.surface_error)
        self.controller.run_json_tool("repair", ["--status", "--json"], self._apply_repair, self.controller.surface_error)

    def _apply_updates(self, payload: dict) -> None:
        sources = payload.get("sources", {})
        for key, label in (
            ("official", "official repos"),
            ("aur", "AUR"),
            ("flatpak", "Flatpak"),
            ("firmware", "firmware"),
        ):
            source = sources.get(key, {})
            if not source.get("available"):
                self.update_fields[key].set_status(source.get("unavailable_reason", f"{label} unavailable"), "skip")
                continue
            if source.get("blocked_reason"):
                self.update_fields[key].set_status(source["blocked_reason"], "warn")
                continue
            kind = "warn" if source.get("error") else "ok"
            message = source.get("error") or f"{label}: {source.get('count', 0)} update(s)"
            self.update_fields[key].set_status(message, kind)

    def _apply_doctor(self, payload: dict) -> None:
        serious = bool(payload.get("serious_issue"))
        self.health_fields["doctor"].set_status(
            "last doctor result: warnings detected" if serious else "last doctor result: clean",
            "warn" if serious else "ok",
        )
        failed = len(payload.get("failed_services", []))
        self.health_fields["failed_services"].set_status(
            f"failed services: {failed}",
            "warn" if failed else "ok",
        )
        disks = payload.get("disks", [])
        disk_warning = any(disk.get("kind") == "warn" or disk.get("serious") for disk in disks)
        self.health_fields["disk"].set_status(
            "disk pressure: warning" if disk_warning else "disk pressure: normal",
            "warn" if disk_warning else "ok",
        )

    def _apply_repair(self, payload: dict) -> None:
        active = payload.get("theme_status", {}).get("active", {})
        self.identity_fields["plasma"].set_status(
            f"Plasma theme: {active.get('plasma_theme', 'unknown')}",
            "ok" if active.get("plasma_theme") not in {None, 'unavailable'} else "skip",
        )
        self.identity_fields["sddm"].set_status(
            f"SDDM theme: {active.get('sddm_theme', 'unknown')}",
            "ok" if active.get("sddm_theme") not in {None, 'unavailable'} else "warn",
        )
        self.identity_fields["plymouth"].set_status(
            f"Plymouth theme: {active.get('plymouth_theme', 'unknown')}",
            "ok" if active.get("plymouth_theme") not in {None, 'unavailable'} else "skip",
        )
