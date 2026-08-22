import fitz

from pdf2image import convert_from_path

import tempfile

import os

from utils.ocr import extract_text_from_image


def extract_text_from_pdf(pdf_path):

    text = ""

    doc = fitz.open(pdf_path)

    for page in doc:
        text += page.get_text()

    doc.close()

    if text.strip():
        return text

    # ---------- OCR Fallback ----------

    images = convert_from_path(pdf_path,poppler_path=r"D:\ProjectsAI\Release-26.02.0-0\poppler-26.02.0\Library\bin")

    text = ""

    with tempfile.TemporaryDirectory() as temp_dir:

        for i, image in enumerate(images):

            image_path = os.path.join(
                temp_dir,
                f"page_{i}.png"
            )

            image.save(image_path)

            text += extract_text_from_image(image_path)

            text += "\n"

    return text