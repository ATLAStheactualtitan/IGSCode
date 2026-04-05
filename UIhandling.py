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
from PySide6.QtCore import Qt, QThread, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QPixmap, QFont, QColor, QPalette, QPen, QPainterPath,
    QPainter, QKeySequence, QShortcut, QBrush, QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QComboBox, QLabel, QFrame, QGroupBox, QGridLayout, QStatusBar,
    QToolBar, QToolButton, QButtonGroup, QPushButton, QSpinBox,
    QColorDialog, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsTextItem, QGraphicsItem,
    QGraphicsItemGroup,
)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
BASE_URL   = "https://war-service-live.foxholeservices.com/api"

TOOL_SELECT   = "select"
TOOL_LINE     = "line"
TOOL_ARROW    = "arrow"
TOOL_ZIGZAG   = "zigzag"
TOOL_WAVE     = "wave"
TOOL_TEXT     = "text"
TOOL_ERASE    = "erase"

LINE_TOOLS = {TOOL_LINE, TOOL_ARROW, TOOL_ZIGZAG, TOOL_WAVE}


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
    error = Signal(str)

    def __init__(self, client: WarAPIClient, hexagon: str):
        super().__init__()
        self.client  = client
        self.hexagon = hexagon

    def run(self):
        try:
            dynamic    = self.client.get_dynamic(self.hexagon)
            war_report = self.client.get_war_report(self.hexagon)
            self.data_ready.emit(self.hexagon, dynamic or {}, war_report or {})
        except Exception as e:
            self.error.emit(str(e))


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

        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._tool       = TOOL_SELECT
        self._pen_color  = QColor("#ff4444")
        self._pen_width  = 3
        self._ann_stack: list = []  # undo history

        # Node-based line drawing state
        self._line_nodes: list[QPointF] = []   # confirmed nodes
        self._preview_item: QGraphicsPathItem | None = None  # live preview

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
        self._tool = tool
        cursor_map = {
            TOOL_SELECT: Qt.CursorShape.ArrowCursor,
            TOOL_LINE:   Qt.CursorShape.CrossCursor,
            TOOL_ARROW:  Qt.CursorShape.CrossCursor,
            TOOL_ZIGZAG: Qt.CursorShape.CrossCursor,
            TOOL_WAVE:   Qt.CursorShape.CrossCursor,
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

    def load_image(self, path: str):
        self._scene.clear()
        self._ann_stack.clear()
        pixmap = QPixmap(path)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setZValue(0)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def clear_image(self):
        self._scene.clear()
        self._pixmap_item = None
        self._ann_stack.clear()
        placeholder = self._scene.addText(
            "No map image available for this hexagon",
            QFont("Segoe UI", 14),
        )
        placeholder.setDefaultTextColor(QColor("#6c7086"))
        self._scene.setSceneRect(QRectF(0, 0, 800, 500))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def clear_annotations(self):
        for item in list(self._scene.items()):
            if item is not self._pixmap_item:
                self._scene.removeItem(item)
        self._ann_stack.clear()

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

    # ── Line path builders ───────────────────────────────────────────────── #

    @staticmethod
    def _build_straight(nodes: list[QPointF]) -> QPainterPath:
        path = QPainterPath(nodes[0])
        for pt in nodes[1:]:
            path.lineTo(pt)
        return path

    @staticmethod
    def _build_zigzag(nodes: list[QPointF], amp: float = 12.0) -> QPainterPath:
        """Zig-zag perpendicular to each segment, alternating sides."""
        path = QPainterPath(nodes[0])
        side = 1
        for i in range(1, len(nodes)):
            a, b = nodes[i - 1], nodes[i]
            dx, dy = b.x() - a.x(), b.y() - a.y()
            length = math.hypot(dx, dy) or 1
            # perpendicular unit vector
            px, py = -dy / length, dx / length
            segs = max(2, int(length / 20))
            for s in range(1, segs + 1):
                t = s / segs
                mx = a.x() + dx * t
                my = a.y() + dy * t
                offset = amp * side if s % 2 == 1 else 0
                path.lineTo(QPointF(mx + px * offset, my + py * offset))
            side *= -1
        return path

    @staticmethod
    def _build_wave(nodes: list[QPointF], amp: float = 10.0, freq: float = 30.0) -> QPainterPath:
        """Sine wave along each segment using cubic bezier curves."""
        path = QPainterPath(nodes[0])
        for i in range(1, len(nodes)):
            a, b = nodes[i - 1], nodes[i]
            dx, dy = b.x() - a.x(), b.y() - a.y()
            length = math.hypot(dx, dy) or 1
            ux, uy = dx / length, dy / length   # tangent unit
            px, py = -uy, ux                    # perpendicular unit
            segs = max(1, int(length / freq))
            seg_len = length / segs
            cur = a
            for s in range(segs):
                t0 = s / segs
                t1 = (s + 1) / segs
                p0 = QPointF(a.x() + dx * t0, a.y() + dy * t0)
                p3 = QPointF(a.x() + dx * t1, a.y() + dy * t1)
                sign = 1 if s % 2 == 0 else -1
                ctrl_off = amp * sign
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

    def _update_preview(self, cursor_pos: QPointF):
        """Redraw the dashed preview path from current nodes to cursor."""
        if not self._line_nodes:
            return
        nodes = self._line_nodes + [cursor_pos]
        path  = self._build_path_for_tool(nodes)

        if self._preview_item is None:
            self._preview_item = QGraphicsPathItem()
            pen = QPen(self._pen_color, self._pen_width,
                       Qt.PenStyle.DashLine)
            pen.setDashPattern([6, 4])
            self._preview_item.setPen(pen)
            self._preview_item.setZValue(2)
            self._scene.addItem(self._preview_item)

        self._preview_item.setPath(path)

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

        if self._tool in LINE_TOOLS and self._line_nodes:
            scene_pos = self.mapToScene(event.position().toPoint())
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
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Escape cancels an in-progress line."""
        if event.key() == Qt.Key.Key_Escape and self._line_nodes:
            self._cancel_line()
        else:
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
        self._pen_color = QColor("#ff4444")

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

        # Color picker
        toolbar.addWidget(QLabel(" Color: "))
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(26, 26)
        self._color_btn.setToolTip("Pick annotation colour")
        self._refresh_color_btn()
        self._color_btn.clicked.connect(self._pick_color)
        toolbar.addWidget(self._color_btn)

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
        QShortcut(QKeySequence("T"),                    self, lambda: self._on_tool_selected(5))
        QShortcut(QKeySequence("E"),                    self, lambda: self._on_tool_selected(6))
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
        left.setFixedWidth(210)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        hex_label = QLabel("Hexagon")
        hex_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        left_layout.addWidget(hex_label)

        self.hex_combo = QComboBox()
        self.hex_combo.setFont(QFont("Segoe UI", 10))
        for name in self.hexagons:
            self.hex_combo.addItem(name)
        self.hex_combo.currentTextChanged.connect(self._on_hex_selected)
        left_layout.addWidget(self.hex_combo)

        left_layout.addSpacing(12)

        self.info_box = QGroupBox("Map Info")
        self.info_box.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        info_grid = QGridLayout(self.info_box)
        info_grid.setColumnStretch(1, 1)
        left_layout.addWidget(self.info_box)
        left_layout.addStretch()

        root.addWidget(left)

        # ── Canvas ───────────────────────────────────────────────────────── #
        self.canvas = AnnotationView()
        root.addWidget(self.canvas, stretch=1)

        # ── Status bar ───────────────────────────────────────────────────── #
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — select a hexagon")

    # ---------------------------------------------------------------------- #
    #  Toolbar helpers                                                         #
    # ---------------------------------------------------------------------- #
    def _on_tool_selected(self, index: int):
        if 0 <= index < len(self._tools):
            self._tool_group.button(index).setChecked(True)
            tool = self._tools[index]
            self.canvas.set_tool(tool)
            if tool in LINE_TOOLS:
                self.status_bar.showMessage(
                    "Left-click to add node  •  Right-click to finish line  •  Esc to cancel"
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

    def _refresh_color_btn(self):
        self._color_btn.setStyleSheet(
            f"background-color: {self._pen_color.name()};"
            f"border: 2px solid #888; border-radius: 4px;"
        )

    # ---------------------------------------------------------------------- #
    #  Event handlers                                                          #
    # ---------------------------------------------------------------------- #
    def _on_hex_selected(self, hexagon: str):
        if not hexagon:
            return

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
            self._worker.quit()

        self._worker = HexDataWorker(self.client, hexagon)
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.error.connect(self._on_data_error)
        self._worker.start()

    def _on_data_ready(self, hexagon: str, dynamic: dict, war_report: dict):
        # colonialCasualties / wardenCasualties fetched but not shown per requirements
        self.status_bar.showMessage(f"{hexagon} — ready")
        self._populate_info_box({
            "Day of War":   war_report.get("dayOfWar", "—"),
            "Map Items":    len(dynamic.get("mapItems", [])),
            "Text Items":   len(dynamic.get("mapTextItems", [])),
            "Last Updated": dynamic.get("lastUpdated", "—"),
        })

    def _on_data_error(self, message: str):
        self.status_bar.showMessage(f"API error: {message}")

    # ---------------------------------------------------------------------- #
    #  Info box helpers                                                        #
    # ---------------------------------------------------------------------- #
    def _clear_info_box(self):
        layout = self.info_box.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_info_box(self, data: dict):
        self._clear_info_box()
        layout = self.info_box.layout()
        for row, (key, value) in enumerate(data.items()):
            k = QLabel(f"{key}:")
            k.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            v = QLabel(str(value))
            v.setFont(QFont("Segoe UI", 9))
            layout.addWidget(k, row, 0, Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(v, row, 1, Qt.AlignmentFlag.AlignLeft)

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
