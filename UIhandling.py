import os
import sys

# Must be set before ANY Qt import so macOS can find the cocoa platform plugin.
# We compute the path without importing PySide6 first (which would trigger its
# __init__.py calling QCoreApplication.addLibraryPath before our env var lands).
if sys.platform == "darwin" and "QT_QPA_PLATFORM_PLUGIN_PATH" not in os.environ:
    import importlib.util as _ilu
    _spec = _ilu.find_spec("PySide6")
    if _spec and _spec.origin:
        _ps6_dir = os.path.dirname(_spec.origin)
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
            _ps6_dir, "Qt", "plugins", "platforms"
        )
    del _ilu, _spec, _ps6_dir

import math

import requests
from PySide6.QtCore import Qt, QThread, Signal, QPoint, QPointF, QRectF, QSize
from PySide6.QtGui import (
    QPixmap, QFont, QColor, QPalette, QPen, QPainterPath, QIcon,
    QPainter, QKeySequence, QShortcut, QBrush, QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QComboBox, QLabel, QFrame, QGridLayout, QStatusBar,
    QToolBar, QToolButton, QButtonGroup, QPushButton, QSpinBox,
    QColorDialog, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsTextItem, QGraphicsItem,
    QGraphicsItemGroup, QScrollArea, QToolTip,
)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
ANNOT_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "Annotassets")
BASE_URL   = "https://war-service-live.foxholeservices.com/api"

TOOL_SELECT   = "select"
TOOL_LINE     = "line"
TOOL_ARROW    = "arrow"
TOOL_ZIGZAG   = "zigzag"
TOOL_WAVE     = "wave"
TOOL_POLYGON  = "polygon"
TOOL_TEXT     = "text"
TOOL_ERASE    = "erase"

LINE_TOOLS = {TOOL_LINE, TOOL_ARROW, TOOL_ZIGZAG, TOOL_WAVE}
MAP_SYMBOL_SCALE = 0.0333333333
FRIENDLY_COLOR_HEX = "#1200f4"
ENEMY_COLOR_HEX = "#e100d8"
SYMBOLS = [
    {"key": "AA", "label": "AA", "friendly": "F_AA.png", "enemy": "AA.png"},
    {"key": "Airfield", "label": "Airfield", "friendly": "F_Airfield.png", "enemy": "Airfield.png"},
    {"key": "Arty_Pos", "label": "Arty Pos", "friendly": "F_Arty_Pos.png", "enemy": "Arty_Pos.png"},
    {"key": "AT_Gar", "label": "AT Gar", "friendly": "F_AT_Gar.png", "enemy": "AT_Gar.png"},
    {"key": "AT_Pill", "label": "AT Pill", "friendly": "F_AT_Pill.png", "enemy": "AT_Pill.png"},
    {"key": "AT_Pill_30mm", "label": "30mm AT", "friendly": "F_AT_Pill_30mm.png", "enemy": "AT_Pill_30mm.png"},
    {"key": "BB", "label": "BB", "friendly": "F_BB.png", "enemy": "BB.png"},
    {"key": "Empl_Anti_inf", "label": "Anti Inf", "friendly": "F_Empl_Anti_inf.png", "enemy": "Empl_Anti_inf.png"},
    {"key": "Empl_AT", "label": "Empl AT", "friendly": "F_Empl_AT.png", "enemy": "Empl_AT.png"},
    {"key": "Empty_B", "label": "Empty B", "friendly": "F_Empty_B.png", "enemy": "Empty_B.png"},
    {"key": "Howi_Gar", "label": "Howi Gar", "friendly": "F_Howi_Gar.png", "enemy": "Howi_Gar.png"},
    {"key": "Industry", "label": "Industry", "friendly": "F_Industry.png", "enemy": "Industry.png"},
    {"key": "Large_Ship", "label": "Large Ship", "friendly": "F_Large_Ship.png", "enemy": "Large_Ship.png"},
    {"key": "Launch_Site", "label": "Launch", "friendly": "F_Launch_Site.png", "enemy": "Launch_Site.png"},
    {"key": "MG_Gar", "label": "MG Gar", "friendly": "F_MG_Gar.png", "enemy": "MGun_Gar.png"},
    {"key": "MG_Pill", "label": "MG Pill", "friendly": "F_MG_Pill.png", "enemy": "MG_Pill.png"},
    {"key": "Obs_B", "label": "Obs B", "friendly": "F_Obs_B.png", "enemy": "Obs_B.png"},
    {"key": "Rel_B_M", "label": "Relic M", "friendly": "F_Rel_B_M.png", "enemy": "Rel_B_M.png"},
    {"key": "Rel_B_S", "label": "Relic S", "friendly": "F_Rel_B_S.png", "enemy": "Rel_B_S.png"},
    {"key": "Rel_B_TH", "label": "Relic TH", "friendly": "F_Rel_B_TH.png", "enemy": "Rel_B_TH.png"},
    {"key": "Rifle_Gar", "label": "Rifle Gar", "friendly": "F_Rifle_Gar.png", "enemy": "Rifle_Gar.png"},
    {"key": "Rifle_Pill", "label": "Rifle Pill", "friendly": "F_Rifle_Pill.png", "enemy": "Rifle_Pill.png"},
    {"key": "Small_Ship", "label": "Small Ship", "friendly": "F_Small_Ship.png", "enemy": "Small_Ship.png"},
    {"key": "Triangle_B", "label": "Triangle B", "friendly": "F_Traingle_B.png", "enemy": "Triangle_B.png"},
    {"key": "VP", "label": "VP", "friendly": None, "enemy": "VP.png"},
]


# --------------------------------------------------------------------------- #
#  WarAPI client                                                               #
# --------------------------------------------------------------------------- #
class WarAPIClient:
    """Minimal synchronous client for the Foxhole War API."""

    def __init__(self):
        self.base_url = BASE_URL
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def get_maps(self) -> list[str]:
        return self._get("/worldconquest/maps")

    def get_war(self) -> dict:
        return self._get("/worldconquest/war")

    def get_war_report(self, map_name: str) -> dict:
        return self._get(f"/worldconquest/warReport/{map_name}")

    def get_static(self, map_name: str) -> dict:
        return self._get(f"/worldconquest/maps/{map_name}/static")

    def get_dynamic(self, map_name: str) -> dict:
        return self._get(f"/worldconquest/maps/{map_name}/dynamic/public")

    def _get(self, endpoint: str):
        response = self._session.get(f"{self.base_url}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()


# --------------------------------------------------------------------------- #
#  Background worker                                                           #
# --------------------------------------------------------------------------- #
class HexDataWorker(QThread):
    data_ready = Signal(str, dict, dict)  # hexagon, dynamic, war_report
    error = Signal(str, str)  # hexagon, message

    def __init__(self, client: WarAPIClient, hexagon: str):
        super().__init__()
        self.client  = client
        self.hexagon = hexagon

    def run(self):
        try:
            dynamic    = self.client.get_dynamic(self.hexagon)
            war_report = self.client.get_war_report(self.hexagon)
            if self.isInterruptionRequested():
                return
            self.data_ready.emit(self.hexagon, dynamic or {}, war_report or {})
        except Exception as e:
            if self.isInterruptionRequested():
                return
            self.error.emit(self.hexagon, str(e))


# --------------------------------------------------------------------------- #
#  Annotation canvas                                                           #
# --------------------------------------------------------------------------- #
class AnnotationView(QGraphicsView):
    """QGraphicsView with mouse-wheel zoom, middle-mouse pan, and draw tools."""

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QBrush(QColor("#1e1e2e")))
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._tool       = TOOL_SELECT
        self._pen_color  = QColor("#ff4444")
        self._pen_width  = 3
        self._symbol_name: str | None = None
        self._symbol_pixmap: QPixmap | None = None
        self._symbol_preview_item: QGraphicsPixmapItem | None = None
        self._ann_stack: list = []  # undo history

        # Node-based line drawing state
        self._line_nodes: list[QPointF] = []   # confirmed nodes
        self._polygon_nodes: list[QPointF] = []
        self._preview_item: QGraphicsPathItem | None = None  # live preview
        self._polygon_preview_item: QGraphicsPolygonItem | None = None

        # Middle-mouse pan state
        self._panning  = False
        self._pan_start: QPointF | None = None

        # Minimum zoom scale (set after fitInView so we never zoom out past fit)
        self._min_scale: float = 0.0

        self.set_tool(TOOL_SELECT)

    # ── Public API ──────────────────────────────────────────────────────── #

    def set_tool(self, tool: str):
        # Cancel any in-progress line when switching tools
        if self._line_nodes and tool != self._tool:
            self._cancel_line()
        if self._polygon_nodes and tool != self._tool:
            self._cancel_polygon()
        self._tool = tool
        cursor_map = {
            TOOL_SELECT: Qt.CursorShape.ArrowCursor,
            TOOL_LINE:   Qt.CursorShape.CrossCursor,
            TOOL_ARROW:  Qt.CursorShape.CrossCursor,
            TOOL_ZIGZAG: Qt.CursorShape.CrossCursor,
            TOOL_WAVE:   Qt.CursorShape.CrossCursor,
            TOOL_POLYGON: Qt.CursorShape.CrossCursor,
            TOOL_TEXT:   Qt.CursorShape.IBeamCursor,
            TOOL_ERASE:  Qt.CursorShape.PointingHandCursor,
        }
        self.setCursor(cursor_map.get(tool, Qt.CursorShape.ArrowCursor))
        self.setDragMode(
            QGraphicsView.DragMode.RubberBandDrag
            if tool == TOOL_SELECT
            else QGraphicsView.DragMode.NoDrag
        )

    def set_pen_color(self, color: QColor):
        self._pen_color = color

    def set_pen_width(self, width: int):
        self._pen_width = width

    def set_symbol_stamp(self, name: str, pixmap: QPixmap):
        if pixmap.isNull():
            self.clear_symbol_stamp()
            return
        self._symbol_name = name
        self._symbol_pixmap = pixmap
        self._ensure_symbol_preview_item()
        self.setCursor(Qt.CursorShape.CrossCursor)

    def clear_symbol_stamp(self):
        self._symbol_name = None
        self._symbol_pixmap = None
        self._hide_symbol_preview()
        self.set_tool(self._tool)

    def load_image(self, path: str):
        self._scene.clear()
        self._ann_stack.clear()
        self._line_nodes = []
        self._polygon_nodes = []
        self._preview_item = None
        self._polygon_preview_item = None
        self._symbol_preview_item = None
        pixmap = QPixmap(path)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setZValue(0)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def clear_image(self):
        self._scene.clear()
        self._pixmap_item = None
        self._ann_stack.clear()
        self._line_nodes = []
        self._polygon_nodes = []
        self._preview_item = None
        self._polygon_preview_item = None
        self._symbol_preview_item = None
        placeholder = self._scene.addText(
            "No map image available for this hexagon",
            QFont("Segoe UI", 14),
        )
        placeholder.setDefaultTextColor(QColor("#6c7086"))
        self._scene.setSceneRect(QRectF(0, 0, 800, 500))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def clear_annotations(self):
        self._hide_symbol_preview()
        for item in list(self._scene.items()):
            if item is not self._pixmap_item:
                self._scene.removeItem(item)
        self._ann_stack.clear()
        self._line_nodes = []
        self._polygon_nodes = []
        self._preview_item = None
        self._polygon_preview_item = None
        self._symbol_preview_item = None
        if self._symbol_pixmap is not None:
            self._ensure_symbol_preview_item()

    def undo_last(self):
        if self._ann_stack:
            self._scene.removeItem(self._ann_stack.pop())

    def zoom_in(self):
        self.scale(1.25, 1.25)

    def zoom_out(self):
        min_s = self._fit_scale()
        if min_s > 0 and self.transform().m11() / 1.25 < min_s:
            return
        self.scale(1 / 1.25, 1 / 1.25)

    def zoom_reset(self):
        self.resetTransform()
        if self._scene.sceneRect().isValid():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _fit_scale(self) -> float:
        """Compute the scale fitInView would produce given the current viewport size."""
        rect = self._scene.sceneRect()
        if not rect.isValid() or rect.width() == 0 or rect.height() == 0:
            return 0.0
        vp = self.viewport()
        return min(vp.width() / rect.width(), vp.height() / rect.height())

    def _grid_spec(self) -> tuple[int, int, float, float] | None:
        if self._pixmap_item is None:
            return None
        pixmap = self._pixmap_item.pixmap()
        if pixmap.isNull():
            return None
        cols = 17  # A-Q
        rows = 15  # 1-15
        col_w = pixmap.width() / cols
        row_h = pixmap.height() / rows
        if col_w <= 0 or row_h <= 0:
            return None
        return cols, rows, col_w, row_h

    def _scene_to_grid_label(self, scene_pos: QPointF) -> str | None:
        spec = self._grid_spec()
        if spec is None:
            return None

        cols, rows, col_w, row_h = spec
        if scene_pos.x() < 0 or scene_pos.y() < 0:
            return None
        if scene_pos.x() >= col_w * cols or scene_pos.y() >= row_h * rows:
            return None

        col_idx = min(cols - 1, max(0, int(scene_pos.x() / col_w)))
        row_top_idx = min(rows - 1, max(0, int(scene_pos.y() / row_h)))

        letter = chr(ord("A") + col_idx)
        number = row_top_idx + 1

        cell_x = scene_pos.x() - (col_idx * col_w)
        cell_y = scene_pos.y() - (row_top_idx * row_h)
        sub_col = min(2, max(0, int(cell_x / (col_w / 3.0))))
        sub_row_top = min(2, max(0, int(cell_y / (row_h / 3.0))))
        sub_row_bottom = 2 - sub_row_top
        subgrid = sub_row_bottom * 3 + sub_col + 1

        return f"{letter},{number}- k{subgrid}"

    def _update_cursor_grid_tooltip(self, event, scene_pos: QPointF):
        label = self._scene_to_grid_label(scene_pos)
        if label is None:
            QToolTip.hideText()
            return
        QToolTip.showText(
            event.globalPosition().toPoint() + QPoint(16, 18),
            label,
            self.viewport(),
        )

    def drawForeground(self, painter: QPainter, rect: QRectF):
        super().drawForeground(painter, rect)

        spec = self._grid_spec()
        if spec is None:
            return

        cols, rows, col_w, row_h = spec
        map_width = col_w * cols
        map_height = row_h * rows
        map_rect = QRectF(0.0, 0.0, map_width, map_height)
        draw_rect = rect.intersected(map_rect)
        if draw_rect.isEmpty():
            return

        painter.save()
        painter.setClipRect(draw_rect)

        scale = self.transform().m11()

        main_pen = QPen(QColor(255, 255, 255, 110))
        main_pen.setCosmetic(True)
        main_pen.setWidth(1)
        painter.setPen(main_pen)

        for col in range(cols + 1):
            x = col * col_w
            painter.drawLine(QPointF(x, 0), QPointF(x, map_height))
        for row in range(rows + 1):
            y = row * row_h
            painter.drawLine(QPointF(0, y), QPointF(map_width, y))

        if scale >= 2.0:
            sub_pen = QPen(QColor(255, 255, 255, 55))
            sub_pen.setCosmetic(True)
            sub_pen.setWidth(1)
            painter.setPen(sub_pen)
            for col in range(cols):
                x0 = col * col_w
                painter.drawLine(QPointF(x0 + (col_w / 3.0), 0), QPointF(x0 + (col_w / 3.0), map_height))
                painter.drawLine(QPointF(x0 + (2.0 * col_w / 3.0), 0), QPointF(x0 + (2.0 * col_w / 3.0), map_height))
            for row in range(rows):
                y0 = row * row_h
                painter.drawLine(QPointF(0, y0 + (row_h / 3.0)), QPointF(map_width, y0 + (row_h / 3.0)))
                painter.drawLine(QPointF(0, y0 + (2.0 * row_h / 3.0)), QPointF(map_width, y0 + (2.0 * row_h / 3.0)))

        painter.restore()

    # ── Line path builders ───────────────────────────────────────────────── #

    @staticmethod
    def _build_straight(nodes: list[QPointF]) -> QPainterPath:
        path = QPainterPath(nodes[0])
        for pt in nodes[1:]:
            path.lineTo(pt)
        return path

    def _build_zigzag(self, nodes: list[QPointF], amp: float = 1.25, wavelength: float = 2.5) -> QPainterPath:
        """Draw a fixed-size zig-zag: longer lines add zigs, not larger zigs."""
        # Sub-1 values are treated as normalized controls for practical UI tuning.
        amp_px = amp if amp > 1.0 else max(self._pen_width * 0.75, amp * 18.0)
        wavelength_px = wavelength if wavelength > 1.0 else max(2.0, wavelength * 24.0)

        path = QPainterPath(nodes[0])
        side = 1
        for i in range(1, len(nodes)):
            a, b = nodes[i - 1], nodes[i]
            dx, dy = b.x() - a.x(), b.y() - a.y()
            length = math.hypot(dx, dy) or 1
            # perpendicular unit vector
            px, py = -dy / length, dx / length
            segs = max(1, min(300, int(math.ceil(length / wavelength_px))))
            for s in range(1, segs):
                t = s / segs
                mx = a.x() + dx * t
                my = a.y() + dy * t
                offset = amp_px * side
                path.lineTo(QPointF(mx + px * offset, my + py * offset))
                side *= -1
            path.lineTo(b)
        return path

    def _build_wave(self, nodes: list[QPointF], amp: float = 1.25, wavelength: float = 5.0) -> QPainterPath:
        """Draw a fixed-size wave: longer lines add waves, not larger waves."""
        # Sub-1 values are treated as normalized controls for practical UI tuning.
        amp_px = amp if amp > 1.0 else max(self._pen_width * 0.75, amp * 18.0)
        wavelength_px = wavelength if wavelength > 1.0 else max(2.0, wavelength * 24.0)

        path = QPainterPath(nodes[0])
        for i in range(1, len(nodes)):
            a, b = nodes[i - 1], nodes[i]
            dx, dy = b.x() - a.x(), b.y() - a.y()
            length = math.hypot(dx, dy) or 1
            ux, uy = dx / length, dy / length   # tangent unit
            px, py = -uy, ux                    # perpendicular unit
            segs = max(1, min(300, int(math.ceil(length / wavelength_px))))
            seg_len = length / segs
            for s in range(segs):
                t0 = s / segs
                t1 = (s + 1) / segs
                p0 = QPointF(a.x() + dx * t0, a.y() + dy * t0)
                p3 = QPointF(a.x() + dx * t1, a.y() + dy * t1)
                sign = 1 if s % 2 == 0 else -1
                ctrl_off = amp_px * sign
                p1 = QPointF(p0.x() + ux * seg_len * 0.33 + px * ctrl_off,
                             p0.y() + uy * seg_len * 0.33 + py * ctrl_off)
                p2 = QPointF(p0.x() + ux * seg_len * 0.67 + px * ctrl_off,
                             p0.y() + uy * seg_len * 0.67 + py * ctrl_off)
                path.cubicTo(p1, p2, p3)
        return path

    def _build_path_for_tool(self, nodes: list[QPointF]) -> QPainterPath:
        if self._tool == TOOL_ZIGZAG:
            return self._build_zigzag(nodes)
        if self._tool == TOOL_WAVE:
            return self._build_wave(nodes)
        return self._build_straight(nodes)  # LINE and ARROW

    def _make_pen(self) -> QPen:
        return QPen(
            self._pen_color, self._pen_width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )

    def _add_arrowhead(self, group: QGraphicsItemGroup, tip: QPointF, prev: QPointF):
        """Attach a filled arrowhead polygon pointing from prev→tip."""
        dx, dy = tip.x() - prev.x(), tip.y() - prev.y()
        length = math.hypot(dx, dy) or 1
        ux, uy = dx / length, dy / length
        size = max(12, self._pen_width * 4)
        base = QPointF(tip.x() - ux * size, tip.y() - uy * size)
        perp = QPointF(-uy * size * 0.4, ux * size * 0.4)
        poly = QPolygonF([
            tip,
            QPointF(base.x() + perp.x(), base.y() + perp.y()),
            QPointF(base.x() - perp.x(), base.y() - perp.y()),
        ])
        arrow_item = QGraphicsPolygonItem(poly)
        arrow_item.setPen(QPen(Qt.PenStyle.NoPen))
        arrow_item.setBrush(QBrush(self._pen_color))
        arrow_item.setZValue(1)
        group.addToGroup(arrow_item)

    def _commit_line(self):
        """Finalise and commit the current node list as a permanent annotation."""
        if len(self._line_nodes) < 2:
            self._cancel_line()
            return

        if self._preview_item:
            self._scene.removeItem(self._preview_item)
            self._preview_item = None

        path = self._build_path_for_tool(self._line_nodes)
        group = QGraphicsItemGroup()
        self._scene.addItem(group)

        path_item = QGraphicsPathItem(path)
        path_item.setPen(self._make_pen())
        path_item.setZValue(1)
        group.addToGroup(path_item)

        if self._tool == TOOL_ARROW and len(self._line_nodes) >= 2:
            self._add_arrowhead(group, self._line_nodes[-1], self._line_nodes[-2])

        self._ann_stack.append(group)
        self._line_nodes = []

    def _cancel_line(self):
        if self._preview_item:
            self._scene.removeItem(self._preview_item)
            self._preview_item = None
        self._line_nodes = []

    def _commit_polygon(self):
        if len(self._polygon_nodes) < 3:
            self._cancel_polygon()
            return

        if self._polygon_preview_item:
            self._scene.removeItem(self._polygon_preview_item)
            self._polygon_preview_item = None

        poly_item = QGraphicsPolygonItem(QPolygonF(self._polygon_nodes))
        poly_item.setPen(self._make_pen())
        fill_color = QColor(self._pen_color)
        fill_color.setAlphaF(0.2)
        poly_item.setBrush(QBrush(fill_color))
        poly_item.setZValue(1)
        poly_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        poly_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self._scene.addItem(poly_item)
        self._ann_stack.append(poly_item)
        self._polygon_nodes = []

    def _cancel_polygon(self):
        if self._polygon_preview_item:
            self._scene.removeItem(self._polygon_preview_item)
            self._polygon_preview_item = None
        self._polygon_nodes = []

    def _ensure_symbol_preview_item(self):
        if self._symbol_pixmap is None or self._pixmap_item is None:
            return
        if self._symbol_preview_item is None:
            self._symbol_preview_item = QGraphicsPixmapItem(self._symbol_pixmap)
            self._symbol_preview_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            self._symbol_preview_item.setOpacity(0.35)
            self._symbol_preview_item.setZValue(2)
            self._symbol_preview_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._scene.addItem(self._symbol_preview_item)
        else:
            self._symbol_preview_item.setPixmap(self._symbol_pixmap)

        self._symbol_preview_item.setOffset(
            -self._symbol_pixmap.width() / 2,
            -self._symbol_pixmap.height() / 2,
        )
        self._symbol_preview_item.setScale(MAP_SYMBOL_SCALE)
        self._symbol_preview_item.hide()

    def _hide_symbol_preview(self):
        if self._symbol_preview_item is not None:
            self._symbol_preview_item.hide()

    def _update_symbol_preview(self, scene_pos: QPointF):
        if self._symbol_pixmap is None:
            self._hide_symbol_preview()
            return
        self._ensure_symbol_preview_item()
        if self._symbol_preview_item is None:
            return
        self._symbol_preview_item.setPos(scene_pos)
        self._symbol_preview_item.show()

    def _place_symbol(self, scene_pos: QPointF):
        if self._symbol_pixmap is None:
            return

        item = QGraphicsPixmapItem(self._symbol_pixmap)
        item.setOffset(-self._symbol_pixmap.width() / 2, -self._symbol_pixmap.height() / 2)
        item.setPos(scene_pos)
        item.setScale(MAP_SYMBOL_SCALE)
        item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        item.setZValue(1)
        self._scene.addItem(item)
        self._ann_stack.append(item)
        self._update_symbol_preview(scene_pos)

    def _update_preview(self, cursor_pos: QPointF):
        """Redraw the ghost preview path from current nodes to cursor."""
        if not self._line_nodes:
            return
        nodes = self._line_nodes + [cursor_pos]
        path  = self._build_path_for_tool(nodes)

        if self._preview_item is None:
            self._preview_item = QGraphicsPathItem()
            preview_color = QColor(self._pen_color)
            preview_color.setAlphaF(0.35)
            pen = QPen(preview_color, self._pen_width, Qt.PenStyle.SolidLine)
            self._preview_item.setPen(pen)
            self._preview_item.setZValue(2)
            self._scene.addItem(self._preview_item)

        self._preview_item.setPath(path)

    def _update_polygon_preview(self, cursor_pos: QPointF):
        if not self._polygon_nodes:
            return

        points = self._polygon_nodes + [cursor_pos]

        if self._polygon_preview_item is None:
            self._polygon_preview_item = QGraphicsPolygonItem()
            self._polygon_preview_item.setZValue(2)
            self._polygon_preview_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._scene.addItem(self._polygon_preview_item)

        preview_pen = QPen(self._pen_color, max(1, self._pen_width), Qt.PenStyle.SolidLine)
        preview_color = QColor(self._pen_color)
        preview_color.setAlphaF(0.12)
        self._polygon_preview_item.setPen(preview_pen)
        self._polygon_preview_item.setBrush(QBrush(preview_color))
        self._polygon_preview_item.setPolygon(QPolygonF(points))
        self._polygon_preview_item.show()

    # ── Wheel: zoom ─────────────────────────────────────────────────────── #

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            min_s = self._fit_scale()
            if min_s > 0 and self.transform().m11() / 1.15 < min_s:
                return
            self.scale(1 / 1.15, 1 / 1.15)

    # ── Mouse: line / text / erase / pan ────────────────────────────────── #

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning   = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        scene_pos = self.mapToScene(event.position().toPoint())

        if self._symbol_pixmap is not None and event.button() == Qt.MouseButton.LeftButton:
            self._place_symbol(scene_pos)
            return

        if self._tool == TOOL_POLYGON:
            if event.button() == Qt.MouseButton.LeftButton:
                self._polygon_nodes.append(scene_pos)
            elif event.button() == Qt.MouseButton.RightButton:
                if len(self._polygon_nodes) == 0:
                    return
                if len(self._polygon_nodes) == 1:
                    self._cancel_polygon()
                else:
                    self._polygon_nodes.append(scene_pos)
                    self._commit_polygon()
            return

        if self._tool in LINE_TOOLS:
            if event.button() == Qt.MouseButton.LeftButton:
                # Start line or add first node
                self._line_nodes.append(scene_pos)
            elif event.button() == Qt.MouseButton.RightButton:
                if len(self._line_nodes) == 0:
                    return
                if len(self._line_nodes) == 1:
                    # Second right-click with only start: cancel
                    self._cancel_line()
                else:
                    # Add final node and commit
                    self._line_nodes.append(scene_pos)
                    self._commit_line()
            return

        if self._tool == TOOL_TEXT and event.button() == Qt.MouseButton.LeftButton:
            item = QGraphicsTextItem("Label")
            item.setPos(scene_pos)
            item.setDefaultTextColor(self._pen_color)
            item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)
            item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
            item.setZValue(1)
            self._scene.addItem(item)
            self._ann_stack.append(item)
            return

        if self._tool == TOOL_ERASE and event.button() == Qt.MouseButton.LeftButton:
            hit = self._scene.itemAt(scene_pos, self.transform())
            # Walk up to top-level group if needed
            while hit and hit.parentItem():
                hit = hit.parentItem()
            if hit and hit is not self._pixmap_item:
                self._scene.removeItem(hit)
                if hit in self._ann_stack:
                    self._ann_stack.remove(hit)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start is not None:
            delta           = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        self._update_cursor_grid_tooltip(event, scene_pos)

        if self._symbol_pixmap is not None:
            self._update_symbol_preview(scene_pos)

        if self._tool == TOOL_POLYGON and self._polygon_nodes:
            self._update_polygon_preview(scene_pos)
            return

        if self._tool in LINE_TOOLS and self._line_nodes:
            self._update_preview(scene_pos)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning   = False
            self._pan_start = None
            self.set_tool(self._tool)
            return

        if self._tool in LINE_TOOLS and len(self._line_nodes) >= 2:
            # Middle node: right-click already handled in Press; this catches
            # any remaining release events so we don't propagate them.
            pass
        elif self._tool == TOOL_POLYGON and len(self._polygon_nodes) >= 2:
            pass
        else:
            super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        QToolTip.hideText()
        self._hide_symbol_preview()
        if self._polygon_preview_item is not None:
            self._polygon_preview_item.hide()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        """Escape cancels an in-progress line."""
        if event.key() == Qt.Key.Key_Escape:
            if self._line_nodes:
                self._cancel_line()
                return
            if self._polygon_nodes:
                self._cancel_polygon()
                return
        super().keyPressEvent(event)


# --------------------------------------------------------------------------- #
#  Main window                                                                 #
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    def __init__(self, client: WarAPIClient, hexagons: list[str]):
        super().__init__()
        self.client   = client
        self.hexagons = hexagons
        self._worker: HexDataWorker | None = None
        self._active_workers: set[HexDataWorker] = set()
        self._current_hexagon: str | None = None
        self._pen_color = QColor("#ff4444")
        self._selected_symbol_key: str | None = None
        self._selected_symbol_variant: str | None = None
        self._symbol_buttons: dict[str, QToolButton] = {}
        self._variant_buttons: dict[tuple[str, str], QToolButton] = {}

        self.setWindowTitle("IGS – Foxhole Map Annotator")
        self.resize(1400, 900)
        self._apply_dark_theme()
        self._build_ui()

        if self.hexagons:
            self.hex_combo.setCurrentIndex(0)
            self._on_hex_selected(self.hex_combo.currentText())

    # ---------------------------------------------------------------------- #
    #  UI construction                                                         #
    # ---------------------------------------------------------------------- #
    def _build_ui(self):
        # ── Toolbar ──────────────────────────────────────────────────────── #
        toolbar = QToolBar("Annotation Tools")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { spacing: 4px; padding: 4px; }")
        self.addToolBar(toolbar)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        tool_defs = [
            ("Select",  TOOL_SELECT, "Select / move items  [S]"),
            ("Line",    TOOL_LINE,   "Straight line  [L]"),
            ("Arrow",   TOOL_ARROW,  "Arrow  [A]"),
            ("Zigzag",  TOOL_ZIGZAG, "Zig-zag line  [Z]"),
            ("Wave",    TOOL_WAVE,   "Wave line  [W]"),
            ("Polygon", TOOL_POLYGON, "Filled polygon  [P]"),
            ("Text",    TOOL_TEXT,   "Place text label  [T]"),
            ("Erase",   TOOL_ERASE,  "Click item to erase  [E]"),
        ]
        for i, (label, tool, tip) in enumerate(tool_defs):
            btn = QToolButton()
            btn.setText(label)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setMinimumWidth(68)
            self._tool_group.addButton(btn, i)
            toolbar.addWidget(btn)

        self._tool_group.buttons()[0].setChecked(True)
        self._tool_group.idClicked.connect(self._on_tool_selected)
        self._tools = [t for _, t, _ in tool_defs]

        toolbar.addSeparator()

        toolbar.addWidget(QLabel(" Hex: "))
        self.hex_combo = QComboBox()
        self.hex_combo.setFont(QFont("Segoe UI", 10))
        self.hex_combo.setMinimumWidth(180)
        for name in self.hexagons:
            self.hex_combo.addItem(name)
        self.hex_combo.currentTextChanged.connect(self._on_hex_selected)
        toolbar.addWidget(self.hex_combo)

        toolbar.addSeparator()

        # Color picker
        toolbar.addWidget(QLabel(" Color: "))
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(26, 26)
        self._color_btn.setToolTip("Pick annotation colour")
        self._refresh_color_btn()
        self._color_btn.clicked.connect(self._pick_color)
        toolbar.addWidget(self._color_btn)

        friendly_btn = QPushButton("Friendly")
        friendly_btn.setFont(QFont("Segoe UI", 9))
        friendly_btn.setToolTip(f"Set annotation colour to {FRIENDLY_COLOR_HEX}")
        friendly_btn.clicked.connect(
            lambda: self._set_main_color(FRIENDLY_COLOR_HEX, "Friendly")
        )
        toolbar.addWidget(friendly_btn)

        enemy_btn = QPushButton("Enemy")
        enemy_btn.setFont(QFont("Segoe UI", 9))
        enemy_btn.setToolTip(f"Set annotation colour to {ENEMY_COLOR_HEX}")
        enemy_btn.clicked.connect(
            lambda: self._set_main_color(ENEMY_COLOR_HEX, "Enemy")
        )
        toolbar.addWidget(enemy_btn)

        # Pen width
        toolbar.addWidget(QLabel("  Width: "))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 30)
        self._width_spin.setValue(3)
        self._width_spin.setFixedWidth(55)
        self._width_spin.valueChanged.connect(lambda v: self.canvas.set_pen_width(v))
        toolbar.addWidget(self._width_spin)

        toolbar.addSeparator()

        # Zoom controls
        for label, tip, fn in [
            ("+ Zoom In",  "Zoom in  [Ctrl++]",  lambda: self.canvas.zoom_in()),
            ("- Zoom Out", "Zoom out  [Ctrl+-]", lambda: self.canvas.zoom_out()),
            ("Fit",        "Fit to window",       lambda: self.canvas.zoom_reset()),
        ]:
            btn = QPushButton(label)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setToolTip(tip)
            btn.clicked.connect(fn)
            toolbar.addWidget(btn)

        toolbar.addSeparator()

        # Undo / Clear
        undo_btn = QPushButton("Undo")
        undo_btn.setFont(QFont("Segoe UI", 10))
        undo_btn.setToolTip("Undo last annotation  [Ctrl+Z]")
        undo_btn.clicked.connect(lambda: self.canvas.undo_last())
        toolbar.addWidget(undo_btn)

        clear_btn = QPushButton("Clear All")
        clear_btn.setFont(QFont("Segoe UI", 10))
        clear_btn.setToolTip("Remove all annotations")
        clear_btn.clicked.connect(lambda: self.canvas.clear_annotations())
        toolbar.addWidget(clear_btn)

        # ── Keyboard shortcuts ───────────────────────────────────────────── #
        QShortcut(QKeySequence("S"),                    self, lambda: self._on_tool_selected(0))
        QShortcut(QKeySequence("L"),                    self, lambda: self._on_tool_selected(1))
        QShortcut(QKeySequence("A"),                    self, lambda: self._on_tool_selected(2))
        QShortcut(QKeySequence("Z"),                    self, lambda: self._on_tool_selected(3))
        QShortcut(QKeySequence("W"),                    self, lambda: self._on_tool_selected(4))
        QShortcut(QKeySequence("P"),                    self, lambda: self._on_tool_selected(5))
        QShortcut(QKeySequence("T"),                    self, lambda: self._on_tool_selected(6))
        QShortcut(QKeySequence("E"),                    self, lambda: self._on_tool_selected(7))
        QShortcut(QKeySequence("Escape"),               self, lambda: self.canvas._cancel_line())
        QShortcut(QKeySequence.StandardKey.ZoomIn,      self, lambda: self.canvas.zoom_in())
        QShortcut(QKeySequence.StandardKey.ZoomOut,     self, lambda: self.canvas.zoom_out())
        QShortcut(QKeySequence.StandardKey.Undo,        self, lambda: self.canvas.undo_last())

        # ── Central layout ───────────────────────────────────────────────── #
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── Left panel ───────────────────────────────────────────────────── #
        left = QWidget()
        left.setFixedWidth(300)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        palette_label = QLabel("Symbol Palette")
        palette_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        left_layout.addWidget(palette_label)

        help_label = QLabel("Use the arrow beside a symbol to open its variants, then choose Friendly or Enemy.")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #a6adc8;")
        left_layout.addWidget(help_label)

        self._symbol_button_group = QButtonGroup(self)
        self._symbol_button_group.setExclusive(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        for symbol in SYMBOLS:
            section = self._build_symbol_section(symbol)
            scroll_layout.addWidget(section)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll, stretch=1)

        root.addWidget(left)

        # ── Canvas ───────────────────────────────────────────────────────── #
        self.canvas = AnnotationView()
        root.addWidget(self.canvas, stretch=1)

        # ── Status bar ───────────────────────────────────────────────────── #
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._map_info_label = QLabel("Map info: —")
        self.status_bar.addPermanentWidget(self._map_info_label)
        self.status_bar.showMessage("Ready — select a hexagon")
        self._refresh_symbol_palette()

    def _build_symbol_section(self, symbol: dict) -> QWidget:
        section = QFrame()
        section.setFrameShape(QFrame.Shape.StyledPanel)
        section.setStyleSheet(
            "QFrame { border: 1px solid #45475a; border-radius: 6px; background: #181825; }"
            "QToolButton { border: none; padding: 6px; }"
        )

        layout = QVBoxLayout(section)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(4)

        header = QToolButton()
        header.setText(symbol["label"])
        header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        header.setIconSize(QSize(28, 28))
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.setStyleSheet("text-align: left; color: #cdd6f4;")
        header.setEnabled(False)
        self._symbol_buttons[symbol["key"]] = header
        header_row.addWidget(header, stretch=1)

        toggle = QToolButton()
        toggle.setCheckable(True)
        toggle.setChecked(False)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        header_row.addWidget(toggle)
        layout.addLayout(header_row)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        for variant_label, variant_key in [("Friendly", "friendly"), ("Enemy", "enemy")]:
            button = QToolButton()
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(36, 36))
            button.setMinimumSize(88, 74)
            button.setText(variant_label)
            button.setProperty("symbol_key", symbol["key"])
            button.setProperty("variant_key", variant_key)
            button.clicked.connect(self._on_symbol_button_clicked)
            self._symbol_button_group.addButton(button)
            self._variant_buttons[(symbol["key"], variant_key)] = button
            content_layout.addWidget(button)

        content_layout.addStretch()
        content.setVisible(False)

        layout.addWidget(content)

        def toggle_section(expanded: bool, panel=content, button=toggle):
            panel.setVisible(expanded)
            button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)

        toggle.toggled.connect(toggle_section)
        return section

    # ---------------------------------------------------------------------- #
    #  Toolbar helpers                                                         #
    # ---------------------------------------------------------------------- #
    def _on_tool_selected(self, index: int):
        if 0 <= index < len(self._tools):
            self._clear_symbol_selection()
            self._tool_group.button(index).setChecked(True)
            tool = self._tools[index]
            self.canvas.set_tool(tool)
            if tool in LINE_TOOLS:
                self.status_bar.showMessage(
                    "Left-click to add node  •  Right-click to finish line  •  Esc to cancel"
                )
            elif tool == TOOL_POLYGON:
                self.status_bar.showMessage(
                    "Left-click to add polygon points  •  Right-click to fill polygon  •  Esc to cancel"
                )
            elif tool == TOOL_TEXT:
                self.status_bar.showMessage("Left-click on the map to place a text label")
            elif tool == TOOL_ERASE:
                self.status_bar.showMessage("Left-click an annotation item to erase it")
            else:
                self.status_bar.showMessage("Left-click to select / drag items")

    def _pick_color(self):
        color = QColorDialog.getColor(self._pen_color, self, "Pick Annotation Colour")
        if color.isValid():
            self._pen_color = color
            self._refresh_color_btn()
            self.canvas.set_pen_color(color)

    def _set_main_color(self, color_hex: str, label: str):
        color = QColor(color_hex)
        if not color.isValid():
            return
        self._pen_color = color
        self._refresh_color_btn()
        self.canvas.set_pen_color(color)
        self.status_bar.showMessage(f"{label} colour selected ({color_hex})")

    def _refresh_color_btn(self):
        self._color_btn.setStyleSheet(
            f"background-color: {self._pen_color.name()};"
            f"border: 2px solid #888; border-radius: 4px;"
        )

    def _symbol_variant_path(self, symbol: dict, iff: str) -> str | None:
        filename = symbol.get(iff)
        if not filename:
            return None
        path = os.path.join(ANNOT_ASSETS_DIR, filename)
        return path if os.path.exists(path) else None

    def _refresh_symbol_palette(self):
        for symbol in SYMBOLS:
            header = self._symbol_buttons.get(symbol["key"])
            if header is not None:
                preview_path = self._symbol_variant_path(symbol, "friendly") or self._symbol_variant_path(symbol, "enemy")
                header.setIcon(QIcon(preview_path) if preview_path else QIcon())
                header.setToolTip(symbol["label"])

            for variant_key, variant_label in (("friendly", "Friendly"), ("enemy", "Enemy")):
                button = self._variant_buttons.get((symbol["key"], variant_key))
                if button is None:
                    continue

                path = self._symbol_variant_path(symbol, variant_key)
                button.setIcon(QIcon(path) if path else QIcon())
                button.setEnabled(path is not None)
                button.setToolTip(
                    f"{variant_label} {symbol['label']}" if path else f"{variant_label} {symbol['label']} unavailable"
                )

        if self._selected_symbol_key and self._selected_symbol_variant:
            symbol = self._symbol_definition(self._selected_symbol_key)
            path = self._symbol_variant_path(symbol, self._selected_symbol_variant) if symbol else None
            if symbol and path:
                self.canvas.set_symbol_stamp(symbol["label"], QPixmap(path))
                self.status_bar.showMessage(
                    f"Stamping {self._selected_symbol_variant} {symbol['label']} symbols"
                )
            else:
                self._clear_symbol_selection()

    def _symbol_definition(self, key: str) -> dict | None:
        for symbol in SYMBOLS:
            if symbol["key"] == key:
                return symbol
        return None

    def _clear_symbol_selection(self):
        self._selected_symbol_key = None
        self._selected_symbol_variant = None
        self.canvas.clear_symbol_stamp()
        self._symbol_button_group.setExclusive(False)
        for button in self._variant_buttons.values():
            button.setChecked(False)
        self._symbol_button_group.setExclusive(True)

    def _on_symbol_button_clicked(self, checked: bool):
        button = self.sender()
        if not isinstance(button, QToolButton):
            return

        symbol_key = button.property("symbol_key")
        variant_key = button.property("variant_key")
        symbol = self._symbol_definition(symbol_key)
        if not checked or symbol is None:
            self._clear_symbol_selection()
            return

        path = self._symbol_variant_path(symbol, variant_key)
        if path is None:
            button.setChecked(False)
            self.status_bar.showMessage(
                f"No {variant_key} icon available for {symbol['label']}"
            )
            return

        self._selected_symbol_key = symbol_key
        self._selected_symbol_variant = variant_key
        self.canvas.set_symbol_stamp(symbol["label"], QPixmap(path))
        self.status_bar.showMessage(
            f"Stamping {variant_key} {symbol['label']} symbols"
        )

    # ---------------------------------------------------------------------- #
    #  Event handlers                                                          #
    # ---------------------------------------------------------------------- #
    def _on_hex_selected(self, hexagon: str):
        if not hexagon:
            return

        self._current_hexagon = hexagon
        self.setWindowTitle(f"IGS – {hexagon}")
        self._clear_info_box()
        self.status_bar.showMessage(f"Loading {hexagon}…")

        img_path = os.path.join(ASSETS_DIR, f"{hexagon}.png")
        if os.path.exists(img_path):
            self.canvas.load_image(img_path)
        else:
            self.canvas.clear_image()
            self.status_bar.showMessage(f"{hexagon} — no local image available")

        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()

        worker = HexDataWorker(self.client, hexagon)
        worker.data_ready.connect(self._on_data_ready)
        worker.error.connect(self._on_data_error)
        worker.finished.connect(lambda worker=worker: self._on_worker_finished(worker))
        self._active_workers.add(worker)
        self._worker = worker
        worker.start()

    def _on_data_ready(self, hexagon: str, dynamic: dict, war_report: dict):
        if hexagon != self._current_hexagon:
            return
        # colonialCasualties / wardenCasualties fetched but not shown per requirements
        self.status_bar.showMessage(f"{hexagon} — ready")
        self._populate_info_box({
            "Day of War":   war_report.get("dayOfWar", "—"),
            "Map Items":    len(dynamic.get("mapItems", [])),
            "Text Items":   len(dynamic.get("mapTextItems", [])),
            "Last Updated": dynamic.get("lastUpdated", "—"),
        })

    def _on_data_error(self, hexagon: str, message: str):
        if hexagon != self._current_hexagon:
            return
        self.status_bar.showMessage(f"API error: {message}")

    def _on_worker_finished(self, worker: HexDataWorker):
        self._active_workers.discard(worker)
        if self._worker is worker:
            self._worker = None
        worker.deleteLater()

    # ---------------------------------------------------------------------- #
    #  Info box helpers                                                        #
    # ---------------------------------------------------------------------- #
    def _clear_info_box(self):
        self._map_info_label.setText("Map info: —")

    def _populate_info_box(self, data: dict):
        summary = "  |  ".join(f"{key}: {value}" for key, value in data.items())
        self._map_info_label.setText(f"Map info: {summary}")

    # ---------------------------------------------------------------------- #
    #  Theme                                                                   #
    # ---------------------------------------------------------------------- #
    def _apply_dark_theme(self):
        palette = QPalette()
        bg      = QColor("#1e1e2e")
        surface = QColor("#2a2a3e")
        text    = QColor("#cdd6f4")
        accent  = QColor("#89b4fa")
        muted   = QColor("#6c7086")

        palette.setColor(QPalette.ColorRole.Window,          bg)
        palette.setColor(QPalette.ColorRole.WindowText,      text)
        palette.setColor(QPalette.ColorRole.Base,            surface)
        palette.setColor(QPalette.ColorRole.AlternateBase,   bg)
        palette.setColor(QPalette.ColorRole.Text,            text)
        palette.setColor(QPalette.ColorRole.Button,          surface)
        palette.setColor(QPalette.ColorRole.ButtonText,      text)
        palette.setColor(QPalette.ColorRole.Highlight,       accent)
        palette.setColor(QPalette.ColorRole.HighlightedText, bg)
        palette.setColor(QPalette.ColorRole.PlaceholderText, muted)
        QApplication.setPalette(palette)


# --------------------------------------------------------------------------- #
#  Entry point                                                                 #
# --------------------------------------------------------------------------- #
def launch():
    client   = WarAPIClient()
    hexagons = client.get_maps()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow(client, hexagons)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
