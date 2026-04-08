import os
import sys
import subprocess

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
    QPainter, QKeySequence, QShortcut, QBrush, QPolygonF, QImage, QFontMetrics,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QComboBox, QLabel, QFrame, QGridLayout, QStatusBar,
    QToolBar, QToolButton, QButtonGroup, QPushButton, QSpinBox,
    QColorDialog, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem,
    QGraphicsItemGroup, QScrollArea, QToolTip, QFileDialog, QMessageBox,
)


def _resource_root() -> str:
    # PyInstaller one-folder/one-file builds expose files through _MEIPASS.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return str(getattr(sys, "_MEIPASS"))
    return os.path.dirname(__file__)


RESOURCE_ROOT = _resource_root()
ASSETS_DIR = os.path.join(RESOURCE_ROOT, "assets")
ANNOT_ASSETS_DIR = os.path.join(RESOURCE_ROOT, "Annotassets")
APP_ICON_PATH = os.path.join(ASSETS_DIR, "IGS.png")
BASE_URL   = "https://war-service-live.foxholeservices.com/api"
REPO_URL = "https://github.com/ATLAStheactualtitan/IGSCode"
REPO_COMMITS_API = "https://api.github.com/repos/ATLAStheactualtitan/IGSCode/commits/main"

TOOL_SELECT   = "select"
TOOL_LINE     = "line"
TOOL_ARROW    = "arrow"
TOOL_ZIGZAG   = "zigzag"
TOOL_WAVE     = "wave"
TOOL_POLYGON  = "polygon"
TOOL_CIRCLE   = "circle"
TOOL_RULER    = "ruler"
TOOL_TEXT     = "text"
TOOL_ERASE    = "erase"

LINE_TOOLS = {TOOL_LINE, TOOL_ARROW, TOOL_ZIGZAG, TOOL_WAVE}
LINE_TOOL_LABELS = {
    TOOL_LINE: "Line",
    TOOL_ARROW: "Arrow",
    TOOL_ZIGZAG: "Tank line",
    TOOL_WAVE: "Infantry line",
}
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
    {"key": "VP", "label": "VP", "friendly": "F_VP.png", "enemy": "VP.png"},
]

SYMBOL_CATEGORY_ORDER = [
    "Pill and 30mm AT",
    "B and Gar",
    "Bases",
    "Emplaced",
    "Misc",
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


def _local_git_commit(repo_dir: str) -> str | None:
    """Return local HEAD commit hash if this app is running from a git checkout."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_dir, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        commit = result.stdout.strip()
        return commit if commit else None
    except Exception:
        return None


def _latest_repo_commit() -> tuple[str | None, str | None]:
    """Return latest remote commit hash and URL from GitHub."""
    try:
        response = requests.get(REPO_COMMITS_API, timeout=4)
        response.raise_for_status()
        data = response.json() if response.content else {}
        if not isinstance(data, dict):
            return None, None
        sha = data.get("sha")
        html_url = data.get("html_url") or REPO_URL
        if isinstance(sha, str) and sha:
            return sha, html_url if isinstance(html_url, str) else REPO_URL
        return None, None
    except Exception:
        return None, None


def check_for_new_version(repo_dir: str) -> dict:
    """Compare local commit with GitHub HEAD and report update availability."""
    local_sha = _local_git_commit(repo_dir)
    remote_sha, remote_url = _latest_repo_commit()

    if remote_sha is None:
        return {
            "status": "unavailable",
            "message": "Update check unavailable",
        }

    if local_sha is None:
        return {
            "status": "unknown-local",
            "message": "Cannot determine local version",
            "remote_sha": remote_sha,
            "remote_url": remote_url or REPO_URL,
        }

    if local_sha != remote_sha:
        return {
            "status": "update-available",
            "message": "A newer version is available on GitHub",
            "local_sha": local_sha,
            "remote_sha": remote_sha,
            "remote_url": remote_url or REPO_URL,
        }

    return {
        "status": "up-to-date",
        "message": "You are running the latest version",
        "local_sha": local_sha,
        "remote_sha": remote_sha,
    }


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
        self._text_size  = 12
        self._symbol_name: str | None = None
        self._symbol_pixmap: QPixmap | None = None
        self._symbol_preview_item: QGraphicsPixmapItem | None = None
        self._ann_stack: list = []  # undo history

        # Node-based line drawing state
        self._line_nodes: list[QPointF] = []   # confirmed nodes
        self._polygon_nodes: list[QPointF] = []
        self._circle_center: QPointF | None = None
        self._preview_item: QGraphicsPathItem | None = None  # live preview
        self._polygon_preview_item: QGraphicsPolygonItem | None = None
        self._circle_preview_item: QGraphicsEllipseItem | None = None
        self._ruler_origin: QPointF | None = None
        self._ruler_line_item: QGraphicsPathItem | None = None
        self._ruler_text_item: QGraphicsTextItem | None = None

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
        if self._circle_center is not None and tool != self._tool:
            self._cancel_circle()
        if self._ruler_origin is not None and tool != self._tool:
            self._clear_ruler()
        self._tool = tool
        cursor_map = {
            TOOL_SELECT: Qt.CursorShape.ArrowCursor,
            TOOL_LINE:   Qt.CursorShape.CrossCursor,
            TOOL_ARROW:  Qt.CursorShape.CrossCursor,
            TOOL_ZIGZAG: Qt.CursorShape.CrossCursor,
            TOOL_WAVE:   Qt.CursorShape.CrossCursor,
            TOOL_POLYGON: Qt.CursorShape.CrossCursor,
            TOOL_CIRCLE: Qt.CursorShape.CrossCursor,
            TOOL_RULER: Qt.CursorShape.CrossCursor,
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

    def set_text_size(self, size: int):
        self._text_size = max(1, size)

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
        self._circle_center = None
        self._preview_item = None
        self._polygon_preview_item = None
        self._circle_preview_item = None
        self._ruler_origin = None
        self._ruler_line_item = None
        self._ruler_text_item = None
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
        self._circle_center = None
        self._preview_item = None
        self._polygon_preview_item = None
        self._circle_preview_item = None
        self._ruler_origin = None
        self._ruler_line_item = None
        self._ruler_text_item = None
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
        self._circle_center = None
        self._preview_item = None
        self._polygon_preview_item = None
        self._circle_preview_item = None
        self._ruler_origin = None
        self._ruler_line_item = None
        self._ruler_text_item = None
        self._symbol_preview_item = None
        if self._symbol_pixmap is not None:
            self._ensure_symbol_preview_item()

    def cancel_active_drawing(self):
        if self._line_nodes:
            self._cancel_line()
            return
        if self._polygon_nodes:
            self._cancel_polygon()
            return
        if self._circle_center is not None:
            self._cancel_circle()
            return
        if self._ruler_origin is not None:
            self._clear_ruler()

    def _clear_ruler(self):
        self._ruler_origin = None
        if self._ruler_line_item is not None:
            self._scene.removeItem(self._ruler_line_item)
            self._ruler_line_item = None
        if self._ruler_text_item is not None:
            self._scene.removeItem(self._ruler_text_item)
            self._ruler_text_item = None

    def _set_ruler_origin(self, origin: QPointF):
        self._clear_ruler()
        self._ruler_origin = origin

    def _ruler_distance_and_azimuth(self, current: QPointF) -> tuple[float, float]:
        if self._ruler_origin is None:
            return 0.0, 0.0

        dx = current.x() - self._ruler_origin.x()
        dy = current.y() - self._ruler_origin.y()

        spec = self._grid_spec()
        if spec is None:
            dist_m = 0.0
        else:
            _, _, col_w, row_h = spec
            meters_per_px_x = 125.0 / col_w if col_w > 0 else 0.0
            meters_per_px_y = 125.0 / row_h if row_h > 0 else 0.0
            dist_m = math.hypot(dx * meters_per_px_x, dy * meters_per_px_y)

        azimuth = math.degrees(math.atan2(dx, -dy))
        if azimuth < 0:
            azimuth += 360.0
        return dist_m, azimuth

    def _update_ruler_preview(self, cursor_pos: QPointF):
        if self._ruler_origin is None:
            return

        path = QPainterPath(self._ruler_origin)
        path.lineTo(cursor_pos)
        if self._ruler_line_item is None:
            self._ruler_line_item = QGraphicsPathItem()
            ruler_color = QColor("#f5c542")
            self._ruler_line_item.setPen(QPen(ruler_color, max(1, self._pen_width), Qt.PenStyle.DashLine))
            self._ruler_line_item.setZValue(2)
            self._ruler_line_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._scene.addItem(self._ruler_line_item)
        self._ruler_line_item.setPath(path)
        self._ruler_line_item.show()

        dist_m, azimuth = self._ruler_distance_and_azimuth(cursor_pos)
        text = f"{dist_m:.1f} m | {azimuth:.1f}°"

        if self._ruler_text_item is None:
            self._ruler_text_item = QGraphicsTextItem()
            self._ruler_text_item.setDefaultTextColor(QColor("#f2f7ff"))
            self._ruler_text_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self._ruler_text_item.setZValue(3)
            self._ruler_text_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._scene.addItem(self._ruler_text_item)

        self._ruler_text_item.setPlainText(text)
        self._ruler_text_item.setPos(cursor_pos + QPointF(12.0, -28.0))
        self._ruler_text_item.show()

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
        group.setData(0, "line_tool")
        group.setData(1, LINE_TOOL_LABELS.get(self._tool, "Line"))

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

    def _update_circle_preview(self, cursor_pos: QPointF):
        if self._circle_center is None:
            return

        radius = math.hypot(cursor_pos.x() - self._circle_center.x(), cursor_pos.y() - self._circle_center.y())
        rect = QRectF(
            self._circle_center.x() - radius,
            self._circle_center.y() - radius,
            radius * 2.0,
            radius * 2.0,
        )

        if self._circle_preview_item is None:
            self._circle_preview_item = QGraphicsEllipseItem()
            self._circle_preview_item.setZValue(2)
            self._circle_preview_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self._scene.addItem(self._circle_preview_item)

        preview_pen = QPen(self._pen_color, max(1, self._pen_width), Qt.PenStyle.SolidLine)
        preview_fill = QColor(self._pen_color)
        preview_fill.setAlphaF(0.12)
        self._circle_preview_item.setPen(preview_pen)
        self._circle_preview_item.setBrush(QBrush(preview_fill))
        self._circle_preview_item.setRect(rect)
        self._circle_preview_item.show()

    def _commit_circle(self, edge_pos: QPointF):
        if self._circle_center is None:
            return

        radius = math.hypot(edge_pos.x() - self._circle_center.x(), edge_pos.y() - self._circle_center.y())
        if radius < 1.0:
            self._cancel_circle()
            return

        if self._circle_preview_item:
            self._scene.removeItem(self._circle_preview_item)
            self._circle_preview_item = None

        circle_item = QGraphicsEllipseItem(
            self._circle_center.x() - radius,
            self._circle_center.y() - radius,
            radius * 2.0,
            radius * 2.0,
        )
        circle_item.setPen(self._make_pen())
        fill_color = QColor(self._pen_color)
        fill_color.setAlphaF(0.2)
        circle_item.setBrush(QBrush(fill_color))
        circle_item.setZValue(1)
        circle_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        circle_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self._scene.addItem(circle_item)
        self._ann_stack.append(circle_item)
        self._circle_center = None

    def _cancel_circle(self):
        if self._circle_preview_item:
            self._scene.removeItem(self._circle_preview_item)
            self._circle_preview_item = None
        self._circle_center = None

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
        item.setData(0, "symbol")
        item.setData(1, self._symbol_name or "Symbol")
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

        if self._tool == TOOL_CIRCLE:
            if event.button() == Qt.MouseButton.LeftButton:
                if self._circle_center is None:
                    self._circle_center = scene_pos
                else:
                    self._commit_circle(scene_pos)
            elif event.button() == Qt.MouseButton.RightButton:
                self._cancel_circle()
            return

        if self._tool == TOOL_RULER:
            if event.button() == Qt.MouseButton.LeftButton:
                self._set_ruler_origin(scene_pos)
                self._update_ruler_preview(scene_pos)
            elif event.button() == Qt.MouseButton.RightButton:
                self._clear_ruler()
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
            item.setFont(QFont("Segoe UI", self._text_size, QFont.Weight.Bold))
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

        if self._tool == TOOL_CIRCLE and self._circle_center is not None:
            self._update_circle_preview(scene_pos)
            return

        if self._tool == TOOL_RULER and self._ruler_origin is not None:
            self._update_ruler_preview(scene_pos)
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
        elif self._tool == TOOL_CIRCLE and self._circle_center is not None:
            pass
        elif self._tool == TOOL_RULER and self._ruler_origin is not None:
            pass
        else:
            super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        QToolTip.hideText()
        self._hide_symbol_preview()
        if self._polygon_preview_item is not None:
            self._polygon_preview_item.hide()
        if self._circle_preview_item is not None:
            self._circle_preview_item.hide()
        if self._ruler_line_item is not None:
            self._ruler_line_item.hide()
        if self._ruler_text_item is not None:
            self._ruler_text_item.hide()
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
            if self._circle_center is not None:
                self._cancel_circle()
                return
            if self._ruler_origin is not None:
                self._clear_ruler()
                return
        super().keyPressEvent(event)


class HoverRevealRibbon(QFrame):
    def __init__(self):
        super().__init__()
        self._secondary_row: QWidget | None = None
        self.setMouseTracking(True)

    def set_secondary_row(self, row: QWidget):
        self._secondary_row = row
        self._secondary_row.setVisible(False)

    def enterEvent(self, event):
        if self._secondary_row is not None:
            self._secondary_row.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._secondary_row is not None:
            self._secondary_row.setVisible(False)
        super().leaveEvent(event)


# --------------------------------------------------------------------------- #
#  Main window                                                                 #
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    def __init__(self, client: WarAPIClient, hexagons: list[str], war_number: str = "—"):
        super().__init__()
        self.client   = client
        self.hexagons = hexagons
        self._war_number = str(war_number) if war_number is not None else "—"
        self._worker: HexDataWorker | None = None
        self._active_workers: set[HexDataWorker] = set()
        self._current_hexagon: str | None = None
        self._pen_color = QColor("#ff4444")
        self._selected_symbol_key: str | None = None
        self._selected_symbol_variant: str | None = None
        self._symbol_buttons: dict[str, QToolButton] = {}
        self._variant_buttons: dict[tuple[str, str], QToolButton] = {}

        self.setWindowTitle("IGS – Foxhole Map Annotator")
        if os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))
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
        # ── Top ribbon ───────────────────────────────────────────────────── #
        ribbon = HoverRevealRibbon()
        ribbon.setObjectName("topRibbon")
        ribbon.setStyleSheet(
            "QFrame#topRibbon { background: #1a1f33; border-bottom: 1px solid #3b4666; }"
            "QPushButton, QToolButton, QComboBox, QSpinBox { margin: 0px 2px; }"
        )

        ribbon_layout = QVBoxLayout(ribbon)
        ribbon_layout.setContentsMargins(8, 6, 8, 6)
        ribbon_layout.setSpacing(6)

        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(4)

        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(4)

        def add_divider(layout: QHBoxLayout):
            divider = QFrame()
            divider.setFrameShape(QFrame.Shape.VLine)
            divider.setFrameShadow(QFrame.Shadow.Plain)
            divider.setStyleSheet("color: #46506e;")
            layout.addWidget(divider)

        ribbon_layout.addWidget(row1)
        ribbon_layout.addWidget(row2)
        ribbon.set_secondary_row(row2)
        self.setMenuWidget(ribbon)

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        tool_defs = [
            ("Select",  TOOL_SELECT, "Select / move items  [S]"),
            ("Line",    TOOL_LINE,   "Straight line  [L]"),
            ("Arrow",   TOOL_ARROW,  "Arrow  [A]"),
            ("Tank",    TOOL_ZIGZAG, "Tank line  [Z]"),
            ("Inf",     TOOL_WAVE,   "Infantry line  [W]"),
            ("Polygon", TOOL_POLYGON, "Filled polygon  [P]"),
            ("Circle",  TOOL_CIRCLE, "Filled circle  [C]"),
            ("Ruler",   TOOL_RULER,  "Measure distance and azimuth  [R]"),
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
            row1_layout.addWidget(btn)

        self._tool_group.buttons()[0].setChecked(True)
        self._tool_group.idClicked.connect(self._on_tool_selected)
        self._tools = [t for _, t, _ in tool_defs]

        add_divider(row1_layout)

        row1_layout.addWidget(QLabel(" Hex: "))
        self.hex_combo = QComboBox()
        self.hex_combo.setFont(QFont("Segoe UI", 10))
        self.hex_combo.setMinimumWidth(180)
        for name in sorted(self.hexagons, key=str.casefold):
            self.hex_combo.addItem(name)
        self.hex_combo.currentTextChanged.connect(self._on_hex_selected)
        row1_layout.addWidget(self.hex_combo)

        add_divider(row1_layout)

        # Color picker
        row1_layout.addWidget(QLabel(" Color: "))
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(26, 26)
        self._color_btn.setToolTip("Pick annotation colour")
        self._refresh_color_btn()
        self._color_btn.clicked.connect(self._pick_color)
        row1_layout.addWidget(self._color_btn)

        friendly_btn = QPushButton("Friendly")
        friendly_btn.setFont(QFont("Segoe UI", 9))
        friendly_btn.setToolTip(f"Set annotation colour to {FRIENDLY_COLOR_HEX}")
        friendly_btn.clicked.connect(
            lambda: self._set_main_color(FRIENDLY_COLOR_HEX, "Friendly")
        )
        row1_layout.addWidget(friendly_btn)

        enemy_btn = QPushButton("Enemy")
        enemy_btn.setFont(QFont("Segoe UI", 9))
        enemy_btn.setToolTip(f"Set annotation colour to {ENEMY_COLOR_HEX}")
        enemy_btn.clicked.connect(
            lambda: self._set_main_color(ENEMY_COLOR_HEX, "Enemy")
        )
        row1_layout.addWidget(enemy_btn)

        row1_layout.addStretch(1)

        # Pen width
        row2_layout.addWidget(QLabel(" Width: "))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 30)
        self._width_spin.setValue(3)
        self._width_spin.setFixedWidth(55)
        self._width_spin.valueChanged.connect(lambda v: self.canvas.set_pen_width(v))
        row2_layout.addWidget(self._width_spin)

        # Text size
        row2_layout.addWidget(QLabel(" Text: "))
        self._text_size_spin = QSpinBox()
        self._text_size_spin.setRange(1, 96)
        self._text_size_spin.setValue(12)
        self._text_size_spin.setFixedWidth(60)
        self._text_size_spin.setToolTip("Text label size")
        self._text_size_spin.valueChanged.connect(lambda v: self.canvas.set_text_size(v))
        row2_layout.addWidget(self._text_size_spin)

        add_divider(row2_layout)

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
            row2_layout.addWidget(btn)

        add_divider(row2_layout)

        # Undo / Clear
        undo_btn = QPushButton("Undo")
        undo_btn.setFont(QFont("Segoe UI", 10))
        undo_btn.setToolTip("Undo last annotation  [Ctrl+Z]")
        undo_btn.clicked.connect(lambda: self.canvas.undo_last())
        row2_layout.addWidget(undo_btn)

        clear_btn = QPushButton("Clear All")
        clear_btn.setFont(QFont("Segoe UI", 10))
        clear_btn.setToolTip("Remove all annotations")
        clear_btn.clicked.connect(lambda: self.canvas.clear_annotations())
        row2_layout.addWidget(clear_btn)

        export_btn = QPushButton("Export PNG")
        export_btn.setFont(QFont("Segoe UI", 10))
        export_btn.setToolTip("Export current visible area with legend")
        export_btn.clicked.connect(self._export_visible_png)
        row2_layout.addWidget(export_btn)

        row2_layout.addStretch(1)

        # ── Keyboard shortcuts ───────────────────────────────────────────── #
        QShortcut(QKeySequence("S"),                    self, lambda: self._on_tool_selected(0))
        QShortcut(QKeySequence("L"),                    self, lambda: self._on_tool_selected(1))
        QShortcut(QKeySequence("A"),                    self, lambda: self._on_tool_selected(2))
        QShortcut(QKeySequence("Z"),                    self, lambda: self._on_tool_selected(3))
        QShortcut(QKeySequence("W"),                    self, lambda: self._on_tool_selected(4))
        QShortcut(QKeySequence("P"),                    self, lambda: self._on_tool_selected(5))
        QShortcut(QKeySequence("C"),                    self, lambda: self._on_tool_selected(6))
        QShortcut(QKeySequence("R"),                    self, lambda: self._on_tool_selected(7))
        QShortcut(QKeySequence("T"),                    self, lambda: self._on_tool_selected(8))
        QShortcut(QKeySequence("E"),                    self, lambda: self._on_tool_selected(9))
        QShortcut(QKeySequence("Escape"),               self, lambda: self.canvas.cancel_active_drawing())
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

        help_label = QLabel("Pick a category, then choose Friendly (F) or Enemy (E) for the symbol you want to stamp.")
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
        scroll_layout.setSpacing(10)

        grouped_symbols: dict[str, list[dict]] = {name: [] for name in SYMBOL_CATEGORY_ORDER}
        for symbol in SYMBOLS:
            grouped_symbols[self._symbol_category(symbol)].append(symbol)

        for category in SYMBOL_CATEGORY_ORDER:
            symbols = grouped_symbols.get(category, [])
            if not symbols:
                continue

            group_frame = QFrame()
            group_frame.setFrameShape(QFrame.Shape.StyledPanel)
            group_frame.setStyleSheet(
                "QFrame { border: 1px solid #45475a; border-radius: 8px; background: #181825; }"
            )
            group_layout = QVBoxLayout(group_frame)
            group_layout.setContentsMargins(8, 8, 8, 8)
            group_layout.setSpacing(8)

            group_title = QLabel(category)
            group_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            group_title.setStyleSheet("color: #cdd6f4;")
            group_layout.addWidget(group_title)

            tile_grid = QGridLayout()
            tile_grid.setContentsMargins(0, 0, 0, 0)
            tile_grid.setHorizontalSpacing(8)
            tile_grid.setVerticalSpacing(8)

            columns = 2
            for idx, symbol in enumerate(symbols):
                row = idx // columns
                col = idx % columns
                tile_grid.addWidget(self._build_symbol_section(symbol), row, col)

            group_layout.addLayout(tile_grid)
            scroll_layout.addWidget(group_frame)

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

    def _symbol_category(self, symbol: dict) -> str:
        key = symbol.get("key", "")
        if key in {"BB", "VP"} or key.startswith("Rel_B_"):
            return "Bases"
        if key in {"AA", "Empl_Anti_inf", "Empl_AT"}:
            return "Emplaced"
        if key in {"AT_Pill", "AT_Pill_30mm"} or "Pill" in key:
            return "Pill and 30mm AT"
        if key.endswith("_B") or "_Gar" in key:
            return "B and Gar"
        return "Misc"

    def _build_symbol_section(self, symbol: dict) -> QWidget:
        section = QFrame()
        section.setFrameShape(QFrame.Shape.StyledPanel)
        section.setStyleSheet(
            "QFrame { border: 1px solid #585b70; border-radius: 8px; background: #11111b; }"
        )

        layout = QVBoxLayout(section)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        preview = QToolButton()
        preview.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        preview.setIconSize(QSize(54, 54))
        preview.setFixedSize(86, 86)
        preview.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        preview.setStyleSheet(
            "QToolButton { border: 1px solid #6c7086; border-radius: 6px; background: #313244; padding: 4px; }"
        )
        self._symbol_buttons[symbol["key"]] = preview
        layout.addWidget(preview, alignment=Qt.AlignmentFlag.AlignHCenter)

        name = QLabel(symbol["label"])
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        name.setStyleSheet("color: #cdd6f4;")
        name.setMinimumHeight(28)
        layout.addWidget(name)

        variant_row = QHBoxLayout()
        variant_row.setContentsMargins(0, 0, 0, 0)
        variant_row.setSpacing(6)

        for variant_label, variant_key, short_label in [
            ("Friendly", "friendly", "F"),
            ("Enemy", "enemy", "E"),
        ]:
            button = QToolButton()
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(28, 28))
            button.setFixedSize(38, 54)
            button.setText(short_label)
            button.setProperty("symbol_key", symbol["key"])
            button.setProperty("variant_key", variant_key)
            button.clicked.connect(self._on_symbol_button_clicked)
            self._symbol_button_group.addButton(button)
            self._variant_buttons[(symbol["key"], variant_key)] = button
            variant_row.addWidget(button)

        layout.addLayout(variant_row)
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
            elif tool == TOOL_CIRCLE:
                self.status_bar.showMessage(
                    "Left-click center, move mouse, then left-click edge to fill circle  •  Right-click/Esc to cancel"
                )
            elif tool == TOOL_RULER:
                self.status_bar.showMessage(
                    "Left-click to set ruler origin  •  Move to read distance/azimuth  •  Right-click/Esc to clear"
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
                is_selected_symbol = symbol["key"] == self._selected_symbol_key
                preview_variant = self._selected_symbol_variant if is_selected_symbol else "friendly"
                preview_path = self._symbol_variant_path(symbol, preview_variant)
                if preview_path is None:
                    preview_path = self._symbol_variant_path(symbol, "friendly") or self._symbol_variant_path(symbol, "enemy")
                header.setIcon(QIcon(preview_path) if preview_path else QIcon())

                if is_selected_symbol and self._selected_symbol_variant == "enemy":
                    accent = ENEMY_COLOR_HEX
                elif is_selected_symbol:
                    accent = FRIENDLY_COLOR_HEX
                else:
                    accent = "#6c7086"
                header.setStyleSheet(
                    "QToolButton { "
                    f"border: 2px solid {accent}; border-radius: 6px; "
                    "background: #313244; padding: 4px; }"
                )
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
                variant_name = self._selected_symbol_variant.title()
                self.canvas.set_symbol_stamp(f"{variant_name} {symbol['label']}", QPixmap(path))
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
        self._refresh_symbol_palette()

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
        self.canvas.set_symbol_stamp(f"{variant_key.title()} {symbol['label']}", QPixmap(path))
        self._refresh_symbol_palette()
        self.status_bar.showMessage(
            f"Stamping {variant_key} {symbol['label']} symbols"
        )

    def _collect_visible_legend(self, scene_rect: QRectF) -> tuple[list[tuple[str, QPixmap]], list[tuple[str, QPen]]]:
        icon_entries: dict[str, QPixmap] = {}
        line_entries: dict[str, QPen] = {}
        processed: set[int] = set()

        for item in self.canvas.scene().items(scene_rect, Qt.ItemSelectionMode.IntersectsItemShape):
            top = item
            while top.parentItem() is not None:
                top = top.parentItem()

            top_id = id(top)
            if top_id in processed:
                continue
            processed.add(top_id)

            ann_type = top.data(0)
            ann_name = top.data(1)
            if not isinstance(ann_name, str) or not ann_name:
                continue

            if ann_type == "symbol" and isinstance(top, QGraphicsPixmapItem):
                icon_entries.setdefault(ann_name, top.pixmap())
            elif ann_type == "line_tool" and isinstance(top, QGraphicsItemGroup):
                for child in top.childItems():
                    if isinstance(child, QGraphicsPathItem):
                        line_entries.setdefault(ann_name, child.pen())
                        break

        icons = sorted(icon_entries.items(), key=lambda x: x[0].casefold())
        lines = sorted(line_entries.items(), key=lambda x: x[0].casefold())
        return icons, lines

    def _wrap_legend_entries(self, entries: list[str], max_width: int, font: QFont) -> list[str]:
        if not entries:
            return []

        metrics = QFontMetrics(font)
        lines: list[str] = []
        current = ""
        for entry in entries:
            candidate = entry if not current else f"{current}  |  {entry}"
            if metrics.horizontalAdvance(candidate) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = entry
        if current:
            lines.append(current)
        return lines

    def _export_visible_png(self):
        if self.canvas.sceneRect().isEmpty():
            QMessageBox.warning(self, "Export PNG", "Nothing to export right now.")
            return

        default_name = f"{self._current_hexagon or 'map'}_visible_export.png"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Visible PNG",
            default_name,
            "PNG Images (*.png)",
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path = f"{path}.png"

        visible_rect = self.canvas.mapToScene(self.canvas.viewport().rect()).boundingRect()
        visible_rect = visible_rect.intersected(self.canvas.sceneRect())
        if visible_rect.isEmpty():
            QMessageBox.warning(self, "Export PNG", "Visible viewport area is empty.")
            return

        upscale = 3
        export_width = max(1, self.canvas.viewport().width() * upscale)
        export_height = max(1, self.canvas.viewport().height() * upscale)

        base_image = QImage(export_width, export_height, QImage.Format.Format_ARGB32_Premultiplied)
        base_image.fill(QColor("#1e1e2e"))

        painter = QPainter(base_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.scale(upscale, upscale)
        self.canvas.viewport().render(painter, QPoint(0, 0))
        painter.end()

        icons_used, lines_used = self._collect_visible_legend(visible_rect)

        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        body_font = QFont("Segoe UI", 12)
        section_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        footer_font = QFont("Segoe UI", 11)
        body_metrics = QFontMetrics(body_font)
        section_metrics = QFontMetrics(section_font)
        title_metrics = QFontMetrics(title_font)
        footer_metrics = QFontMetrics(footer_font)

        row_height = max(34, body_metrics.lineSpacing() + 8)
        section_gap = 8

        enemy_icons: dict[str, tuple[str, QPixmap]] = {}
        friendly_icons: dict[str, tuple[str, QPixmap]] = {}
        neutral_icons: dict[str, tuple[str, QPixmap]] = {}
        for name, pixmap in icons_used:
            lower = name.casefold()
            if lower.startswith("enemy "):
                base_name = name[6:].strip()
                enemy_icons[base_name] = (name, pixmap)
            elif lower.startswith("friendly "):
                base_name = name[9:].strip()
                friendly_icons[base_name] = (name, pixmap)
            else:
                neutral_icons[name] = (name, pixmap)

        icon_rows: list[tuple[tuple[str, QPixmap] | None, tuple[str, QPixmap] | None]] = []
        paired_names = sorted(set(enemy_icons) | set(friendly_icons), key=str.casefold)
        for base_name in paired_names:
            icon_rows.append((enemy_icons.get(base_name), friendly_icons.get(base_name)))
        for neutral_name in sorted(neutral_icons, key=str.casefold):
            icon_rows.append((None, neutral_icons[neutral_name]))

        legend_height = 24 + title_metrics.height() + 12
        if icon_rows:
            legend_height += section_metrics.height() + 6 + (len(icon_rows) * row_height) + section_gap
        if lines_used:
            legend_height += section_metrics.height() + 6 + (len(lines_used) * row_height) + section_gap
        if not icon_rows and not lines_used:
            legend_height += body_metrics.lineSpacing() + section_gap
        legend_height += 14 + footer_metrics.height() + 24

        final_image = QImage(
            export_width,
            export_height + legend_height,
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        final_image.fill(QColor("#0f1117"))

        final_painter = QPainter(final_image)
        final_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        final_painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        final_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        final_painter.drawImage(0, 0, base_image)

        legend_top = export_height
        final_painter.fillRect(0, legend_top, export_width, legend_height, QColor("#1f355a"))

        x = 24
        preview_x = x
        label_x = x + 44
        y = legend_top + 24
        final_painter.setPen(QColor("#e6edf3"))
        final_painter.setFont(title_font)
        final_painter.drawText(x, y + title_metrics.ascent(), "Legend (Visible Area)")
        y += title_metrics.height() + 12

        if icon_rows:
            final_painter.setFont(section_font)
            final_painter.setPen(QColor("#dce6ff"))
            final_painter.drawText(x, y + section_metrics.ascent(), "Icons (Enemy | Friendly)")
            y += section_metrics.height() + 6

            col_width = max(120, (export_width - (x * 2)) // 2)
            enemy_preview_x = x
            enemy_label_x = x + 44
            friendly_preview_x = x + col_width
            friendly_label_x = friendly_preview_x + 44

            final_painter.setFont(body_font)
            final_painter.setPen(QColor("#e6edf3"))
            for enemy_entry, friendly_entry in icon_rows:
                baseline = y + ((row_height + body_metrics.ascent() - body_metrics.descent()) // 2)

                if enemy_entry is not None:
                    name, pixmap = enemy_entry
                    icon = pixmap.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    iy = y + max(0, (row_height - icon.height()) // 2)
                    ix = enemy_preview_x + max(0, (30 - icon.width()) // 2)
                    final_painter.drawPixmap(ix, iy, icon)
                    final_painter.drawText(enemy_label_x, baseline, name)

                if friendly_entry is not None:
                    name, pixmap = friendly_entry
                    icon = pixmap.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    iy = y + max(0, (row_height - icon.height()) // 2)
                    ix = friendly_preview_x + max(0, (30 - icon.width()) // 2)
                    final_painter.drawPixmap(ix, iy, icon)
                    final_painter.drawText(friendly_label_x, baseline, name)

                y += row_height
            y += section_gap

        if lines_used:
            final_painter.setFont(section_font)
            final_painter.setPen(QColor("#dce6ff"))
            final_painter.drawText(x, y + section_metrics.ascent(), "Lines and Arrows")
            y += section_metrics.height() + 6

            final_painter.setFont(body_font)
            for name, pen in lines_used:
                sample_pen = QPen(pen)
                sample_pen.setWidth(max(2, min(8, int(round(max(1.0, pen.widthF()) * 2.0)))))
                sample_pen.setCosmetic(True)
                final_painter.setPen(sample_pen)
                mid_y = y + row_height // 2
                final_painter.drawLine(preview_x + 2, mid_y, preview_x + 34, mid_y)

                if "arrow" in name.lower():
                    final_painter.setBrush(sample_pen.color())
                    arrow = QPolygonF([
                        QPointF(preview_x + 34, mid_y),
                        QPointF(preview_x + 28, mid_y - 4),
                        QPointF(preview_x + 28, mid_y + 4),
                    ])
                    final_painter.drawPolygon(arrow)
                    final_painter.setBrush(Qt.BrushStyle.NoBrush)

                final_painter.setPen(QColor("#e6edf3"))
                baseline = y + ((row_height + body_metrics.ascent() - body_metrics.descent()) // 2)
                final_painter.drawText(label_x, baseline, name)
                y += row_height
            y += section_gap

        if not icon_rows and not lines_used:
            final_painter.setFont(body_font)
            final_painter.setPen(QColor("#e6edf3"))
            final_painter.drawText(x, y + body_metrics.ascent(), "No icons, lines, or arrows used in the visible area.")
            y += body_metrics.lineSpacing() + section_gap

        y += 14
        footer = f"Made with CMRC IGS  |  War {self._war_number}"
        final_painter.setFont(footer_font)
        final_painter.setPen(QColor("#9aa4b2"))
        final_painter.drawText(x, y + footer_metrics.ascent(), footer)
        final_painter.end()

        if not final_image.save(path, "PNG"):
            QMessageBox.critical(self, "Export PNG", "Failed to save the PNG file.")
            return

        self.status_bar.showMessage(f"Exported visible area to {path}")

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
        if war_report.get("warNumber") is not None:
            self._war_number = str(war_report.get("warNumber"))
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
    war_number = "—"
    try:
        war_data = client.get_war()
        if isinstance(war_data, dict):
            war_number = str(war_data.get("warNumber", "—"))
    except Exception:
        war_number = "—"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if os.path.exists(APP_ICON_PATH):
        app.setWindowIcon(QIcon(APP_ICON_PATH))
    window = MainWindow(client, hexagons, war_number=war_number)
    window.show()

    update_info = check_for_new_version(os.path.dirname(__file__))
    status = update_info.get("status")
    if status == "update-available":
        remote_url = str(update_info.get("remote_url", REPO_URL))
        local_short = str(update_info.get("local_sha", ""))[:7]
        remote_short = str(update_info.get("remote_sha", ""))[:7]
        window.status_bar.showMessage(
            f"Update available: local {local_short} -> remote {remote_short}"
        )
        QMessageBox.information(
            window,
            "Update Available",
            (
                "A newer version of this app is available.\n\n"
                f"Local:  {local_short}\n"
                f"Remote: {remote_short}\n\n"
                f"Repository: {remote_url}"
            ),
        )
    elif status == "up-to-date":
        window.status_bar.showMessage("Version check: app is up to date")
    else:
        window.status_bar.showMessage("Version check unavailable")

    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
