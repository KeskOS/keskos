mod backend;
mod logger;

use backend::{
    ActionResponse, BrowserSnapshot, CatalogStatus, InstallReportRuntime, InstallSource, NetworkSnapshot,
    ThemeSnapshot,
};
use clap::Parser;
use gtk::prelude::*;
use gtk::{
    Align, Application, ApplicationWindow, Box as GtkBox, Button, CheckButton, ComboBoxText, CssProvider,
    Entry,
    Frame, Grid, Label, MessageDialog, MessageType, Orientation, PolicyType, ReliefStyle, ResponseType,
    ScrolledWindow, Separator, Stack, StyleContext, StackTransitionType,
};
use logger::Logger;

use std::cell::RefCell;
use std::collections::HashMap;
use std::process::{Child, Command};
use std::rc::Rc;
use std::time::Duration;

const APP_ID: &str = "org.keskos.welcome";
const WINDOW_WIDTH: i32 = 1240;
const WINDOW_HEIGHT: i32 = 740;
const SIDEBAR_WIDTH: i32 = 280;
const TITLEBAR_HEIGHT: i32 = 42;
const HERO_HEIGHT: i32 = 108;
const NAV_HEIGHT: i32 = 64;
const STEP_ROW_HEIGHT: i32 = 46;
const CSS: &str = r#"
* {
  background-image: none;
  box-shadow: none;
  text-shadow: none;
  outline-color: transparent;
  -gtk-icon-shadow: none;
  -gtk-icon-transform: none;
  transition: none;
}

window,
box,
grid,
label,
checkbutton,
button,
entry,
combobox,
textview,
frame,
viewport,
scrolledwindow,
separator {
  background-color: #030303;
  color: #b8afa6;
  font-family: "JetBrains Mono", "JetBrainsMono Nerd Font", "Iosevka", "Noto Sans Mono", monospace;
}

window {
  background-color: #030303;
}

label {
  background-color: transparent;
  color: #b8afa6;
}

viewport,
scrolledwindow,
scrolledwindow viewport,
scrolledwindow overshoot,
scrolledwindow undershoot {
  background-color: #030303;
  border: none;
}

stack,
box.page-shell,
box.page-content,
viewport.page-viewport,
scrolledwindow.page-scroll {
  background-color: #030303;
  border: none;
}

frame.shell,
frame.shell > border {
  background-color: #030303;
  border: 1px solid rgba(206, 106, 53, 0.55);
}

frame.titlebar,
frame.titlebar > border {
  background-color: #030303;
  border: none;
  border-bottom: 1px solid rgba(206, 106, 53, 0.45);
}

frame.rail,
frame.rail > border {
  background-color: #050505;
  border: none;
  border-right: 1px solid rgba(206, 106, 53, 0.42);
}

frame.hero,
frame.hero > border {
  background-color: #050505;
  border: 1px solid rgba(206, 106, 53, 0.45);
}

frame.content-shell,
frame.content-shell > border {
  background-color: #030303;
  border: none;
}

frame.nav,
frame.nav > border {
  background-color: #050505;
  border: none;
  border-top: 1px solid rgba(206, 106, 53, 0.45);
}

frame.section,
frame.section > border {
  background-color: #050505;
  border: 1px solid rgba(206, 106, 53, 0.38);
  padding: 0;
}

label.strip-title {
  color: #ce6a35;
  font-family: "VT323", "JetBrains Mono", "Iosevka", monospace;
  font-size: 28px;
  font-weight: 700;
}

label.hero-title {
  color: #e2d8cf;
  font-family: "VT323", "JetBrains Mono", "Iosevka", monospace;
  font-size: 30px;
  font-weight: 700;
}

label.hero-subtitle {
  color: #8f8a84;
  font-size: 14px;
}

label.rail-brand-title {
  color: #ce6a35;
  font-family: "VT323", "JetBrains Mono", "Iosevka", monospace;
  font-size: 26px;
  font-weight: 700;
}

label.rail-brand-meta {
  color: #8f8a84;
  font-size: 13px;
}

label.panel-title {
  color: #ce6a35;
  font-family: "VT323", "JetBrains Mono", "Iosevka", monospace;
  font-size: 22px;
  font-weight: 700;
}

label.section-title {
  color: #e2d8cf;
  font-weight: 700;
  font-size: 14px;
}

label.dim,
label.muted {
  color: #8f8a84;
}

label.badge {
  color: #ce6a35;
  font-weight: 700;
}

button,
button label {
  background-color: #050505;
  color: #b8afa6;
}

button {
  border: 1px solid rgba(206, 106, 53, 0.45);
  border-radius: 0;
  box-shadow: none;
  padding: 6px 14px;
}

button:hover,
button:hover label {
  color: #e2d8cf;
}

button:hover {
  background-color: #2a160f;
  border-color: #ce6a35;
}

button:active,
button:checked {
  background-color: #341b11;
  border-color: #ce6a35;
}

button:focus {
  background-color: #050505;
  border-color: #ce6a35;
  outline: none;
}

button:disabled {
  color: #4f4a45;
  background-color: #030303;
  border-color: rgba(143, 138, 132, 0.25);
}

button.primary,
button.primary label {
  color: #e2d8cf;
}

button.primary {
  background-color: #2a160f;
  border-color: #ce6a35;
}

button.primary:hover {
  background-color: #341b11;
}

button.primary:focus {
  background-color: #2a160f;
}

button.step {
  background-color: #050505;
  color: #8f8a84;
  border-top: 1px solid transparent;
  border-right: 1px solid transparent;
  border-bottom: 1px solid rgba(206, 106, 53, 0.18);
  border-left: 3px solid transparent;
  border-radius: 0;
  min-height: 40px;
  padding: 10px 14px;
}

button.step label {
  color: #8f8a84;
}

button.step:hover {
  background-color: rgba(206, 106, 53, 0.08);
  border-top-color: rgba(206, 106, 53, 0.35);
  border-right-color: rgba(206, 106, 53, 0.35);
  border-bottom-color: rgba(206, 106, 53, 0.35);
  border-left-color: rgba(206, 106, 53, 0.35);
}

button.step:hover label {
  color: #b8afa6;
}

button.step-active {
  background-color: #2a160f;
  color: #e2d8cf;
  border-left: 3px solid #ce6a35;
  border-top: 1px solid #ce6a35;
  border-right: 1px solid #ce6a35;
  border-bottom: 1px solid #ce6a35;
}

button.step-active label {
  color: #e2d8cf;
}

button.step-done {
  color: #b8afa6;
}

button.step-done label {
  color: #b8afa6;
}

entry,
entry selection,
combobox,
combobox box,
combobox button,
combobox button box,
combobox button label,
combobox cellview,
combobox arrow,
combobox menu,
combobox menuitem,
entry {
  background-color: #050505;
  color: #b8afa6;
  border-radius: 0;
  border: 1px solid rgba(206, 106, 53, 0.45);
  padding: 4px 10px;
}

entry selection {
  background-color: #2a160f;
  color: #e2d8cf;
}

combobox button:hover,
combobox button:active,
combobox button:focus,
combobox button:checked,
combobox:focus,
entry:focus {
  border-color: #ce6a35;
}

combobox button:hover,
combobox button:active,
combobox button:checked {
  background-color: #2a160f;
  color: #e2d8cf;
}

combobox button:focus,
combobox:focus,
entry:focus {
  background-color: #050505;
  color: #b8afa6;
}

combobox arrow {
  color: #ce6a35;
}

entry:disabled,
combobox:disabled,
combobox button:disabled,
combobox box:disabled {
  background-color: #030303;
  color: #4f4a45;
  border-color: rgba(143, 138, 132, 0.25);
}

menu,
menuitem,
popover,
popover.background,
modelbutton {
  background-color: #050505;
  color: #b8afa6;
  border-radius: 0;
}

menuitem:hover,
menuitem:selected,
modelbutton:hover,
modelbutton:checked,
modelbutton:selected {
  background-color: #2a160f;
  color: #e2d8cf;
}

checkbutton,
checkbutton label {
  background-color: transparent;
  color: #b8afa6;
}

checkbutton:hover label,
checkbutton:focus label {
  color: #e2d8cf;
}

checkbutton check {
  min-width: 16px;
  min-height: 16px;
  background-color: #030303;
  border-radius: 0;
  border: 1px solid rgba(206, 106, 53, 0.55);
  background-image: none;
  box-shadow: none;
  -gtk-icon-source: none;
}

checkbutton check:checked {
  background-color: #2a160f;
  color: #e2d8cf;
  border-color: #ce6a35;
  -gtk-icon-source: -gtk-icontheme("object-select-symbolic");
}

checkbutton check:hover {
  background-color: rgba(206, 106, 53, 0.08);
  border-color: #ce6a35;
}

checkbutton:disabled,
checkbutton:disabled label,
checkbutton:disabled check {
  color: #4f4a45;
  background-color: #030303;
  border-color: rgba(143, 138, 132, 0.25);
}

scrollbar,
scrollbar trough,
scrollbar slider {
  background-color: #050505;
  border-radius: 0;
}

scrollbar slider {
  background-color: rgba(206, 106, 53, 0.45);
  border: 1px solid rgba(206, 106, 53, 0.45);
}

scrollbar slider:hover {
  background-color: #ce6a35;
}

separator {
  background-color: rgba(206, 106, 53, 0.20);
  min-height: 1px;
}
"#;

#[derive(Parser, Debug)]
#[command(author, version, about = "KeskOS first-boot welcome app", long_about = None)]
struct Cli {
    #[arg(long)]
    first_run: bool,
    #[arg(long)]
    rerun: bool,
}

#[derive(Clone, Copy)]
struct PageSpec {
    key: &'static str,
    sidebar: &'static str,
    title: &'static str,
    description: &'static str,
}

const PAGES: [PageSpec; 8] = [
    PageSpec {
        key: "welcome",
        sidebar: "01 WELCOME",
        title: "Welcome to KeskOS",
        description: "The machine greets you. Let’s finish your first boot setup.",
    },
    PageSpec {
        key: "network",
        sidebar: "02 NETWORK / UPLINK",
        title: "Network / Uplink",
        description: "Check internet access or connect to Wi-Fi before installing browsers and optional packages.",
    },
    PageSpec {
        key: "browser",
        sidebar: "03 BROWSER",
        title: "Browser",
        description: "Choose a default browser and apply the current KeskOS browser setup.",
    },
    PageSpec {
        key: "topbar",
        sidebar: "04 TOP BAR WIDGETS",
        title: "Top Bar Widgets",
        description: "Control the current KeskOS top bar widget layer.",
    },
    PageSpec {
        key: "apps",
        sidebar: "05 OPTIONAL APPS",
        title: "Optional Apps",
        description: "Install a curated set of applications with pacman first and yay as a fallback.",
    },
    PageSpec {
        key: "theme",
        sidebar: "06 THEME CHECK",
        title: "Theme Check",
        description: "Repair or reapply the current KeskOS desktop identity without exposing fake theme options.",
    },
    PageSpec {
        key: "links",
        sidebar: "07 SYSTEM LINKS",
        title: "System Links",
        description: "Open the official KeskOS links and launch the current system tools.",
    },
    PageSpec {
        key: "finish",
        sidebar: "08 FINISH",
        title: "Finish",
        description: "Review what happened during setup and complete the first-boot flow.",
    },
];

struct WizardState {
    current_page: usize,
    internet_available: bool,
    network: NetworkSnapshot,
    selected_browser: String,
    browser_install_result: String,
    browser_default_result: String,
    browser_theme_result: String,
    topbar_result: String,
    optional_apps_result: String,
    theme_result: String,
}

struct NetworkWidgets {
    support_badge: Label,
    uplink_status: Label,
    uplink_message: Label,
    backend_status: Label,
    active_connection: Label,
    wired_status: Label,
    wifi_status: Label,
    note: Label,
    ssid_combo: ComboBoxText,
    password_entry: Entry,
    show_password: CheckButton,
    scan_button: Button,
    connect_button: Button,
    recheck_button: Button,
}

struct BrowserWidgets {
    combo: ComboBoxText,
    status: Label,
    homepage_toggle: CheckButton,
    install_button: Button,
    default_button: Button,
    theme_button: Button,
    note: Label,
}

struct TopBarWidgets {
    backend_status: Label,
    info: Label,
    master_toggle: CheckButton,
    media_toggle: CheckButton,
    cpu_toggle: CheckButton,
    memory_toggle: CheckButton,
    network_toggle: CheckButton,
    apply_button: Button,
    reset_button: Button,
    restart_button: Button,
}

struct OptionalRow {
    id: String,
    check: CheckButton,
    status: Label,
}

struct OptionalWidgets {
    rows: Vec<OptionalRow>,
    info: Label,
    install_button: Button,
}

struct ThemeWidgets {
    theme_active: Label,
    kde_defaults: Label,
    launcher: Label,
    panels: Label,
    konsole: Label,
    dunst: Label,
    boot_note: Label,
    apply_kesk: Button,
    reset_kde: Button,
    reapply_launcher: Button,
    reapply_panels: Button,
    reapply_konsole: Button,
    reapply_dunst: Button,
}

struct FinishWidgets {
    summary: Label,
    report_basic: CheckButton,
    report_extra: CheckButton,
}

struct WelcomeApp {
    cli: Cli,
    logger: Logger,
    window: ApplicationWindow,
    stack: Stack,
    title_label: Label,
    description_label: Label,
    footer_label: Label,
    back_button: Button,
    skip_button: Button,
    continue_button: Button,
    sidebar_buttons: Vec<Button>,
    network: NetworkWidgets,
    browser: BrowserWidgets,
    topbar: TopBarWidgets,
    optional: OptionalWidgets,
    theme: ThemeWidgets,
    finish: FinishWidgets,
    state: RefCell<WizardState>,
}

impl WelcomeApp {
    fn new(application: &Application, cli: Cli) -> Rc<Self> {
        let logger = Logger::new(backend::log_path());
        logger.log(&format!(
            "app start mode={} first_run={} rerun={} marker={} legacy_marker={}",
            if cli.first_run { "first-run" } else if cli.rerun { "rerun" } else { "manual" },
            cli.first_run,
            cli.rerun,
            backend::marker_path().display(),
            backend::legacy_marker_path().display(),
        ));

        install_css(&logger);

        let window = ApplicationWindow::builder()
            .application(application)
            .title("Kesk Welcome")
            .default_width(WINDOW_WIDTH)
            .default_height(WINDOW_HEIGHT)
            .build();
        window.set_size_request(WINDOW_WIDTH, WINDOW_HEIGHT);

        let shell_frame = panel_frame("shell");
        window.add(&shell_frame);

        let root = GtkBox::new(Orientation::Vertical, 0);
        shell_frame.add(&root);

        let strip_frame = panel_frame("titlebar");
        strip_frame.set_size_request(-1, TITLEBAR_HEIGHT);
        let strip_box = GtkBox::new(Orientation::Horizontal, 0);
        strip_box.set_margin_top(6);
        strip_box.set_margin_bottom(6);
        strip_box.set_margin_start(10);
        strip_box.set_margin_end(10);
        strip_box.add(&label("[ KESKOS DEPLOYMENT CONSOLE ]", "strip-title"));
        strip_frame.add(&strip_box);
        root.pack_start(&strip_frame, false, false, 0);

        let body = GtkBox::new(Orientation::Horizontal, 0);
        body.set_vexpand(true);
        root.pack_start(&body, true, true, 0);

        let sidebar_frame = panel_frame("rail");
        sidebar_frame.set_size_request(SIDEBAR_WIDTH, -1);
        let sidebar_box = GtkBox::new(Orientation::Vertical, 0);

        let rail_brand = GtkBox::new(Orientation::Vertical, 4);
        rail_brand.set_margin_top(14);
        rail_brand.set_margin_bottom(12);
        rail_brand.set_margin_start(12);
        rail_brand.set_margin_end(12);
        rail_brand.add(&label("K E S K   O S", "rail-brand-title"));
        rail_brand.add(&label("FIRST BOOT SEQUENCE", "rail-brand-meta"));
        rail_brand.add(&label("S.P.L.I.T. EDITION", "rail-brand-meta"));
        sidebar_box.pack_start(&rail_brand, false, false, 0);
        sidebar_box.pack_start(&panel_separator(), false, false, 0);

        let mut sidebar_buttons = Vec::with_capacity(PAGES.len());
        for spec in PAGES {
            let button = Button::with_label(spec.sidebar);
            button.set_halign(Align::Fill);
            button.set_hexpand(true);
            button.set_size_request(-1, STEP_ROW_HEIGHT);
            prepare_button(&button);
            align_button_label_start(&button);
            add_class(&button, "step");
            sidebar_box.pack_start(&button, false, false, 0);
            sidebar_buttons.push(button);
        }
        sidebar_frame.add(&sidebar_box);
        body.pack_start(&sidebar_frame, false, false, 0);

        let content_column = GtkBox::new(Orientation::Vertical, 0);
        body.pack_start(&content_column, true, true, 0);

        let header_frame = panel_frame("hero");
        header_frame.set_size_request(-1, HERO_HEIGHT);
        header_frame.set_margin_top(10);
        header_frame.set_margin_bottom(0);
        header_frame.set_margin_start(10);
        header_frame.set_margin_end(10);
        let header_box = GtkBox::new(Orientation::Vertical, 6);
        header_box.set_margin_top(14);
        header_box.set_margin_bottom(14);
        header_box.set_margin_start(14);
        header_box.set_margin_end(14);
        let title_label = label(&hero_title_for_page(&PAGES[0]), "hero-title");
        let description_label = label(PAGES[0].description, "hero-subtitle");
        description_label.set_line_wrap(true);
        header_box.add(&title_label);
        header_box.add(&description_label);
        header_frame.add(&header_box);
        content_column.pack_start(&header_frame, false, false, 0);

        let content_frame = panel_frame("content-shell");
        content_frame.set_hexpand(true);
        content_frame.set_vexpand(true);
        content_frame.set_margin_top(10);
        content_frame.set_margin_bottom(0);
        content_frame.set_margin_start(10);
        content_frame.set_margin_end(10);
        content_column.pack_start(&content_frame, true, true, 0);
        let content_box = GtkBox::new(Orientation::Vertical, 0);
        content_frame.add(&content_box);

        let stack = Stack::new();
        stack.set_hexpand(true);
        stack.set_vexpand(true);
        stack.set_hhomogeneous(true);
        stack.set_vhomogeneous(true);
        stack.set_transition_type(StackTransitionType::None);
        stack.set_interpolate_size(false);
        content_box.pack_start(&stack, true, true, 0);

        let network = build_network_page(&stack);
        let browser = build_browser_page(&stack);
        let topbar = build_topbar_page(&stack);
        let optional = build_optional_apps_page(&stack);
        let theme = build_theme_page(&stack);
        let finish = build_finish_page(&stack);
        build_welcome_page(&stack, &cli);
        build_links_page(&stack);

        let footer_frame = panel_frame("nav");
        footer_frame.set_size_request(-1, NAV_HEIGHT);
        let footer_box = GtkBox::new(Orientation::Horizontal, 12);
        footer_box.set_margin_top(8);
        footer_box.set_margin_bottom(8);
        footer_box.set_margin_start(12);
        footer_box.set_margin_end(12);
        let footer_label = label("Waiting for first-boot choices.", "muted");
        footer_label.set_hexpand(true);
        footer_label.set_halign(Align::Start);
        let button_box = GtkBox::new(Orientation::Horizontal, 8);
        let back_button = Button::with_label("[ BACK ]");
        let skip_button = Button::with_label("[ SKIP ]");
        let continue_button = Button::with_label("[ CONTINUE ]");
        prepare_button(&back_button);
        prepare_button(&skip_button);
        prepare_button(&continue_button);
        apply_primary(&continue_button);
        button_box.pack_start(&back_button, false, false, 0);
        button_box.pack_start(&skip_button, false, false, 0);
        button_box.pack_start(&continue_button, false, false, 0);
        footer_box.pack_start(&footer_label, true, true, 0);
        footer_box.pack_end(&button_box, false, false, 0);
        footer_frame.add(&footer_box);
        root.pack_end(&footer_frame, false, false, 0);

        let network_snapshot = backend::network_snapshot();
        let state = WizardState {
            current_page: 0,
            internet_available: network_snapshot.uplink_online,
            network: network_snapshot,
            selected_browser: String::from("librewolf"),
            browser_install_result: String::from("skipped"),
            browser_default_result: String::from("skipped"),
            browser_theme_result: String::from("skipped"),
            topbar_result: String::from("skipped"),
            optional_apps_result: String::from("skipped"),
            theme_result: String::from("skipped"),
        };

        let app = Rc::new(Self {
            cli,
            logger,
            window,
            stack,
            title_label,
            description_label,
            footer_label,
            back_button,
            skip_button,
            continue_button,
            sidebar_buttons,
            network,
            browser,
            topbar,
            optional,
            theme,
            finish,
            state: RefCell::new(state),
        });

        app.connect_signals();
        app.refresh_all();
        app.go_to_page(0);
        app
    }

    fn connect_signals(self: &Rc<Self>) {
        for (index, button) in self.sidebar_buttons.iter().enumerate() {
            let app = Rc::clone(self);
            button.connect_clicked(move |_| app.go_to_page(index));
        }

        {
            let app = Rc::clone(self);
            self.back_button.connect_clicked(move |_| {
                let current = app.state.borrow().current_page;
                if current > 0 {
                    app.go_to_page(current - 1);
                }
            });
        }

        {
            let app = Rc::clone(self);
            self.skip_button.connect_clicked(move |_| {
                let current = app.state.borrow().current_page;
                if current + 1 < PAGES.len() {
                    app.go_to_page(current + 1);
                }
            });
        }

        {
            let app = Rc::clone(self);
            self.continue_button.connect_clicked(move |_| {
                let current = app.state.borrow().current_page;
                if current + 1 >= PAGES.len() {
                    app.finish_and_quit();
                } else {
                    app.go_to_page(current + 1);
                }
            });
        }

        {
            let app = Rc::clone(self);
            self.network
                .scan_button
                .connect_clicked(move |_| app.scan_networks());
        }

        {
            let app = Rc::clone(self);
            self.network
                .recheck_button
                .connect_clicked(move |_| app.recheck_uplink());
        }

        {
            let app = Rc::clone(self);
            self.network
                .connect_button
                .connect_clicked(move |_| app.connect_selected_wifi());
        }

        {
            let app = Rc::clone(self);
            self.network
                .show_password
                .connect_toggled(move |toggle| app.network.password_entry.set_visibility(toggle.is_active()));
        }

        {
            let app = Rc::clone(self);
            self.network
                .ssid_combo
                .connect_changed(move |_| app.refresh_network_selection_note());
        }

        {
            let app = Rc::clone(self);
            self.finish.report_basic.connect_toggled(move |toggle| {
                let active = toggle.is_active();
                app.finish.report_extra.set_sensitive(active);
                if !active && app.finish.report_extra.is_active() {
                    app.finish.report_extra.set_active(false);
                }
                app.update_finish_summary();
            });
        }

        {
            let app = Rc::clone(self);
            self.finish.report_extra.connect_toggled(move |_| app.update_finish_summary());
        }

        {
            let app = Rc::clone(self);
            self.browser.combo.connect_changed(move |combo| {
                if let Some(active) = combo.active_id() {
                    app.state.borrow_mut().selected_browser = active.to_string();
                    app.refresh_browser_status();
                }
            });
        }

        {
            let app = Rc::clone(self);
            self.browser.install_button.connect_clicked(move |_| app.install_selected_browser());
        }

        {
            let app = Rc::clone(self);
            self.browser.default_button.connect_clicked(move |_| app.set_selected_browser_default());
        }

        {
            let app = Rc::clone(self);
            self.browser.theme_button.connect_clicked(move |_| app.apply_selected_browser_theme());
        }

        {
            let app = Rc::clone(self);
            self.topbar.reset_button.connect_clicked(move |_| app.reapply_topbar_defaults());
        }

        {
            let app = Rc::clone(self);
            self.topbar.restart_button.connect_clicked(move |_| app.restart_topbar_widgets());
        }

        {
            let app = Rc::clone(self);
            self.optional.install_button.connect_clicked(move |_| app.install_optional_apps());
        }

        {
            let app = Rc::clone(self);
            self.theme.apply_kesk.connect_clicked(move |_| {
                app.run_sync_action(
                    "Reapply KeskOS Theme",
                    &backend::theme_apply_command_path(),
                    &[],
                    "Applied the current KeskOS theme stack.",
                    |this| {
                        this.state.borrow_mut().theme_result = String::from("reapplied KeskOS theme");
                        this.refresh_theme_page();
                    },
                );
            });
        }

        {
            let app = Rc::clone(self);
            self.theme.reset_kde.connect_clicked(move |_| {
                app.run_sync_action(
                    "Reset to KDE Defaults",
                    &backend::kde_defaults_command_path(),
                    &[],
                    "Restored KDE defaults where supported.",
                    |this| {
                        this.state.borrow_mut().theme_result = String::from("restored KDE defaults");
                        this.refresh_theme_page();
                    },
                );
            });
        }

        {
            let app = Rc::clone(self);
            self.theme.reapply_launcher.connect_clicked(move |_| app.reapply_launcher());
        }

        {
            let app = Rc::clone(self);
            self.theme.reapply_panels.connect_clicked(move |_| app.reapply_panels());
        }

        {
            let app = Rc::clone(self);
            self.theme.reapply_konsole.connect_clicked(move |_| app.reapply_konsole());
        }

        let link_buttons = self
            .stack
            .child_by_name("links")
            .and_then(|widget| widget.downcast::<ScrolledWindow>().ok())
            .and_then(|scroll| scroll.child())
            .and_then(|viewport| viewport.downcast::<gtk::Viewport>().ok())
            .and_then(|viewport| viewport.child())
            .and_then(|child| child.downcast::<GtkBox>().ok())
            .expect("links page exists");

        for child in link_buttons.children() {
            if let Ok(button) = child.clone().downcast::<Button>() {
                if let Some(name) = button.widget_name().as_str().strip_prefix("link-") {
                    let app = Rc::clone(self);
                    let target = name.to_string();
                    button.connect_clicked(move |_| app.handle_link_button(&target));
                } else if let Some(name) = button.widget_name().as_str().strip_prefix("tool-") {
                    let app = Rc::clone(self);
                    let target = name.to_string();
                    button.connect_clicked(move |_| app.handle_tool_button(&target));
                }
            }
        }
    }

    fn refresh_all(&self) {
        self.refresh_network_page("startup");
        self.refresh_topbar_page();
        self.refresh_theme_page();
        self.update_finish_summary();
    }

    fn go_to_page(&self, index: usize) {
        let clamped = index.min(PAGES.len() - 1);
        self.state.borrow_mut().current_page = clamped;
        self.stack.set_visible_child_name(PAGES[clamped].key);
        self.title_label.set_text(&hero_title_for_page(&PAGES[clamped]));
        self.description_label.set_text(PAGES[clamped].description);
        self.update_sidebar();
        self.update_nav_buttons();
        if PAGES[clamped].key == "network" {
            self.logger.log("network page opened");
            self.refresh_network_page("page-open");
        } else if PAGES[clamped].key == "theme" {
            self.refresh_theme_page();
        } else if PAGES[clamped].key == "apps" {
            self.refresh_optional_page();
        } else if PAGES[clamped].key == "browser" {
            self.refresh_browser_status();
        } else if PAGES[clamped].key == "finish" {
            self.update_finish_summary();
        }
    }

    fn update_sidebar(&self) {
        let current = self.state.borrow().current_page;
        for (index, button) in self.sidebar_buttons.iter().enumerate() {
            let context = button.style_context();
            context.remove_class("step-active");
            context.remove_class("step-done");
            if index == current {
                context.add_class("step-active");
            } else if index < current {
                context.add_class("step-done");
            }
        }
    }

    fn update_nav_buttons(&self) {
        let current = self.state.borrow().current_page;
        self.back_button.set_sensitive(current > 0);
        self.skip_button.set_visible(current > 0 && current + 1 < PAGES.len());
        if current + 1 >= PAGES.len() {
            self.continue_button.set_label("[ FINISH ]");
        } else {
            self.continue_button.set_label("[ CONTINUE ]");
        }
    }

    fn footer(&self, message: &str) {
        self.footer_label.set_text(message);
    }

    fn refresh_network_page(&self, reason: &str) {
        let snapshot = backend::network_snapshot();
        self.logger.log(&format!(
            "network snapshot reason={} nmcli_available={} ping_available={} wired_active={} wifi_device_detected={} active_connection={} connection_type={} online={} checked={} ssid_count={} checked_at={}",
            reason,
            yes_no(snapshot.nmcli_available),
            yes_no(snapshot.ping_available),
            yes_no(snapshot.wired_active),
            yes_no(snapshot.wifi_device_detected),
            snapshot.active_connection,
            snapshot.connection_type,
            yes_no(snapshot.uplink_online),
            yes_no(snapshot.uplink_checked),
            snapshot.wifi_networks.len(),
            snapshot.last_checked_timestamp.unwrap_or(0),
        ));
        {
            let mut state = self.state.borrow_mut();
            state.internet_available = snapshot.uplink_online;
            state.network = snapshot.clone();
        }
        self.apply_network_snapshot(&snapshot);
        self.refresh_browser_status();
        self.refresh_optional_page();
        self.update_finish_summary();
    }

    fn apply_network_snapshot(&self, snapshot: &NetworkSnapshot) {
        self.network
            .support_badge
            .set_text(&format!("Support badge: {}", snapshot.support_badge));
        self.network
            .uplink_status
            .set_text(&format!("Uplink status: {}", snapshot.status_label));
        self.network.uplink_message.set_text(&snapshot.status_message);
        self.network
            .backend_status
            .set_text(&format!("Backend status: {}", snapshot.backend_status));
        self.network
            .active_connection
            .set_text(&format!("Active connection: {}", snapshot.active_connection));
        self.network
            .wired_status
            .set_text(&format!("Wired connection: {}", snapshot.wired_status));
        self.network
            .wifi_status
            .set_text(&format!("Wi-Fi adapter: {}", snapshot.wifi_status));

        let previous = self
            .network
            .ssid_combo
            .active_id()
            .map(|value| value.to_string())
            .filter(|value| !value.is_empty());
        self.network.ssid_combo.remove_all();
        for network in &snapshot.wifi_networks {
            let title = format!("{} [{}% / {}]", network.ssid, network.signal, network.security);
            self.network.ssid_combo.append(Some(&network.ssid), &title);
        }
        if let Some(selected) = previous {
            self.network.ssid_combo.set_active_id(Some(&selected));
        } else if !snapshot.wifi_networks.is_empty() {
            self.network.ssid_combo.set_active(Some(0));
        }

        let nmcli_wifi_ready = snapshot.nmcli_available && snapshot.wifi_device_detected;
        self.network.scan_button.set_sensitive(nmcli_wifi_ready);
        self.network
            .recheck_button
            .set_sensitive(snapshot.nmcli_available || snapshot.ping_available);
        self.network
            .ssid_combo
            .set_sensitive(nmcli_wifi_ready && !snapshot.wifi_networks.is_empty());
        self.network
            .password_entry
            .set_sensitive(nmcli_wifi_ready && !snapshot.wifi_networks.is_empty());
        self.network
            .show_password
            .set_sensitive(nmcli_wifi_ready && !snapshot.wifi_networks.is_empty());
        self.network
            .connect_button
            .set_sensitive(nmcli_wifi_ready && self.selected_wifi_ssid().is_some());
        self.refresh_network_selection_note();
    }

    fn selected_wifi_ssid(&self) -> Option<String> {
        self.network
            .ssid_combo
            .active_id()
            .map(|value| value.to_string())
            .filter(|value| !value.is_empty())
    }

    fn selected_wifi_network(&self) -> Option<backend::WiFiNetwork> {
        let selected = self.selected_wifi_ssid()?;
        self.state
            .borrow()
            .network
            .wifi_networks
            .iter()
            .find(|network| network.ssid == selected)
            .cloned()
    }

    fn refresh_network_selection_note(&self) {
        let snapshot = self.state.borrow().network.clone();
        let note = if !snapshot.nmcli_available {
            "NetworkManager is unavailable. Network setup cannot be managed from Kesk Welcome."
        } else if !snapshot.wifi_device_detected {
            "No Wi-Fi adapter was detected. A wired connection may still be used."
        } else if let Some(network) = self.selected_wifi_network() {
            if network.security.eq_ignore_ascii_case("open") {
                "Selected network appears open. Password not required."
            } else {
                "Password is required for secured Wi-Fi networks. Passwords are never written to welcome.log."
            }
        } else if snapshot.wifi_networks.is_empty() {
            "No Wi-Fi networks are listed yet. Scan or rescan to refresh the list."
        } else {
            "Select an SSID and enter the password if the network is secured."
        };
        self.network.note.set_text(note);
        self.network
            .connect_button
            .set_sensitive(snapshot.nmcli_available && snapshot.wifi_device_detected && self.selected_wifi_ssid().is_some());
    }

    fn scan_networks(&self) {
        self.logger.log("network scan attempted");
        self.footer("Scanning Wi-Fi networks.");
        self.refresh_network_page("scan");
    }

    fn recheck_uplink(&self) {
        self.logger.log("uplink recheck requested");
        self.footer("Rechecking uplink status.");
        self.refresh_network_page("recheck");
    }

    fn connect_selected_wifi(&self) {
        let Some(selected) = self.selected_wifi_network() else {
            self.show_message(MessageType::Info, "Select a Wi-Fi network first.");
            return;
        };

        let password = self.network.password_entry.text().to_string();
        let password_required = !selected.security.eq_ignore_ascii_case("open");
        if password_required && password.trim().is_empty() {
            self.show_message(MessageType::Warning, "Enter the Wi-Fi password before connecting.");
            return;
        }

        self.logger.log(&format!(
            "wifi connect attempt ssid={} secured={}",
            selected.ssid,
            yes_no(password_required),
        ));
        let response = backend::connect_wifi(
            &selected.ssid,
            if password_required { Some(password.as_str()) } else { None },
        );
        self.network.password_entry.set_text("");
        self.network.show_password.set_active(false);
        self.network.password_entry.set_visibility(false);
        self.logger.log(&format!(
            "wifi connect result ssid={} ok={} message={}",
            selected.ssid,
            yes_no(response.ok),
            response.message,
        ));
        self.footer(&response.message);
        if response.ok {
            self.show_message(MessageType::Info, &response.message);
        } else {
            self.show_message(MessageType::Warning, &response.message);
        }
        self.refresh_network_page("connect");
    }

    fn selected_browser_key(&self) -> String {
        self.browser
            .combo
            .active_id()
            .map(|value| value.to_string())
            .unwrap_or_else(|| self.state.borrow().selected_browser.clone())
    }

    fn refresh_browser_status(&self) {
        let snapshots = backend::browser_snapshots();
        if self.browser.combo.active_id().is_none() {
            self.browser.combo.set_active_id(Some(&self.state.borrow().selected_browser));
        }

        let selected = self.selected_browser_key();
        let snapshot = snapshots
            .into_iter()
            .find(|entry| entry.key == selected)
            .unwrap_or(BrowserSnapshot {
                key: selected.clone(),
                label: String::from("Unknown"),
                installed: false,
                current_default: false,
                homepage_assets_available: false,
                source_label: String::from("unavailable"),
                package_name: String::new(),
            });
        let install_target = backend::browser_install_target(&snapshot.key);
        let status = format!(
            "Selected browser: {}\n\
Package source: {}\n\
Package: {}\n\
Installed: {}\n\
Default browser: {}\n\
Homepage assets: {}",
            snapshot.label,
            snapshot.source_label,
            if snapshot.package_name.is_empty() { String::from("unknown") } else { snapshot.package_name.clone() },
            yes_no(snapshot.installed),
            yes_no(snapshot.current_default),
            yes_no(snapshot.homepage_assets_available),
        );
        self.browser.status.set_text(&status);

        let no_internet = !self.state.borrow().internet_available;
        let install_enabled = !no_internet
            && matches!(install_target.source, InstallSource::Pacman | InstallSource::Aur | InstallSource::AurNeedsYay);
        self.browser.install_button.set_sensitive(install_enabled);
        self.browser.default_button.set_sensitive(snapshot.installed);
        self.browser.theme_button.set_sensitive(snapshot.installed && snapshot.homepage_assets_available);

        let note = if no_internet {
            "No uplink to the internet. Package installation is unavailable."
        } else if !snapshot.homepage_assets_available {
            "Homepage or browser theme assets are missing. The browser theme action is disabled."
        } else if install_target.source == InstallSource::AurNeedsYay {
            "Selected browser requires AUR access. yay is not installed yet."
        } else if install_target.source == InstallSource::Unavailable {
            "Selected browser package is unavailable in the current repositories."
        } else {
            "LibreWolf is the recommended default browser."
        };
        self.browser.note.set_text(note);
        self.update_finish_summary();
    }

    fn install_selected_browser(self: &Rc<Self>) {
        let key = self.selected_browser_key();
        let target = backend::browser_install_target(&key);
        let label = browser_label(&key);

        if !self.state.borrow().internet_available {
            self.show_message(MessageType::Warning, "No uplink to the internet. Package installation is unavailable.");
            return;
        }

        match target.source {
            InstallSource::Installed => {
                self.show_message(MessageType::Info, &format!("{label} is already installed."));
            },
            InstallSource::Pacman => {
                let preview = format!("pkexec pacman -S --needed {}", target.package_name);
                let script = preview.clone();
                let app = Rc::clone(self);
                self.launch_terminal_script(
                    &format!("Install {label}"),
                    &preview,
                    &script,
                    move |success| {
                        app.logger.log(&format!("browser install result browser={} success={success}", key));
                        app.state.borrow_mut().browser_install_result = if success {
                            format!("{label} install finished")
                        } else {
                            format!("{label} install failed")
                        };
                        app.refresh_browser_status();
                    },
                );
            },
            InstallSource::Aur => {
                let preview = format!("yay -S --needed {}", target.package_name);
                let script = preview.clone();
                let app = Rc::clone(self);
                self.launch_terminal_script(
                    &format!("Install {label}"),
                    &preview,
                    &script,
                    move |success| {
                        app.logger.log(&format!("browser install result browser={} success={success}", key));
                        app.state.borrow_mut().browser_install_result = if success {
                            format!("{label} install finished")
                        } else {
                            format!("{label} install failed")
                        };
                        app.refresh_browser_status();
                    },
                );
            },
            InstallSource::AurNeedsYay => {
                if self.confirm(
                    "Selected browser requires yay",
                    "This browser needs AUR access and yay is not installed.\n\nInstall yay now?",
                ) {
                    let app = Rc::clone(self);
                    let spec = backend::yay_install_command_spec();
                    self.launch_terminal_argv(
                        &spec.label,
                        &spec.preview,
                        spec.argv,
                        move |success| {
                            app.logger.log(&format!("yay install result success={success}"));
                            app.state.borrow_mut().browser_install_result = if success {
                                String::from("yay install finished")
                            } else {
                                String::from("yay install failed")
                            };
                            app.refresh_browser_status();
                            app.refresh_optional_page();
                        },
                    );
                }
            },
            InstallSource::Unavailable => {
                self.show_message(MessageType::Error, "Selected browser package is unavailable.");
            },
        }
    }

    fn set_selected_browser_default(&self) {
        let key = self.selected_browser_key();
        self.logger.log(&format!("set default browser browser={key}"));
        let response = backend::set_default_browser(&key);
        self.handle_response("Default browser", response, |this| {
            this.state.borrow_mut().browser_default_result = format!("default browser -> {}", browser_label(&key));
            this.refresh_browser_status();
        });
    }

    fn apply_selected_browser_theme(&self) {
        let key = self.selected_browser_key();
        let include_homepage = self.browser.homepage_toggle.is_active();
        self.logger.log(&format!("apply browser theme browser={} homepage={}", key, include_homepage));
        let response = backend::apply_browser_theme(&key, include_homepage);
        self.handle_response("Browser theme", response, |this| {
            this.state.borrow_mut().browser_theme_result = if include_homepage {
                format!("applied browser theme + homepage for {}", browser_label(&key))
            } else {
                format!("applied browser theme for {}", browser_label(&key))
            };
            this.refresh_browser_status();
        });
    }

    fn refresh_topbar_page(&self) {
        let snapshot = backend::topbar_snapshot();
        self.topbar.backend_status.set_text(if snapshot.backend_connected { "Limited" } else { "Limited (backend not connected)" });
        self.topbar.info.set_text(if snapshot.backend_connected {
            "The current top bar backend exists, but per-widget toggles are not fully connected yet."
        } else {
            "These controls require the current KeskOS top bar widget backend to be connected."
        });
        for toggle in [
            &self.topbar.master_toggle,
            &self.topbar.media_toggle,
            &self.topbar.cpu_toggle,
            &self.topbar.memory_toggle,
            &self.topbar.network_toggle,
        ] {
            toggle.set_sensitive(false);
            toggle.set_active(true);
        }
        self.topbar.apply_button.set_sensitive(false);
        self.topbar.reset_button.set_sensitive(snapshot.can_reset);
        self.topbar.restart_button.set_sensitive(snapshot.can_restart);
    }

    fn reapply_topbar_defaults(&self) {
        let Some(helper) = backend::configure_user_command_path() else {
            self.show_message(MessageType::Error, "keskos-configure-user was not found on this system.");
            return;
        };

        let mut args = Vec::new();
        if let Ok(user) = std::env::var("USER") {
            args.push(String::from("--user"));
            args.push(user);
        }
        args.push(String::from("--force"));
        self.logger.log("topbar reset requested");
        self.run_sync_action(
            "Top bar reset",
            &helper,
            &args,
            "Reapplied the current KeskOS top bar widget configuration.",
            |this| {
                this.state.borrow_mut().topbar_result = String::from("reapplied top bar defaults");
            },
        );
    }

    fn restart_topbar_widgets(&self) {
        let Some(helper) = backend::quickshell_wrapper_command_path() else {
            self.show_message(MessageType::Error, "keskos-shell was not found on this system.");
            return;
        };

        let _ = Command::new("pkill").args(["-x", "quickshell"]).output();
        self.logger.log("topbar restart requested");
        self.run_sync_action(
            "Top bar restart",
            &helper,
            &[],
            "Restarted the KeskOS top bar widgets.",
            |this| {
                this.state.borrow_mut().topbar_result = String::from("restarted top bar widgets");
            },
        );
    }

    fn refresh_optional_page(&self) {
        let statuses = backend::optional_app_statuses();
        let internet = self.state.borrow().internet_available;
        self.optional.info.set_text(if internet {
            "Package installs use pacman first and yay as a fallback when needed."
        } else {
            "No uplink to the internet. Package installation is unavailable."
        });

        let status_map: HashMap<String, CatalogStatus> = statuses.into_iter().map(|entry| (entry.id.clone(), entry)).collect();
        for row in &self.optional.rows {
            if let Some(status) = status_map.get(&row.id) {
                let text = if status.target.package_name.is_empty() {
                    status.target.source_label.clone()
                } else {
                    format!("{} / {}", status.target.source_label, status.target.package_name)
                };
                row.status.set_text(&text);
            }
        }
        self.optional.install_button.set_sensitive(internet);
    }

    fn install_optional_apps(self: &Rc<Self>) {
        if !self.state.borrow().internet_available {
            self.show_message(MessageType::Warning, "No uplink to the internet. Package installation is unavailable.");
            return;
        }

        let selected: Vec<String> = self
            .optional
            .rows
            .iter()
            .filter(|row| row.check.is_active())
            .map(|row| row.id.clone())
            .collect();

        if selected.is_empty() {
            self.show_message(MessageType::Info, "No optional apps were selected.");
            return;
        }

        let statuses: HashMap<String, CatalogStatus> = backend::optional_app_statuses()
            .into_iter()
            .map(|entry| (entry.id.clone(), entry))
            .collect();

        let mut pacman_packages = Vec::new();
        let mut aur_packages = Vec::new();
        let mut skipped = Vec::new();
        let mut needs_yay = false;

        for id in &selected {
            if let Some(status) = statuses.get(id) {
                match status.target.source {
                    InstallSource::Installed => skipped.push(format!("{} already installed", status.label)),
                    InstallSource::Pacman => pacman_packages.push(status.target.package_name.clone()),
                    InstallSource::Aur => aur_packages.push(status.target.package_name.clone()),
                    InstallSource::AurNeedsYay => needs_yay = true,
                    InstallSource::Unavailable => skipped.push(format!("{} unavailable", status.label)),
                }
            }
        }

        if needs_yay {
            if self.confirm(
                "Selected apps require yay",
                "One or more selected apps require AUR access and yay is not installed.\n\nInstall yay now?",
            ) {
                let spec = backend::yay_install_command_spec();
                let app = Rc::clone(self);
                self.launch_terminal_argv("Install yay", &spec.preview, spec.argv, move |success| {
                    app.logger.log(&format!("yay install result success={success}"));
                    app.state.borrow_mut().optional_apps_result = if success {
                        String::from("yay install finished")
                    } else {
                        String::from("yay install failed")
                    };
                    app.refresh_optional_page();
                });
            }
            return;
        }

        if pacman_packages.is_empty() && aur_packages.is_empty() {
            self.show_message(MessageType::Info, &format!("Nothing to install.\n\n{}", skipped.join("\n")));
            return;
        }

        let mut preview_lines = Vec::new();
        let mut script_lines = Vec::new();
        if !pacman_packages.is_empty() {
            let command = format!("pkexec pacman -S --needed {}", pacman_packages.join(" "));
            preview_lines.push(command.clone());
            script_lines.push(command);
        }
        if !aur_packages.is_empty() {
            let command = format!("yay -S --needed {}", aur_packages.join(" "));
            preview_lines.push(command.clone());
            script_lines.push(command);
        }

        let preview = preview_lines.join("\n");
        let script = script_lines.join("; ");
        let app = Rc::clone(self);
        self.launch_terminal_script("Install optional apps", &preview, &script, move |success| {
            app.logger.log(&format!("optional app install result success={success}"));
            let mut state = app.state.borrow_mut();
            state.optional_apps_result = if success {
                String::from("optional apps install finished")
            } else {
                String::from("optional apps install failed")
            };
            drop(state);
            app.refresh_optional_page();
        });
    }

    fn refresh_theme_page(&self) {
        let snapshot = backend::theme_snapshot();
        self.set_theme_snapshot(&snapshot);
        self.update_finish_summary();
    }

    fn set_theme_snapshot(&self, snapshot: &ThemeSnapshot) {
        self.theme.theme_active.set_text(&snapshot.kesk_theme_active);
        self.theme.kde_defaults.set_text(&snapshot.kde_defaults_active);
        self.theme.launcher.set_text(&snapshot.launcher_layout);
        self.theme.panels.set_text(&snapshot.panel_layout);
        self.theme.konsole.set_text(&snapshot.konsole_profile);
        self.theme.dunst.set_text(&snapshot.dunst_theme);
        self.theme.boot_note.set_text(&format!(
            "Boot Splash is under development. Plymouth integrated: {}. KeskOS Plymouth theme installed: {}.",
            yes_no(snapshot.plymouth_installed),
            yes_no(snapshot.plymouth_theme_installed),
        ));
        self.theme.apply_kesk.set_sensitive(snapshot.can_reapply_kesk);
        self.theme.reset_kde.set_sensitive(snapshot.can_reset_kde);
        self.theme.reapply_launcher.set_sensitive(snapshot.can_reapply_launcher);
        self.theme.reapply_panels.set_sensitive(snapshot.can_reapply_panels);
        self.theme.reapply_konsole.set_sensitive(snapshot.can_reapply_konsole);
        self.theme.reapply_dunst.set_sensitive(false);
    }

    fn reapply_launcher(&self) {
        let Some(helper) = backend::fix_launcher_command_path() else {
            self.show_message(MessageType::Error, "No launcher repair helper was found on this system.");
            return;
        };

        let args = if helper.ends_with("keskos-launcher-switch") {
            vec![String::from("keskos")]
        } else {
            Vec::new()
        };
        self.logger.log("launcher reapply requested");
        self.run_sync_action("Launcher repair", &helper, &args, "Reapplied the KeskOS launcher.", |this| {
            this.state.borrow_mut().theme_result = String::from("reapplied launcher");
            this.refresh_theme_page();
        });
    }

    fn reapply_panels(&self) {
        let Some(helper) = backend::reset_panel_command_path() else {
            self.show_message(MessageType::Error, "keskos-reset-panel was not found on this system.");
            return;
        };

        self.logger.log("panel reapply requested");
        self.run_sync_action("Panel reapply", &helper, &[], "Reapplied the current KDE panel layout.", |this| {
            this.state.borrow_mut().theme_result = String::from("reapplied panel layout");
            this.refresh_theme_page();
        });
    }

    fn reapply_konsole(&self) {
        let repair = backend::repair_command_path();
        self.logger.log("konsole reapply requested");
        self.run_sync_action(
            "Konsole profile",
            &repair,
            &[String::from("repair"), String::from("--konsole"), String::from("--yes")],
            "Reapplied the current Konsole profile.",
            |this| {
                this.state.borrow_mut().theme_result = String::from("reapplied konsole profile");
                this.refresh_theme_page();
            },
        );
    }

    fn handle_link_button(&self, target: &str) {
        let url = match target {
            "website" => "https://keskos.org",
            "docs" => "https://docs.keskos.org",
            "github" => "https://github.com/memegeko/keskos",
            "downloads" => "https://downloads.keskos.org",
            _ => return,
        };
        self.logger.log(&format!("open link url={url}"));
        let response = backend::open_url(url);
        if !response.ok {
            self.show_message(MessageType::Warning, &response.message);
        }
    }

    fn handle_tool_button(self: &Rc<Self>, target: &str) {
        match target {
            "settings" => {
                let command = backend::doctor_command_path();
                let _ = Command::new(command).arg("settings").spawn();
                self.footer("Opened Kesk Settings.");
            },
            "doctor" => {
                let command = format!("{} doctor", backend::doctor_command_path());
                self.launch_terminal_script("Run Kesk Doctor", &command, &command, |_| {});
            },
            "upgrade" => {
                if self.confirm("Run Kesk Upgrade", "Open `kesk upgrade` in Konsole?") {
                    let command = format!("{} upgrade", backend::doctor_command_path());
                    self.launch_terminal_script("Run Kesk Upgrade", &command, &command, |_| {});
                }
            },
            "repair" => {
                if self.confirm("Run Kesk Repair", "Open `kesk repair` in Konsole?") {
                    let command = format!("{} repair", backend::doctor_command_path());
                    self.launch_terminal_script("Run Kesk Repair", &command, &command, |_| {});
                }
            },
            _ => {},
        }
    }

    fn update_finish_summary(&self) {
        let state = self.state.borrow();
        let report_mode = if self.finish.report_basic.is_active() {
            if self.finish.report_extra.is_active() {
                "basic + extra diagnostics"
            } else {
                "basic"
            }
        } else {
            "disabled"
        };
        let network_result = if !state.network.uplink_checked {
            "skipped"
        } else if state.network.uplink_online {
            "online"
        } else {
            "offline"
        };
        let uplink_result = if state.network.uplink_checked {
            if state.network.uplink_online { "passed" } else { "failed" }
        } else {
            "skipped"
        };
        let summary = format!(
            "Network: {}\n\
Connection: {}\n\
Uplink check: {}\n\
Selected browser: {}\n\
Browser install: {}\n\
Default browser: {}\n\
Browser theme/homepage: {}\n\
Top bar widgets: {}\n\
Optional apps: {}\n\
Theme actions: {}\n\
Install report: {}\n\
Links available: keskos.org, docs.keskos.org, github.com/memegeko/keskos, downloads.keskos.org",
            network_result,
            state.network.connection_type,
            uplink_result,
            browser_label(&self.selected_browser_key()),
            state.browser_install_result,
            state.browser_default_result,
            state.browser_theme_result,
            state.topbar_result,
            state.optional_apps_result,
            state.theme_result,
            report_mode,
        );
        self.finish.summary.set_text(&summary);
    }

    fn finish_and_quit(&self) {
        self.logger.log("finish clicked");
        if self.finish.report_basic.is_active() {
            let include_extra = self.finish.report_extra.is_active();
            self.logger
                .log(&format!("install report requested basic=yes extra={}", yes_no(include_extra)));
            let response = backend::send_install_report(include_extra, &self.install_report_runtime());
            self.logger.log(&format!(
                "install report result ok={} message={}",
                yes_no(response.ok),
                response.message
            ));
            self.footer(&response.message);
        } else {
            self.logger.log("install report skipped by user");
        }
        match backend::write_marker(if self.cli.rerun { "rerun" } else { "complete" }) {
            Ok(()) => {
                self.logger.log(&format!("marker created path={}", backend::marker_path().display()));
                self.window.close();
            },
            Err(error) => {
                self.show_message(MessageType::Error, &format!("Could not write the completion marker.\n\n{error}"));
            },
        }
    }

    fn handle_response<F>(&self, title: &str, response: ActionResponse, on_success: F)
    where
        F: FnOnce(&Self),
    {
        self.logger.log(&format!("action title={} ok={} message={}", title, response.ok, response.message));
        self.footer(&response.message);
        if response.ok {
            self.show_message(MessageType::Info, &response.message);
            on_success(self);
        } else {
            self.show_message(MessageType::Warning, &response.message);
        }
        self.update_finish_summary();
    }

    fn run_sync_action<F>(&self, title: &str, program: &str, args: &[String], success_message: &str, on_success: F)
    where
        F: FnOnce(&Self),
    {
        let output = Command::new(program).args(args).output();
        match output {
            Ok(result) if result.status.success() => {
                self.footer(success_message);
                self.show_message(MessageType::Info, success_message);
                on_success(self);
            },
            Ok(result) => {
                let stderr = String::from_utf8_lossy(&result.stderr).trim().to_string();
                let message = if stderr.is_empty() {
                    format!("{title} failed.")
                } else {
                    stderr
                };
                self.logger.log(&format!("action title={} ok=false message={}", title, message));
                self.footer(&message);
                self.show_message(MessageType::Warning, &message);
            },
            Err(error) => {
                self.logger.log(&format!("action title={} ok=false message={}", title, error));
                self.footer(&error.to_string());
                self.show_message(MessageType::Error, &error.to_string());
            },
        }
        self.update_finish_summary();
    }

    fn launch_terminal_script<F>(self: &Rc<Self>, title: &str, preview: &str, script: &str, on_complete: F)
    where
        F: Fn(bool) + 'static,
    {
        let wrapped = format!("{script}; code=$?; echo; read -n 1 -s -r -p 'Press any key to close'; exit $code");
        let argv = if backend::command_exists("konsole") {
            vec![
                String::from("konsole"),
                String::from("-e"),
                String::from("bash"),
                String::from("-lc"),
                wrapped,
            ]
        } else {
            vec![String::from("bash"), String::from("-lc"), script.to_string()]
        };
        self.launch_terminal_argv(title, preview, argv, on_complete);
    }

    fn launch_terminal_argv<F>(self: &Rc<Self>, title: &str, preview: &str, argv: Vec<String>, on_complete: F)
    where
        F: Fn(bool) + 'static,
    {
        let body = format!("This action will run:\n\n{preview}");
        if !self.confirm(title, &body) {
            return;
        }

        self.logger.log(&format!("terminal action start title={} preview={}", title, preview.replace('\n', "; ")));
        let mut command = Command::new(&argv[0]);
        command.args(&argv[1..]);

        match command.spawn() {
            Ok(child) => {
                self.footer(&format!("{title} launched in a terminal window."));
                self.watch_child(child, on_complete);
            },
            Err(error) => {
                self.logger.log(&format!("terminal action failed title={} message={}", title, error));
                self.show_message(MessageType::Error, &format!("Could not start the terminal action.\n\n{error}"));
            },
        }
    }

    fn watch_child<F>(self: &Rc<Self>, child: Child, on_complete: F)
    where
        F: Fn(bool) + 'static,
    {
        let child = Rc::new(RefCell::new(Some(child)));
        let app = Rc::clone(self);
        gtk::glib::timeout_add_local(Duration::from_millis(900), move || {
            let mut borrow = child.borrow_mut();
            let Some(process) = borrow.as_mut() else {
                return gtk::glib::ControlFlow::Break;
            };

            match process.try_wait() {
                Ok(Some(status)) => {
                    let success = status.success();
                    borrow.take();
                    on_complete(success);
                    app.update_finish_summary();
                    gtk::glib::ControlFlow::Break
                },
                Ok(None) => gtk::glib::ControlFlow::Continue,
                Err(error) => {
                    app.logger.log(&format!("child wait failed message={}", error));
                    app.show_message(MessageType::Warning, &format!("Installer watcher failed.\n\n{error}"));
                    borrow.take();
                    on_complete(false);
                    gtk::glib::ControlFlow::Break
                },
            }
        });
    }

    fn show_message(&self, message_type: MessageType, text: &str) {
        let dialog = MessageDialog::new(
            Some(&self.window),
            gtk::DialogFlags::MODAL,
            message_type,
            gtk::ButtonsType::Ok,
            text,
        );
        dialog.run();
        dialog.close();
    }

    fn confirm(&self, title: &str, body: &str) -> bool {
        let dialog = MessageDialog::new(
            Some(&self.window),
            gtk::DialogFlags::MODAL,
            MessageType::Question,
            gtk::ButtonsType::None,
            title,
        );
        dialog.set_secondary_text(Some(body));
        dialog.add_button("[ CANCEL ]", ResponseType::Cancel);
        dialog.add_button("[ APPLY ]", ResponseType::Ok);
        let response = dialog.run();
        dialog.close();
        response == ResponseType::Ok
    }

    fn selected_top_bar_widgets(&self) -> Vec<String> {
        if !self.topbar.master_toggle.is_active() {
            return Vec::new();
        }

        let mut selected = Vec::new();
        if self.topbar.media_toggle.is_active() {
            selected.push(String::from("Media"));
        }
        if self.topbar.cpu_toggle.is_active() {
            selected.push(String::from("CPU"));
        }
        if self.topbar.memory_toggle.is_active() {
            selected.push(String::from("Memory"));
        }
        if self.topbar.network_toggle.is_active() {
            selected.push(String::from("Network"));
        }
        selected
    }

    fn selected_optional_app_labels(&self) -> Vec<String> {
        self.optional
            .rows
            .iter()
            .filter(|row| row.check.is_active())
            .map(|row| {
                row.check
                    .label()
                    .map(|value| value.to_string())
                    .unwrap_or_else(|| row.id.clone())
            })
            .collect()
    }

    fn install_report_runtime(&self) -> InstallReportRuntime {
        let state = self.state.borrow();
        let welcome_mode = if self.cli.rerun {
            "rerun"
        } else if self.cli.first_run {
            "first-run"
        } else {
            "manual"
        };

        InstallReportRuntime {
            install_result: String::from("success"),
            browser_selected: browser_label(&self.selected_browser_key()).to_string(),
            top_bar_widgets_selected: self.selected_top_bar_widgets(),
            optional_apps_selected: self.selected_optional_app_labels(),
            browser_install_result: state.browser_install_result.clone(),
            browser_default_result: state.browser_default_result.clone(),
            browser_theme_result: state.browser_theme_result.clone(),
            topbar_result: state.topbar_result.clone(),
            optional_apps_result: state.optional_apps_result.clone(),
            theme_result: state.theme_result.clone(),
            welcome_mode: String::from(welcome_mode),
            network_connection_type: state.network.connection_type.clone(),
            network_uplink_checked: state.network.uplink_checked,
            network_uplink_online: state.network.uplink_online,
            nmcli_available: state.network.nmcli_available,
            ping_available: state.network.ping_available,
        }
    }
}

fn build_welcome_page(stack: &Stack, cli: &Cli) {
    let content = page_box();
    let top_row = GtkBox::new(Orientation::Horizontal, 10);
    top_row.set_homogeneous(true);

    let (brand_frame, brand_panel) = titled_section("DEPLOY STATUS");
    brand_panel.add(&label("K E S K   O S", "rail-brand-title"));
    brand_panel.add(&label("FIRST BOOT STAGE", "rail-brand-meta"));
    brand_panel.add(&label("The machine greets you.", ""));
    brand_panel.add(&label("Let’s finish your first boot setup and hand the system over cleanly.", "muted"));
    top_row.pack_start(&brand_frame, true, true, 0);

    let (status_frame, status_panel) = titled_section("SYSTEM STATUS");
    status_panel.add(&label("[ OK ] user session detected", ""));
    status_panel.add(&label("[ OK ] KeskOS profile loaded", ""));
    status_panel.add(&label("[ OK ] first boot sequence ready", ""));
    status_panel.add(&label(
        if cli.rerun {
            "[ OK ] rerun mode active"
        } else if cli.first_run {
            "[ OK ] first-run mode active"
        } else {
            "[ OK ] manual launch mode active"
        },
        "muted",
    ));
    top_row.pack_start(&status_frame, true, true, 0);
    content.add(&top_row);

    let (notes_frame, notes_panel) = titled_section("CONSOLE NOTES");
    let intro = label(
        "Welcome to KeskOS.\n\nThis guided console checks uplink status, browser setup, top bar defaults, optional software, and the current desktop identity before the first session is marked complete.",
        "",
    );
    intro.set_line_wrap(true);
    notes_panel.add(&intro);
    notes_panel.add(&label("> Use [ SKIP ] when a setup block is not needed yet.", "muted"));
    notes_panel.add(&label("> Finish writes the first-boot completion marker only at the end of the flow.", "muted"));
    content.add(&notes_frame);
    stack.add_named(&wrap_scrolled(content), "welcome");
}

fn build_network_page(stack: &Stack) -> NetworkWidgets {
    let content = page_box();
    let top_row = GtkBox::new(Orientation::Horizontal, 10);
    top_row.set_homogeneous(true);

    let (status_frame, status_panel) = titled_section("UPLINK STATUS");
    let support_badge = label("Support badge: Limited", "badge");
    let uplink_status = label("Uplink status: checking", "section-title");
    let uplink_message = label(
        "Check internet access or connect to Wi-Fi before installing browsers and optional packages.",
        "muted",
    );
    uplink_message.set_line_wrap(true);
    let backend_status = label("", "");
    backend_status.set_line_wrap(true);
    let active_connection = label("", "");
    active_connection.set_line_wrap(true);
    let wired_status = label("", "");
    wired_status.set_line_wrap(true);
    let wifi_status = label("", "");
    wifi_status.set_line_wrap(true);

    status_panel.add(&support_badge);
    status_panel.add(&uplink_status);
    status_panel.add(&uplink_message);
    status_panel.add(&backend_status);
    status_panel.add(&active_connection);
    status_panel.add(&wired_status);
    status_panel.add(&wifi_status);
    top_row.pack_start(&status_frame, true, true, 0);

    let (wifi_frame, wifi_panel) = titled_section("WI-FI CONTROL");
    let grid = Grid::new();
    grid.set_row_spacing(10);
    grid.set_column_spacing(12);

    let ssid_combo = ComboBoxText::new();
    let password_entry = Entry::new();
    password_entry.set_visibility(false);
    password_entry.set_placeholder_text(Some("Wi-Fi password"));
    let show_password = CheckButton::with_label("Show password");

    grid.attach(&label("Detected SSID", "section-title"), 0, 0, 1, 1);
    grid.attach(&ssid_combo, 1, 0, 2, 1);
    grid.attach(&label("Password", "section-title"), 0, 1, 1, 1);
    grid.attach(&password_entry, 1, 1, 1, 1);
    grid.attach(&show_password, 2, 1, 1, 1);
    wifi_panel.add(&grid);

    let buttons = GtkBox::new(Orientation::Horizontal, 8);
    let scan_button = Button::with_label("[ SCAN NETWORKS ]");
    let connect_button = Button::with_label("[ CONNECT ]");
    let recheck_button = Button::with_label("[ RECHECK UPLINK ]");
    prepare_button(&scan_button);
    prepare_button(&connect_button);
    prepare_button(&recheck_button);
    apply_primary(&connect_button);
    scan_button.set_hexpand(true);
    connect_button.set_hexpand(true);
    recheck_button.set_hexpand(true);
    buttons.add(&scan_button);
    buttons.add(&connect_button);
    buttons.add(&recheck_button);
    wifi_panel.add(&buttons);

    let note = label("", "muted");
    note.set_line_wrap(true);
    wifi_panel.add(&note);
    top_row.pack_start(&wifi_frame, true, true, 0);
    content.add(&top_row);

    let (console_frame, console_panel) = titled_section("UPLINK TEST");
    console_panel.add(&label("> NetworkManager / nmcli is used when available for scan and connect operations.", "muted"));
    console_panel.add(&label("> Reachability check: ping -c 1 -W 2 8.8.8.8", "muted"));
    console_panel.add(&label("> Browser and package installs stay blocked until an uplink is detected.", "muted"));
    content.add(&console_frame);
    stack.add_named(&wrap_scrolled(content), "network");

    NetworkWidgets {
        support_badge,
        uplink_status,
        uplink_message,
        backend_status,
        active_connection,
        wired_status,
        wifi_status,
        note,
        ssid_combo,
        password_entry,
        show_password,
        scan_button,
        connect_button,
        recheck_button,
    }
}

fn build_browser_page(stack: &Stack) -> BrowserWidgets {
    let content = page_box();
    let top_row = GtkBox::new(Orientation::Horizontal, 10);
    top_row.set_homogeneous(true);

    let (profile_frame, profile_panel) = titled_section("BROWSER PROFILE");
    profile_panel.add(&label("LibreWolf is the recommended browser for KeskOS.", "muted"));

    let grid = Grid::new();
    grid.set_row_spacing(10);
    grid.set_column_spacing(12);

    let combo = ComboBoxText::new();
    for option in backend::browser_snapshots() {
        combo.append(Some(&option.key), &option.label);
    }
    combo.set_active_id(Some("librewolf"));

    let homepage_toggle = CheckButton::with_label("Apply KeskOS homepage");
    homepage_toggle.set_active(true);
    let status = label("", "");
    status.set_line_wrap(true);
    let note = label("", "muted");
    note.set_line_wrap(true);

    grid.attach(&label("Preferred browser", "section-title"), 0, 0, 1, 1);
    grid.attach(&combo, 1, 0, 1, 1);
    grid.attach(&status, 0, 1, 2, 1);
    grid.attach(&homepage_toggle, 0, 2, 2, 1);
    grid.attach(&note, 0, 3, 2, 1);
    profile_panel.add(&grid);
    top_row.pack_start(&profile_frame, true, true, 0);

    let (actions_frame, actions_panel) = titled_section("ACTIONS");
    let buttons = GtkBox::new(Orientation::Vertical, 8);
    let install_button = Button::with_label("[ INSTALL SELECTED BROWSER ]");
    let default_button = Button::with_label("[ SET AS DEFAULT BROWSER ]");
    let theme_button = Button::with_label("[ APPLY KESKOS BROWSER THEME ]");
    prepare_button(&install_button);
    prepare_button(&default_button);
    prepare_button(&theme_button);
    apply_primary(&install_button);
    install_button.set_hexpand(true);
    default_button.set_hexpand(true);
    theme_button.set_hexpand(true);
    buttons.add(&install_button);
    buttons.add(&default_button);
    buttons.add(&theme_button);
    actions_panel.add(&buttons);
    actions_panel.add(&label("> Package source is resolved with pacman first and yay as fallback.", "muted"));
    actions_panel.add(&label("> Browser setup stays available on rerun without touching the first-boot marker.", "muted"));
    top_row.pack_start(&actions_frame, true, true, 0);
    content.add(&top_row);
    stack.add_named(&wrap_scrolled(content), "browser");

    BrowserWidgets { combo, status, homepage_toggle, install_button, default_button, theme_button, note }
}

fn build_topbar_page(stack: &Stack) -> TopBarWidgets {
    let content = page_box();
    let top_row = GtkBox::new(Orientation::Horizontal, 10);
    top_row.set_homogeneous(true);

    let (status_frame, status_panel) = titled_section("BACKEND STATUS");
    status_panel.add(&label("Support badge: Limited", "badge"));

    let backend_status = label("", "");
    let info = label("", "muted");
    info.set_line_wrap(true);
    status_panel.add(&backend_status);
    status_panel.add(&info);
    top_row.pack_start(&status_frame, true, true, 0);

    let (control_frame, control_panel) = titled_section("WIDGET CONTROLS");
    let grid = Grid::new();
    grid.set_row_spacing(10);
    grid.set_column_spacing(12);
    let master_toggle = CheckButton::with_label("Enable top bar widgets");
    let media_toggle = CheckButton::with_label("Media widget");
    let cpu_toggle = CheckButton::with_label("CPU widget");
    let memory_toggle = CheckButton::with_label("Memory widget");
    let network_toggle = CheckButton::with_label("Network widget");
    for (row, toggle) in [master_toggle.clone(), media_toggle.clone(), cpu_toggle.clone(), memory_toggle.clone(), network_toggle.clone()].into_iter().enumerate() {
        grid.attach(&toggle, 0, row as i32, 1, 1);
    }
    control_panel.add(&grid);

    let buttons = GtkBox::new(Orientation::Vertical, 8);
    let apply_button = Button::with_label("[ APPLY WIDGET CHOICES ]");
    let reset_button = Button::with_label("[ RESET TO ALL ON ]");
    let restart_button = Button::with_label("[ RESTART TOP BAR WIDGETS ]");
    prepare_button(&apply_button);
    prepare_button(&reset_button);
    prepare_button(&restart_button);
    apply_primary(&apply_button);
    apply_button.set_hexpand(true);
    reset_button.set_hexpand(true);
    restart_button.set_hexpand(true);
    buttons.add(&apply_button);
    buttons.add(&reset_button);
    buttons.add(&restart_button);
    control_panel.add(&buttons);
    top_row.pack_start(&control_frame, true, true, 0);
    content.add(&top_row);
    stack.add_named(&wrap_scrolled(content), "topbar");

    TopBarWidgets {
        backend_status,
        info,
        master_toggle,
        media_toggle,
        cpu_toggle,
        memory_toggle,
        network_toggle,
        apply_button,
        reset_button,
        restart_button,
    }
}

fn build_optional_apps_page(stack: &Stack) -> OptionalWidgets {
    let content = page_box();
    let info = label("", "muted");
    info.set_line_wrap(true);
    let (info_frame, info_panel) = titled_section("PACKAGE SOURCE");
    info_panel.add(&info);
    content.add(&info_frame);

    let grouped: HashMap<&str, Vec<&backend::CatalogItem>> = {
        let mut map: HashMap<&str, Vec<&backend::CatalogItem>> = HashMap::new();
        for item in backend::optional_app_catalog() {
            map.entry(item.group).or_default().push(item);
        }
        map
    };

    let mut rows = Vec::new();
    for (left_group, right_group) in [("Gaming", "Creator"), ("Dev", "Utilities")] {
        let row = GtkBox::new(Orientation::Horizontal, 10);
        row.set_homogeneous(true);

        for group in [left_group, right_group] {
            let (frame, panel) = titled_section(group);
            if let Some(items) = grouped.get(group) {
                for item in items {
                    let row_box = GtkBox::new(Orientation::Horizontal, 10);
                    let check = CheckButton::with_label(item.label);
                    check.set_hexpand(true);
                    check.set_halign(Align::Start);
                    let status = label("", "muted");
                    status.set_halign(Align::End);
                    status.set_hexpand(true);
                    row_box.pack_start(&check, false, false, 0);
                    row_box.pack_end(&status, false, false, 0);
                    panel.add(&row_box);
                    rows.push(OptionalRow {
                        id: item.id.to_string(),
                        check,
                        status,
                    });
                }
            }
            row.pack_start(&frame, true, true, 0);
        }

        content.add(&row);
    }

    let (action_frame, action_panel) = titled_section("PACKAGE ACTIONS");
    let install_button = Button::with_label("[ INSTALL SELECTED APPS ]");
    prepare_button(&install_button);
    apply_primary(&install_button);
    action_panel.add(&install_button);
    action_panel.add(&label("> Docker is intentionally not part of this first-boot flow.", "muted"));
    action_panel.add(&label("> Optional installs are always confirmation-based and never run silently.", "muted"));
    content.add(&action_frame);
    stack.add_named(&wrap_scrolled(content), "apps");

    OptionalWidgets { rows, info, install_button }
}

fn build_theme_page(stack: &Stack) -> ThemeWidgets {
    let content = page_box();
    let top_row = GtkBox::new(Orientation::Horizontal, 10);
    top_row.set_homogeneous(true);

    let (status_frame, status_panel) = titled_section("DEPLOYMENT STATUS");
    status_panel.add(&label("Support badge: Limited", "badge"));

    let grid = Grid::new();
    grid.set_row_spacing(10);
    grid.set_column_spacing(18);

    let theme_active = label("", "");
    let kde_defaults = label("", "");
    let launcher = label("", "");
    let panels = label("", "");
    let konsole = label("", "");
    let dunst = label("", "");

    for (row, (left, right)) in [
        ("KeskOS Orange theme active", &theme_active),
        ("KDE defaults active", &kde_defaults),
        ("KDE launcher layout", &launcher),
        ("Panel layout", &panels),
        ("Konsole profile", &konsole),
        ("Dunst notification theme", &dunst),
    ]
    .into_iter()
    .enumerate()
    {
        grid.attach(&label(left, "section-title"), 0, row as i32, 1, 1);
        grid.attach(right, 1, row as i32, 1, 1);
    }
    status_panel.add(&grid);
    top_row.pack_start(&status_frame, true, true, 0);

    let (actions_frame, actions_panel) = titled_section("RECOVERY ACTIONS");
    let button_grid = Grid::new();
    button_grid.set_row_spacing(8);
    button_grid.set_column_spacing(8);
    let apply_kesk = Button::with_label("[ REAPPLY KESKOS THEME ]");
    let reset_kde = Button::with_label("[ RESET TO KDE DEFAULTS ]");
    let reapply_launcher = Button::with_label("[ REAPPLY KDE LAUNCHER ]");
    let reapply_panels = Button::with_label("[ REAPPLY PANEL LAYOUT ]");
    let reapply_konsole = Button::with_label("[ REAPPLY KONSOLE PROFILE ]");
    let reapply_dunst = Button::with_label("[ REAPPLY DUNST THEME ]");
    prepare_button(&apply_kesk);
    prepare_button(&reset_kde);
    prepare_button(&reapply_launcher);
    prepare_button(&reapply_panels);
    prepare_button(&reapply_konsole);
    prepare_button(&reapply_dunst);
    apply_primary(&apply_kesk);
    for (index, button) in [
        &apply_kesk,
        &reset_kde,
        &reapply_launcher,
        &reapply_panels,
        &reapply_konsole,
        &reapply_dunst,
    ]
    .into_iter()
    .enumerate()
    {
        button_grid.attach(button, (index % 2) as i32, (index / 2) as i32, 1, 1);
    }
    actions_panel.add(&button_grid);
    actions_panel.add(&label("> KeskOS accent color is fixed to #ce6a35 in the current desktop profile.", "muted"));
    actions_panel.add(&label("> Use these actions as repair/reset controls, not as a full theme picker.", "muted"));
    top_row.pack_start(&actions_frame, true, true, 0);
    content.add(&top_row);

    let boot_note = label("", "muted");
    boot_note.set_line_wrap(true);
    let (note_frame, note_panel) = titled_section("BOOT SPLASH STATUS");
    note_panel.add(&boot_note);
    content.add(&note_frame);
    stack.add_named(&wrap_scrolled(content), "theme");

    ThemeWidgets {
        theme_active,
        kde_defaults,
        launcher,
        panels,
        konsole,
        dunst,
        boot_note,
        apply_kesk,
        reset_kde,
        reapply_launcher,
        reapply_panels,
        reapply_konsole,
        reapply_dunst,
    }
}

fn build_links_page(stack: &Stack) {
    let content = page_box();
    let row = GtkBox::new(Orientation::Horizontal, 10);
    row.set_homogeneous(true);

    let (links_frame, links_panel) = titled_section("EXTERNAL LINKS");
    links_panel.add(&label("Use xdg-open for official KeskOS sites and project resources.", "muted"));
    for (name, title) in [
        ("website", "[ WEBSITE ]"),
        ("docs", "[ DOCS ]"),
        ("github", "[ GITHUB ]"),
        ("downloads", "[ DOWNLOADS ]"),
    ] {
        let button = Button::with_label(title);
        prepare_button(&button);
        button.set_widget_name(&format!("link-{name}"));
        links_panel.add(&button);
    }
    row.pack_start(&links_frame, true, true, 0);

    let (tools_frame, tools_panel) = titled_section("SYSTEM TOOLS");
    tools_panel.add(&label("Open the current KeskOS maintenance and configuration commands from here.", "muted"));
    for (name, title) in [
        ("settings", "[ OPEN KESK SETTINGS ]"),
        ("doctor", "[ RUN KESK DOCTOR ]"),
        ("upgrade", "[ RUN KESK UPGRADE ]"),
        ("repair", "[ RUN KESK REPAIR ]"),
    ] {
        let button = Button::with_label(title);
        prepare_button(&button);
        button.set_widget_name(&format!("tool-{name}"));
        tools_panel.add(&button);
    }
    row.pack_start(&tools_frame, true, true, 0);

    content.add(&row);

    stack.add_named(&wrap_scrolled(content), "links");
}

fn build_finish_page(stack: &Stack) -> FinishWidgets {
    let content = page_box();
    let row = GtkBox::new(Orientation::Horizontal, 10);
    row.set_homogeneous(true);

    let (summary_frame, summary_panel) = titled_section("DEPLOYMENT SUMMARY");
    let summary = label("", "");
    summary.set_selectable(true);
    summary.set_line_wrap(true);
    summary_panel.add(&summary);
    row.pack_start(&summary_frame, true, true, 0);

    let right_column = GtkBox::new(Orientation::Vertical, 10);

    let (finish_frame, finish_panel) = titled_section("COMPLETION");
    finish_panel.add(&label("Finish writes the completion marker only when you press [ FINISH ].", "muted"));
    finish_panel.add(&label("> The first-boot autostart stops only after the completion marker exists.", "muted"));
    finish_panel.add(&label("> You can reopen this flow later with `kesk welcome-rerun`.", "muted"));
    right_column.pack_start(&finish_frame, false, false, 0);

    let (report_frame, report_panel) = titled_section("INSTALL REPORT");
    let description = label(
        "KeskOS can send an install report to help improve future builds. The default report contains install status, system class, selected setup options, duration, and sanitized errors. It does not send your username, hostname, IP address, Wi-Fi name, MAC address, passwords, files, or exact location.",
        "muted",
    );
    description.set_line_wrap(true);
    let report_basic = CheckButton::with_label("Send basic install report");
    let report_extra = CheckButton::with_label("Include extra diagnostic details");
    report_extra.set_sensitive(false);
    report_panel.add(&description);
    report_panel.add(&report_basic);
    report_panel.add(&report_extra);
    report_panel.add(&label("> Client destination: https://api.keskos.org/install-report", "muted"));
    report_panel.add(&label("> Leave both options off to finish without sending a report.", "muted"));
    right_column.pack_start(&report_frame, false, false, 0);

    row.pack_start(&right_column, true, true, 0);

    content.add(&row);
    stack.add_named(&wrap_scrolled(content), "finish");
    FinishWidgets {
        summary,
        report_basic,
        report_extra,
    }
}

fn wrap_scrolled(content: GtkBox) -> ScrolledWindow {
    let scroll = ScrolledWindow::new(None::<&gtk::Adjustment>, None::<&gtk::Adjustment>);
    scroll.set_policy(PolicyType::Automatic, PolicyType::Automatic);
    scroll.set_hexpand(true);
    scroll.set_vexpand(true);
    add_class(&scroll, "page-scroll");
    let viewport = gtk::Viewport::new(None::<&gtk::Adjustment>, None::<&gtk::Adjustment>);
    viewport.set_hexpand(true);
    viewport.set_vexpand(true);
    add_class(&viewport, "page-viewport");
    let shell = GtkBox::new(Orientation::Vertical, 0);
    shell.set_hexpand(true);
    shell.set_vexpand(true);
    shell.set_halign(Align::Fill);
    shell.set_valign(Align::Start);
    add_class(&shell, "page-shell");
    add_class(&content, "page-content");
    content.set_hexpand(true);
    content.set_vexpand(false);
    shell.pack_start(&content, false, false, 0);
    let spacer = GtkBox::new(Orientation::Vertical, 0);
    spacer.set_hexpand(true);
    spacer.set_vexpand(true);
    shell.pack_start(&spacer, true, true, 0);
    viewport.add(&shell);
    scroll.add(&viewport);
    scroll
}

fn page_box() -> GtkBox {
    let content = GtkBox::new(Orientation::Vertical, 12);
    content.set_margin_top(10);
    content.set_margin_bottom(10);
    content.set_margin_start(10);
    content.set_margin_end(10);
    content
}

fn panel_frame(class_name: &str) -> Frame {
    let frame = Frame::new(None);
    add_class(&frame, class_name);
    frame
}

fn section_frame() -> Frame {
    let frame = Frame::new(None);
    add_class(&frame, "section");
    frame
}

fn label(text: &str, class_name: &str) -> Label {
    let label = Label::new(Some(text));
    label.set_halign(Align::Start);
    label.set_xalign(0.0);
    if !class_name.is_empty() {
        add_class(&label, class_name);
    }
    label
}

fn panel_separator() -> Separator {
    Separator::new(Orientation::Horizontal)
}

fn titled_section(title: &str) -> (Frame, GtkBox) {
    let frame = section_frame();
    let panel = GtkBox::new(Orientation::Vertical, 8);
    panel.set_margin_top(12);
    panel.set_margin_bottom(12);
    panel.set_margin_start(12);
    panel.set_margin_end(12);
    if !title.is_empty() {
        panel.add(&label(title, "panel-title"));
        panel.add(&panel_separator());
    }
    frame.add(&panel);
    (frame, panel)
}

fn apply_primary(button: &Button) {
    prepare_button(button);
    add_class(button, "primary");
}

fn prepare_button(button: &Button) {
    button.set_relief(ReliefStyle::None);
    button.set_can_default(false);
}

fn add_class<W: IsA<gtk::Widget>>(widget: &W, class_name: &str) {
    widget.style_context().add_class(class_name);
}

fn hero_title_for_page(spec: &PageSpec) -> String {
    if spec.key == "welcome" {
        String::from("KESKOS FIRST BOOT CONSOLE")
    } else {
        spec.sidebar
            .split_once(' ')
            .map(|(_, label)| label.to_string())
            .unwrap_or_else(|| spec.title.to_uppercase())
    }
}

fn align_button_label_start(button: &Button) {
    if let Some(child) = button.child() {
        if let Ok(label) = child.downcast::<Label>() {
            label.set_xalign(0.0);
            label.set_line_wrap(true);
        }
    }
}

fn install_css(logger: &Logger) {
    if let Some(settings) = gtk::Settings::default() {
        let _ = settings.set_property("gtk-application-prefer-dark-theme", &true);
    }
    let provider = CssProvider::new();
    if let Err(error) = provider.load_from_data(CSS.as_bytes()) {
        logger.log(&format!("css load warning: {error}"));
        return;
    }
    StyleContext::add_provider_for_screen(
        &gtk::gdk::Screen::default().expect("screen"),
        &provider,
        gtk::STYLE_PROVIDER_PRIORITY_USER,
    );
}

fn yes_no(value: bool) -> &'static str {
    if value { "yes" } else { "no" }
}

fn browser_label(key: &str) -> &'static str {
    match key {
        "librewolf" => "LibreWolf",
        "brave" => "Brave",
        "zen" => "Zen Browser",
        "firefox" => "Firefox",
        _ => "Unknown",
    }
}

fn main() {
    let cli = Cli::parse();
    let logger = Logger::new(backend::log_path());

    if cli.first_run {
        if backend::is_live_environment() {
            logger.log("first-run autostart skipped live environment detected");
            return;
        }
        if backend::marker_path().exists() || backend::legacy_marker_path().exists() {
            logger.log("first-run autostart skipped completion marker present");
            return;
        }
    }

    let application = Application::new(Some(APP_ID), Default::default());
    application.connect_activate(move |application| {
        let app = WelcomeApp::new(application, Cli {
            first_run: cli.first_run,
            rerun: cli.rerun,
        });
        app.window.show_all();
        app.go_to_page(0);
        app.logger.log("startup page forced to welcome");
    });
    application.run_with_args(&["kesk-welcome"]);
}
