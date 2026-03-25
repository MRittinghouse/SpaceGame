"""EQUIP mode helper for the ship builder view.

Extracted from ship_builder_view.py to reduce file size. Handles
equipment slot listing, equipment installation/uninstallation, and
rendering for the EQUIP mode in the drydock.

All methods operate on the parent builder view's state via a
reference passed at construction. This is organizational separation,
not architectural decoupling — the helper is tightly bound to the
builder view's data model.
"""

import pygame

from spacegame.config import Colors, scale_y
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.draw_utils import draw_panel
from spacegame.models.ship_module import (
    get_module_equipment_slots,
    resolve_placed_module,
)


# Layout constants (imported from builder, but defined locally for independence)
def _get_layout(view: object) -> dict[str, int]:
    """Get layout constants from the parent builder view.

    Returns:
        Dict with panel position/size keys (spx, spy, spw, sph, mpx, mpy, mpw).
    """
    from spacegame.views.ship_builder_view import (
        MATERIAL_PANEL_W,
        MATERIAL_PANEL_X,
        MATERIAL_PANEL_Y,
        SHAPE_PANEL_H,
        SHAPE_PANEL_W,
        SHAPE_PANEL_X,
        SHAPE_PANEL_Y,
    )

    return {
        "spx": SHAPE_PANEL_X,
        "spy": SHAPE_PANEL_Y,
        "spw": SHAPE_PANEL_W,
        "sph": SHAPE_PANEL_H,
        "mpx": MATERIAL_PANEL_X,
        "mpy": MATERIAL_PANEL_Y,
        "mpw": MATERIAL_PANEL_W,
    }


class EquipModeHelper:
    """Manages EQUIP mode interactions and rendering for the builder.

    Operates on the parent builder view's shared state (build, player,
    data_loader, fonts) via a reference. This is organizational
    separation — the helper is tightly bound to ShipBuilderView.

    Args:
        view: The parent ShipBuilderView instance.
    """

    def __init__(self, view: "ShipBuilderView") -> None:  # type: ignore[name-defined]
        self.v = view

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_equip_slots(self) -> list[dict]:
        """Get all equipment slots from placed modules."""
        catalog = self.v._get_module_catalog()
        return get_module_equipment_slots(self.v.build, catalog)

    def get_compatible_upgrades(self, slot_type: str) -> list:
        """Get installed upgrades compatible with the given slot type."""
        upgrades = getattr(self.v.player, "upgrade_manager", None)
        if not upgrades:
            return []
        type_map = {
            "core": [],
            "engine": ["engine"],
            "weapon": ["weapon"],
            "defense": ["defense"],
        }
        valid_types = type_map.get(slot_type, ["utility"])
        if not valid_types:
            return []
        return [u for u in upgrades.installed if u.slot_type in valid_types]

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def select_module_at(self, gx: int, gy: int) -> None:
        """Select a module for equipping by clicking its grid position."""
        catalog = self.v._get_module_catalog()
        for i, placed in enumerate(self.v.build.modules):
            if placed.module_id not in catalog:
                continue
            module = catalog[placed.module_id]
            if not module.provides.get("slot_type"):
                continue
            pixels = resolve_placed_module(placed, catalog)
            for p in pixels:
                if p.x == gx and p.y == gy:
                    self.v._equip_selected_module_idx = i
                    self.v._equip_scroll = 0
                    return
        self.v._equip_selected_module_idx = None

    def handle_slot_list_click(self, mx: int, my: int) -> None:
        """Handle click on the slot list (left panel in equip mode)."""
        L = _get_layout(self.v)
        slots = self.get_equip_slots()
        item_h = scale_y(46)
        start_y = L["spy"] + scale_y(28)
        for i, slot in enumerate(slots):
            iy = start_y + i * item_h
            if L["spx"] <= mx < L["spx"] + L["spw"] and iy <= my < iy + item_h:
                self.v._equip_selected_module_idx = slot["module_idx"]
                self.v._equip_scroll = 0
                return

    def handle_panel_click(self, mx: int, my: int) -> None:
        """Handle click on the equipment selection panel (right side)."""
        L = _get_layout(self.v)
        if self.v._equip_selected_module_idx is None:
            return
        if self.v._equip_selected_module_idx >= len(self.v.build.modules):
            return

        placed = self.v.build.modules[self.v._equip_selected_module_idx]
        catalog = self.v._get_module_catalog()
        module = catalog.get(placed.module_id)
        if not module:
            return
        slot_type = module.provides.get("slot_type", "")
        compatible = self.get_compatible_upgrades(slot_type)

        # Uninstall button
        uninstall_y = L["mpy"] + scale_y(26)
        if placed.installed_upgrade_id:
            uninstall_rect = pygame.Rect(L["mpx"] + 8, uninstall_y, L["mpw"] - 16, scale_y(22))
            if uninstall_rect.collidepoint(mx, my):
                self.v._push_undo()
                placed.installed_upgrade_id = None
                placed.upgrade_mark = 1
                placed.upgrade_tuning = None
                self.v._modified = True
                self.v._recompute_stats()
                try:
                    get_audio_manager().play_sfx("ui_cancel")
                except Exception:
                    pass
                return
            uninstall_y += scale_y(28)

        # Equipment items
        item_h = scale_y(40)
        start_y = uninstall_y + scale_y(6)
        for i, upgrade in enumerate(compatible):
            iy = start_y + i * item_h
            if L["mpx"] <= mx < L["mpx"] + L["mpw"] and iy <= my < iy + item_h:
                already_placed = any(
                    m.installed_upgrade_id == upgrade.id
                    for j, m in enumerate(self.v.build.modules)
                    if j != self.v._equip_selected_module_idx
                )
                if already_placed:
                    return
                self.v._push_undo()
                placed.installed_upgrade_id = upgrade.id
                if placed.upgrade_mark > 1 and placed.installed_upgrade_id != upgrade.id:
                    placed.upgrade_mark = 1
                    placed.upgrade_tuning = None
                self.v._modified = True
                self.v._recompute_stats()
                try:
                    get_audio_manager().play_sfx("ui_build")
                except Exception:
                    pass
                return

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_slot_list(self, screen: pygame.Surface) -> None:
        """Render the equipment slot list (left panel in equip mode).

        Args:
            screen: The pygame surface to render onto.
        """
        L = _get_layout(self.v)
        panel_x, panel_y = L["spx"], L["spy"]
        panel_w, panel_h = L["spw"], L["sph"]
        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=200)

        title = self.v.small_font.render("EQUIPMENT SLOTS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (panel_x + 8, panel_y + 6))

        slots = self.get_equip_slots()
        all_upgrades: dict = getattr(getattr(self.v, "data_loader", None), "upgrades", {})
        item_h = scale_y(46)
        start_y = panel_y + scale_y(28)

        # RGB tuples for slot type accent colors (left stripe + type label)
        slot_colors = {
            "core": (200, 180, 60),
            "engine": (200, 140, 40),
            "weapon": (200, 60, 60),
            "defense": (60, 120, 200),
        }

        for i, slot in enumerate(slots):
            iy = start_y + i * item_h
            if iy + item_h > panel_y + panel_h:
                break

            is_selected = slot["module_idx"] == self.v._equip_selected_module_idx
            has_equip = slot["installed_upgrade_id"] is not None
            bg = (45, 65, 100) if is_selected else ((25, 40, 30) if has_equip else (20, 25, 40))
            pygame.draw.rect(
                screen, bg, (panel_x + 3, iy, panel_w - 6, item_h - 2), border_radius=3
            )

            s_color = slot_colors.get(slot["slot_type"], Colors.TEXT_SECONDARY)
            pygame.draw.rect(screen, s_color, (panel_x + 3, iy, 4, item_h - 2))

            if is_selected:
                pygame.draw.rect(
                    screen,
                    Colors.TEXT_HIGHLIGHT,
                    (panel_x + 3, iy, panel_w - 6, item_h - 2),
                    1,
                    border_radius=3,
                )

            name_surf = self.v.label_font.render(slot["module_name"], True, Colors.TEXT_PRIMARY)
            screen.blit(name_surf, (panel_x + 12, iy + 3))
            type_label = slot["slot_type"].upper()
            type_surf = self.v.label_font.render(type_label, True, s_color)
            screen.blit(type_surf, (panel_x + 12, iy + 16))

            uid = slot["installed_upgrade_id"]
            if uid and uid in all_upgrades:
                equip_name = all_upgrades[uid].name
                mark = slot.get("upgrade_mark", 1)
                mark_text = f" Mk{mark}" if mark > 1 else ""
                equip_surf = self.v.label_font.render(
                    f"{equip_name}{mark_text}", True, Colors.GREEN
                )
                screen.blit(equip_surf, (panel_x + 12, iy + 29))
            else:
                empty_surf = self.v.label_font.render("— empty —", True, (80, 80, 90))
                screen.blit(empty_surf, (panel_x + 12, iy + 29))

    def render_panel(self, screen: pygame.Surface) -> None:
        """Render the equipment selection panel (right side in equip mode).

        Shows the selected module's current equipment, an uninstall button,
        and a list of compatible upgrades the player can install.

        Args:
            screen: The pygame surface to render onto.
        """
        L = _get_layout(self.v)
        panel_x, panel_y = L["mpx"], L["mpy"]
        panel_w = L["mpw"]
        panel_h = scale_y(400)
        draw_panel(screen, (panel_x, panel_y, panel_w, panel_h), alpha=200)

        if self.v._equip_selected_module_idx is None:
            title = self.v.small_font.render("SELECT A SLOT", True, Colors.TEXT_HIGHLIGHT)
            screen.blit(title, (panel_x + 8, panel_y + 6))
            hint = self.v.label_font.render(
                "Click a module on the grid", True, Colors.TEXT_SECONDARY
            )
            screen.blit(hint, (panel_x + 8, panel_y + 26))
            hint2 = self.v.label_font.render(
                "or a slot from the left panel", True, Colors.TEXT_SECONDARY
            )
            screen.blit(hint2, (panel_x + 8, panel_y + 40))
            return

        if self.v._equip_selected_module_idx >= len(self.v.build.modules):
            return

        placed = self.v.build.modules[self.v._equip_selected_module_idx]
        catalog = self.v._get_module_catalog()
        module = catalog.get(placed.module_id)
        if not module:
            return

        slot_type = module.provides.get("slot_type", "")
        title = self.v.small_font.render(f"EQUIP: {module.name}", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (panel_x + 8, panel_y + 6))

        row_y = panel_y + scale_y(26)
        all_upgrades = getattr(self.v.data_loader, "upgrades", {})

        if placed.installed_upgrade_id and placed.installed_upgrade_id in all_upgrades:
            current = all_upgrades[placed.installed_upgrade_id]
            curr_surf = self.v.label_font.render(f"Installed: {current.name}", True, Colors.GREEN)
            screen.blit(curr_surf, (panel_x + 8, row_y))
            row_y += scale_y(14)
            uninstall_rect = pygame.Rect(panel_x + 8, row_y, panel_w - 16, scale_y(22))
            pygame.draw.rect(screen, (50, 30, 30), uninstall_rect, border_radius=3)
            pygame.draw.rect(screen, (150, 60, 60), uninstall_rect, 1, border_radius=3)
            unsf = self.v.label_font.render("Uninstall", True, (200, 80, 80))
            screen.blit(
                unsf,
                (uninstall_rect.x + uninstall_rect.width // 2 - unsf.get_width() // 2, row_y + 4),
            )
            row_y += scale_y(28)
        else:
            empty_surf = self.v.label_font.render(
                "No equipment installed", True, Colors.TEXT_SECONDARY
            )
            screen.blit(empty_surf, (panel_x + 8, row_y))
            row_y += scale_y(18)

        row_y += scale_y(4)
        avail_header = self.v.label_font.render(
            f"Available ({slot_type}):", True, Colors.TEXT_HIGHLIGHT
        )
        screen.blit(avail_header, (panel_x + 8, row_y))
        row_y += scale_y(16)

        compatible = self.get_compatible_upgrades(slot_type)
        if not compatible:
            none_surf = self.v.label_font.render(
                "No compatible equipment owned", True, (100, 80, 80)
            )
            screen.blit(none_surf, (panel_x + 8, row_y))
            return

        item_h = scale_y(40)
        for i, upgrade in enumerate(compatible):
            iy = row_y + i * item_h
            if iy + item_h > panel_y + panel_h:
                break

            is_installed_here = placed.installed_upgrade_id == upgrade.id
            already_elsewhere = any(
                m.installed_upgrade_id == upgrade.id
                for j, m in enumerate(self.v.build.modules)
                if j != self.v._equip_selected_module_idx
            )
            if is_installed_here:
                bg = (25, 50, 35)
                border = Colors.GREEN
            elif already_elsewhere:
                bg = (25, 25, 30)
                border = (60, 60, 70)
            else:
                bg = (20, 25, 40)
                border = Colors.UI_BORDER
            pygame.draw.rect(
                screen, bg, (panel_x + 4, iy, panel_w - 8, item_h - 2), border_radius=3
            )
            pygame.draw.rect(
                screen, border, (panel_x + 4, iy, panel_w - 8, item_h - 2), 1, border_radius=3
            )

            name_color = Colors.TEXT_PRIMARY if not already_elsewhere else (70, 70, 80)
            name_surf = self.v.label_font.render(upgrade.name, True, name_color)
            screen.blit(name_surf, (panel_x + 10, iy + 3))

            if upgrade.combat_move:
                dmg = sum(
                    e.get("value", 0)
                    for e in upgrade.combat_move.get("effects", [])
                    if e.get("type") == "damage"
                )
                ecost = upgrade.combat_move.get("energy_cost", 0)
                info = f"{int(dmg)} dmg  {ecost}E"
            elif upgrade.bonus_type:
                info = f"+{upgrade.bonus_value} {upgrade.bonus_type.replace('_', ' ')}"
            else:
                info = ""
            if info:
                info_surf = self.v.label_font.render(info, True, Colors.TEXT_SECONDARY)
                screen.blit(info_surf, (panel_x + 10, iy + 16))

            if is_installed_here:
                status = self.v.label_font.render("INSTALLED", True, Colors.GREEN)
                screen.blit(status, (panel_x + panel_w - status.get_width() - 10, iy + 6))
            elif already_elsewhere:
                status = self.v.label_font.render("In use", True, (100, 80, 80))
                screen.blit(status, (panel_x + panel_w - status.get_width() - 10, iy + 6))
