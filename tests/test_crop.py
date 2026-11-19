from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from capsha.annotations import (
    ArrowAnnotation,
    CaptionAnnotation,
    MosaicAnnotation,
    RectangleAnnotation,
    TextAnnotation,
    Tool,
)
from capsha.canvas import AnnotationCanvas


class CropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def _source_image() -> QImage:
        image = QImage(100, 80, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#1e293b"))
        painter = QPainter(image)
        painter.fillRect(20, 10, 50, 40, QColor("#22c55e"))
        painter.end()
        return image

    def test_crop_translates_annotations_and_undo_restores_everything(self) -> None:
        canvas = AnnotationCanvas(self._source_image())
        canvas._annotations = [
            TextAnnotation("inside", QPointF(25, 15)),
            CaptionAnnotation("①", QPointF(30, 20), number=1),
            RectangleAnnotation(QRectF(10, 5, 30, 20)),
            MosaicAnnotation(QRectF(65, 35, 20, 20)),
            ArrowAnnotation(QPointF(90, 70), QPointF(99, 79)),
        ]
        original = canvas._clone_annotations(canvas._annotations)
        canvas._commit_history()
        shared_base_key = canvas._history[-1].image.cacheKey()

        canvas.set_tool(Tool.CROP)
        canvas._crop_rect = QRectF(20, 10, 50, 40)
        self.assertTrue(canvas.apply_crop())

        self.assertEqual(canvas._base.size().toTuple(), (50, 40))
        self.assertEqual(canvas._base.pixelColor(0, 0), QColor("#22c55e"))
        self.assertEqual(len(canvas._annotations), 4)
        self.assertEqual(canvas._annotations[0].position, QPointF(5, 5))
        self.assertEqual(canvas._annotations[1].position, QPointF(10, 10))
        self.assertEqual(canvas._annotations[2].rect, QRectF(-10, -5, 30, 20))
        self.assertEqual(canvas._annotations[3].rect, QRectF(45, 25, 20, 20))
        self.assertEqual(canvas.render_image().size().toTuple(), (50, 40))

        canvas.undo()
        self.assertEqual(canvas._base.size().toTuple(), (100, 80))
        self.assertEqual(canvas._annotations, original)
        self.assertEqual(canvas._history[canvas._history_index].image.cacheKey(), shared_base_key)

        canvas.redo()
        self.assertEqual(canvas._base.size().toTuple(), (50, 40))
        self.assertEqual(len(canvas._annotations), 4)

    def test_full_image_crop_does_not_create_history_entry(self) -> None:
        canvas = AnnotationCanvas(self._source_image())
        history_length = len(canvas._history)
        canvas.set_tool(Tool.CROP)

        self.assertTrue(canvas.apply_crop())
        self.assertEqual(len(canvas._history), history_length)
        self.assertEqual(canvas._base.size().toTuple(), (100, 80))
        self.assertEqual(canvas._tool, Tool.SELECT)

    def test_crop_edges_corners_and_move_stay_in_source_coordinates(self) -> None:
        canvas = AnnotationCanvas(self._source_image())
        original = QRectF(20, 10, 50, 40)
        cases = {
            "l": (QPointF(25, 30), QRectF(25, 10, 45, 40)),
            "r": (QPointF(60, 30), QRectF(20, 10, 40, 40)),
            "t": (QPointF(45, 15), QRectF(20, 15, 50, 35)),
            "b": (QPointF(45, 45), QRectF(20, 10, 50, 35)),
            "tl": (QPointF(25, 15), QRectF(25, 15, 45, 35)),
            "tr": (QPointF(65, 15), QRectF(20, 15, 45, 35)),
            "bl": (QPointF(25, 45), QRectF(25, 10, 45, 35)),
            "br": (QPointF(65, 45), QRectF(20, 10, 45, 35)),
        }
        for handle, (point, expected) in cases.items():
            canvas._crop_original = QRectF(original)
            canvas._crop_drag_mode = handle
            canvas._update_crop_drag(point)
            self.assertEqual(canvas._crop_rect, expected, handle)

        canvas._crop_original = QRectF(original)
        canvas._crop_drag_mode = "move"
        canvas._crop_drag_origin = QPointF(30, 20)
        canvas._update_crop_drag(QPointF(40, 25))
        self.assertEqual(canvas._crop_rect, QRectF(30, 15, 50, 40))


if __name__ == "__main__":
    unittest.main()
