"""
ocr_engine.py
Unified OCR wrapper:
  - Primary: PaddleOCR (best accuracy for Indian documents)
  - Fallback: PyMuPDF fitz pixmap rendering if PaddleOCR unavailable
"""
import os
import tempfile
import numpy as np
from loguru import logger


class OCREngine:
    """Singleton OCR engine — lazy-initialized on first use."""

    _instance = None
    _paddle_ocr = None
    _available = None

    @classmethod
    def _get_paddle(cls):
        if cls._available is None:
            try:
                from paddleocr import PaddleOCR
                cls._paddle_ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang="en",
                    use_gpu=os.environ.get("OCR_GPU_ENABLED", "false").lower() == "true",
                    show_log=False,
                )
                cls._available = True
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                cls._available = False
                logger.warning(f"PaddleOCR unavailable: {e}. Will use PyMuPDF text layer only.")
        return cls._paddle_ocr if cls._available else None

    @classmethod
    def extract_text_from_pdf(cls, file_path: str, min_text_threshold: int = 200) -> str:
        """
        Extract text from PDF.
        1. Try native text extraction (PyMuPDF).
        2. If text < min_text_threshold chars → run OCR page by page.
        """
        native_text = cls._extract_native(file_path)

        if len(native_text.strip()) >= min_text_threshold:
            logger.debug(f"Native text extraction: {len(native_text)} chars from {file_path}")
            return native_text

        logger.info(f"Sparse native text ({len(native_text)} chars). Running OCR on {file_path}")
        ocr_text = cls._extract_with_ocr(file_path)
        combined = native_text + "\n" + ocr_text
        logger.info(f"OCR total text: {len(combined)} chars")
        return combined

    @classmethod
    def _extract_native(cls, file_path: str) -> str:
        try:
            import fitz
            doc = fitz.open(file_path)
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text("text"))
            doc.close()
            return "\n".join(pages_text)
        except Exception as e:
            logger.warning(f"Native PDF extraction failed: {e}")
            return ""

    @classmethod
    def _extract_with_ocr(cls, file_path: str) -> str:
        paddle = cls._get_paddle()
        if paddle is None:
            return cls._fitz_pixmap_ocr_fallback(file_path)

        try:
            import fitz
            doc = fitz.open(file_path)
            all_text = []

            for page_num, page in enumerate(doc):
                # Render page to image (300 DPI for accuracy)
                mat = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                    pix.save(tmp_path)

                try:
                    result = paddle.ocr(tmp_path, cls=True)
                    page_lines = []
                    if result and result[0]:
                        for line in result[0]:
                            if line and len(line) >= 2:
                                text_conf = line[1]
                                if isinstance(text_conf, (list, tuple)) and len(text_conf) >= 1:
                                    text = text_conf[0]
                                    conf = text_conf[1] if len(text_conf) > 1 else 1.0
                                    if conf > 0.5:  # confidence threshold
                                        page_lines.append(str(text))
                    all_text.append("\n".join(page_lines))
                    logger.debug(f"Page {page_num+1}: OCR extracted {len(page_lines)} lines")
                except Exception as e:
                    logger.warning(f"Page {page_num+1} OCR failed: {e}")
                finally:
                    try: os.unlink(tmp_path)
                    except Exception: pass

            doc.close()
            return "\n".join(all_text)

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

    @classmethod
    def _fitz_pixmap_ocr_fallback(cls, file_path: str) -> str:
        """
        Last resort: use pytesseract if available.
        """
        try:
            import fitz
            import pytesseract
            from PIL import Image
            import io

            doc = fitz.open(file_path)
            all_text = []
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                text = pytesseract.image_to_string(img, lang="eng")
                all_text.append(text)
            doc.close()
            logger.info(f"Pytesseract OCR: {sum(len(t) for t in all_text)} chars")
            return "\n".join(all_text)
        except Exception as e:
            logger.warning(f"Pytesseract fallback failed: {e}")
            return ""
