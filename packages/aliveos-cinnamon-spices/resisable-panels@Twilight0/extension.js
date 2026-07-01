const UUID = "resisable-panels@Twilight0";

const Main = imports.ui.main;
const Settings = imports.ui.settings;

function getPanelLocation(panel) {
    if (!panel) return "unknown";
    
    if (panel.panelPosition === 0) {
        return "top";
    } else if (panel.panelPosition === 1) {
        return "bottom";
    } else if (panel.panelPosition === 2) {
        return "left";
    } else if (panel.panelPosition === 3) {
        return "right";
    }
    
    return "unknown";
}

function ResisablePanelsExtension(metadata) {
    this._init(metadata);
}

ResisablePanelsExtension.prototype = {
    _init: function (metadata) {
        this.metadata = metadata;
        this.settings = new Settings.ExtensionSettings(this, metadata.uuid);
        
        // Bind settings
        this.settings.bind("custom-size-enabled", "custom_size_enabled", this.onSettingsChanged.bind(this));
        this.settings.bind("selected-panel-size", "selected_panel_size", this.onPanelSizeChanged.bind(this));
        this.settings.bind("selected-panel-floating", "selected_panel_floating", this.onPanelFloatingChanged.bind(this));
        this.settings.bind("selected-panel-floating-offset", "selected_panel_floating_offset", this.onPanelFloatingOffsetChanged.bind(this));
        
        // Settings migration: migrate panel-sizes-dict to panel-configs-dict if needed
        let oldSizes = this.settings.getValue("panel-sizes-dict");
        let newConfigs = this.settings.getValue("panel-configs-dict") || {};
        if (oldSizes && Object.keys(oldSizes).length > 0 && Object.keys(newConfigs).length === 0) {
            for (let id in oldSizes) {
                newConfigs[id] = {
                    size: oldSizes[id],
                    floating: false,
                    offset: 10
                };
            }
            this.settings.setValue("panel-configs-dict", newConfigs);
            this.settings.setValue("panel-sizes-dict", {});
        }
        
        this._panelStates = {};
        this._monitorsChangedId = 0;
        this._updateTimeoutId = 0;
        this._highlightTimeoutId = 0;
        
        this._selectedPanelId = null;
        this._blockingSizeUpdate = false;
    },
    
    enable: function () {
        // Listen to monitor changes to refresh layout
        this._monitorsChangedId = Main.layoutManager.connect('monitors-changed', () => this.onMonitorsChanged());
        
        this.setupPanels();
        this._initSelectedPanel();
        this.queueUpdateLayout();
    },
    
    disable: function () {
        if (this._monitorsChangedId) {
            Main.layoutManager.disconnect(this._monitorsChangedId);
            this._monitorsChangedId = 0;
        }
        
        if (this._updateTimeoutId) {
            let GLib = imports.gi.GLib;
            GLib.source_remove(this._updateTimeoutId);
            this._updateTimeoutId = 0;
        }
        
        if (this._highlightTimeoutId) {
            let GLib = imports.gi.GLib;
            GLib.source_remove(this._highlightTimeoutId);
            this._highlightTimeoutId = 0;
        }
        
        this.cleanupPanels();
        this.settings.finalize();
    },
    
    setupPanels: function () {
        this.cleanupPanels();
        
        Main.getPanels().forEach(panel => {
            if (!panel || !panel.actor) return;
            
            this._panelStates[panel.panelId] = {
                lastWidth: 0,
                lastHeight: 0
            };
        });
    },
    
    cleanupPanels: function () {
        Main.getPanels().forEach(panel => {
            if (!panel || !panel.actor) return;
            
            try {
                panel.actor.set_style("");
                panel.actor.translation_y = 0;
                panel.actor.translation_x = 0;
            } catch (e) {}
        });
        this._panelStates = {};
    },
    
    getActivePanels: function () {
        return Main.getPanels().filter(panel => panel && panel.actor);
    },
    
    _initSelectedPanel: function () {
        let activePanels = this.getActivePanels();
        if (activePanels.length === 0) {
            this._selectedPanelId = null;
            return;
        }
        
        let currentActive = activePanels.some(p => p.panelId === this._selectedPanelId);
        if (!currentActive) {
            this._selectedPanelId = activePanels[0].panelId;
        }
    },
    
    on_next_panel_pressed: function () {
        this.cycleSelectedPanel(1);
    },
    
    on_prev_panel_pressed: function () {
        this.cycleSelectedPanel(-1);
    },
    
    cycleSelectedPanel: function (direction) {
        let activePanels = this.getActivePanels();
        if (activePanels.length === 0) return;
        
        this._initSelectedPanel();
        
        let index = activePanels.findIndex(p => p.panelId === this._selectedPanelId);
        if (index === -1) {
            index = 0;
        } else {
            index = (index + direction + activePanels.length) % activePanels.length;
        }
        
        let newPanel = activePanels[index];
        this._selectedPanelId = newPanel.panelId;
        
        let configsDict = this.settings.getValue("panel-configs-dict") || {};
        let config = configsDict[this._selectedPanelId] || {};
        
        let size = config.size !== undefined ? config.size : 80;
        let floating = config.floating !== undefined ? config.floating : false;
        let offset = config.offset !== undefined ? config.offset : 10;
        
        this._blockingSizeUpdate = true;
        this.settings.setValue("selected-panel-size", size);
        this.settings.setValue("selected-panel-floating", floating);
        this.settings.setValue("selected-panel-floating-offset", offset);
        
        // Defer unblocking until all GSettings change events have completed on the main loop
        let GLib = imports.gi.GLib;
        GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            this._blockingSizeUpdate = false;
            return GLib.SOURCE_REMOVE;
        });
        
        this.highlightPanel(newPanel);
    },
    
    highlightPanel: function (panel) {
        if (!panel || !panel.actor) return;
        
        if (this._highlightTimeoutId) {
            let GLib = imports.gi.GLib;
            GLib.source_remove(this._highlightTimeoutId);
            this._highlightTimeoutId = 0;
        }
        
        let location = getPanelLocation(panel);
        let monitor = Main.layoutManager.monitors[panel.monitorIndex];
        if (!monitor) return;
        
        let configsDict = this.settings.getValue("panel-configs-dict") || {};
        let config = configsDict[panel.panelId] || {};
        
        let sizePercent = config.size !== undefined ? config.size : 80;
        let isFloating = config.floating !== undefined ? config.floating : false;
        let floatOffset = config.offset !== undefined ? config.offset : 10;
        
        let styleStr = "";
        if (this.custom_size_enabled) {
            if (location === "bottom" || location === "top") {
                let desiredWidth = monitor.width * (sizePercent / 100.0);
                desiredWidth = Math.max(desiredWidth, 200);
                let margin = (monitor.width - desiredWidth) / 2;
                styleStr += "margin-left: " + margin + "px; margin-right: " + margin + "px;";
            } else if (location === "left" || location === "right") {
                let desiredHeight = monitor.height * (sizePercent / 100.0);
                desiredHeight = Math.max(desiredHeight, 200);
                let margin = (monitor.height - desiredHeight) / 2;
                styleStr += "margin-top: " + margin + "px; margin-bottom: " + margin + "px;";
            }
        }
        
        let translationX = 0;
        let translationY = 0;
        if (isFloating && floatOffset > 0) {
            if (location === "top") {
                translationY = floatOffset;
            } else if (location === "bottom") {
                translationY = -floatOffset;
            } else if (location === "left") {
                translationX = floatOffset;
            } else if (location === "right") {
                translationX = -floatOffset;
            }
        }
        
        // Highlight styling
        let highlightStyle = styleStr + " border: 3px solid #ff5500; box-shadow: 0 0 10px #ff5500;";
        panel.actor.set_style(highlightStyle);
        panel.actor.translation_x = translationX;
        panel.actor.translation_y = translationY;
        
        // Revert style after 1.5s
        let GLib = imports.gi.GLib;
        this._highlightTimeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1500, () => {
            this._highlightTimeoutId = 0;
            this.updateLayout();
            return GLib.SOURCE_REMOVE;
        });
    },
    
    onMonitorsChanged: function () {
        this.setupPanels();
        this._initSelectedPanel();
        this.queueUpdateLayout();
    },
    
    onSettingsChanged: function () {
        this.queueUpdateLayout();
    },
    
    onPanelSizeChanged: function () {
        if (this._blockingSizeUpdate) return;
        
        this._initSelectedPanel();
        if (this._selectedPanelId === null) return;
        
        let configsDict = this.settings.getValue("panel-configs-dict") || {};
        let config = configsDict[this._selectedPanelId] || {};
        config.size = this.selected_panel_size;
        configsDict[this._selectedPanelId] = config;
        
        this.settings.setValue("panel-configs-dict", configsDict);
        this.queueUpdateLayout();
    },
    
    onPanelFloatingChanged: function () {
        if (this._blockingSizeUpdate) return;
        
        this._initSelectedPanel();
        if (this._selectedPanelId === null) return;
        
        let configsDict = this.settings.getValue("panel-configs-dict") || {};
        let config = configsDict[this._selectedPanelId] || {};
        config.floating = this.selected_panel_floating;
        configsDict[this._selectedPanelId] = config;
        
        this.settings.setValue("panel-configs-dict", configsDict);
        this.queueUpdateLayout();
    },
    
    onPanelFloatingOffsetChanged: function () {
        if (this._blockingSizeUpdate) return;
        
        this._initSelectedPanel();
        if (this._selectedPanelId === null) return;
        
        let configsDict = this.settings.getValue("panel-configs-dict") || {};
        let config = configsDict[this._selectedPanelId] || {};
        config.offset = this.selected_panel_floating_offset;
        configsDict[this._selectedPanelId] = config;
        
        this.settings.setValue("panel-configs-dict", configsDict);
        this.queueUpdateLayout();
    },
    
    queueUpdateLayout: function () {
        if (this._updateTimeoutId) {
            return;
        }
        
        let GLib = imports.gi.GLib;
        this._updateTimeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
            this._updateTimeoutId = 0;
            this.updateLayout();
            return GLib.SOURCE_REMOVE;
        });
    },
    
    updateLayout: function () {
        let configsDict = this.settings.getValue("panel-configs-dict") || {};
        
        Main.getPanels().forEach(panel => {
            if (!panel || !panel.actor) return;
            let state = this._panelStates[panel.panelId];
            if (!state) return;
            
            // Skip layout update if the panel is currently highlighted
            if (this._highlightTimeoutId && panel.panelId === this._selectedPanelId) {
                return;
            }
            
            let location = getPanelLocation(panel);
            let monitor = Main.layoutManager.monitors[panel.monitorIndex];
            if (!monitor) return;
            
            let styleStr = "";
            let config = configsDict[panel.panelId] || {};
            let sizePercent = config.size !== undefined ? config.size : 80;
            let isFloating = config.floating !== undefined ? config.floating : false;
            let floatOffset = config.offset !== undefined ? config.offset : 10;
            
            if (this.custom_size_enabled) {
                if (location === "bottom" || location === "top") {
                    let desiredWidth = monitor.width * (sizePercent / 100.0);
                    desiredWidth = Math.max(desiredWidth, 200);
                    let margin = (monitor.width - desiredWidth) / 2;
                    styleStr += "margin-left: " + margin + "px; margin-right: " + margin + "px;";
                } else if (location === "left" || location === "right") {
                    let desiredHeight = monitor.height * (sizePercent / 100.0);
                    desiredHeight = Math.max(desiredHeight, 200);
                    let margin = (monitor.height - desiredHeight) / 2;
                    styleStr += "margin-top: " + margin + "px; margin-bottom: " + margin + "px;";
                }
            }
            
            let translationX = 0;
            let translationY = 0;
            if (isFloating && floatOffset > 0) {
                if (location === "top") {
                    translationY = floatOffset;
                } else if (location === "bottom") {
                    translationY = -floatOffset;
                } else if (location === "left") {
                    translationX = floatOffset;
                } else if (location === "right") {
                    translationX = -floatOffset;
                }
            }
            
            let currentStyle = panel.actor.get_style();
            if (currentStyle === styleStr &&
                panel.actor.translation_x === translationX &&
                panel.actor.translation_y === translationY) {
                return;
            }
            
            panel.actor.translation_x = translationX;
            panel.actor.translation_y = translationY;
            panel.actor.set_style(styleStr);
        });
    }
};

var extension = null;

function enable() {
    try {
        extension.enable();
        return extension;
    } catch (err) {
        global.logError(err);
        if (extension) {
            extension.disable();
        }
        throw err;
    }
}

function disable() {
    try {
        if (extension) {
            extension.disable();
        }
    } catch (err) {
        global.logError(err);
    } finally {
        extension = null;
    }
}

function init(metadata) {
    extension = new ResisablePanelsExtension(metadata);
}
