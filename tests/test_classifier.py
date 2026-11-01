"""Tests for the file classification engine."""


import pytest

from cleandownloads.classifier import Classifier
from cleandownloads.config import DEFAULT_RULES, AppConfig, RuleConfig


@pytest.fixture
def classifier() -> Classifier:
    rules = [RuleConfig(**r) for r in DEFAULT_RULES]
    config = AppConfig(rules=rules)
    return Classifier(config)


def test_classify_documents(classifier: Classifier):
    assert classifier.classify_filename("invoice.pdf").subfolder == "Documents/PDF"
    assert classifier.classify_filename("document.docx").subfolder == "Documents/Word"
    assert classifier.classify_filename("old.doc").subfolder == "Documents/Word"
    assert classifier.classify_filename("report.odt").subfolder == "Documents/Word"
    assert classifier.classify_filename("notes.rtf").subfolder == "Documents/Word"
    assert classifier.classify_filename("data.xlsx").subfolder == "Documents/Excel"
    assert classifier.classify_filename("metrics.csv").subfolder == "Documents/Excel"
    assert classifier.classify_filename("slides.pptx").subfolder == "Documents/PowerPoint"


def test_classify_images(classifier: Classifier):
    assert classifier.classify_filename("screenshot.png").subfolder == "Images/PNG"
    assert classifier.classify_filename("photo.jpg").subfolder == "Images"
    assert classifier.classify_filename("photo.jpeg").subfolder == "Images"
    assert classifier.classify_filename("animation.gif").subfolder == "Images"
    assert classifier.classify_filename("vector.svg").subfolder == "Images"
    assert classifier.classify_filename("hero.webp").subfolder == "Images"


def test_classify_media(classifier: Classifier):
    assert classifier.classify_filename("clip.mp4").category == "Videos"
    assert classifier.classify_filename("movie.mkv").category == "Videos"
    assert classifier.classify_filename("song.mp3").category == "Audio"
    assert classifier.classify_filename("sound.wav").category == "Audio"
    assert classifier.classify_filename("lossless.flac").category == "Audio"


def test_classify_archives(classifier: Classifier):
    assert classifier.classify_filename("archive.zip").subfolder == "Archives/ZIP"
    assert classifier.classify_filename("package.rar").subfolder == "Archives"
    assert classifier.classify_filename("backup.7z").subfolder == "Archives"
    assert classifier.classify_filename("source.tar.gz").subfolder == "Archives"


def test_classify_software(classifier: Classifier):
    assert classifier.classify_filename("installer.exe").subfolder == "Software/EXE"
    assert classifier.classify_filename("setup.msi").subfolder == "Software"
    assert classifier.classify_filename("app.msix").subfolder == "Software"


def test_classify_code(classifier: Classifier):
    assert classifier.classify_filename("script.py").subfolder == "Code/Python"
    assert classifier.classify_filename("analysis.ipynb").subfolder == "Code/Python"
    assert classifier.classify_filename("index.html").subfolder == "Code/Web Development"
    assert classifier.classify_filename("app.tsx").subfolder == "Code/Web Development"
    assert classifier.classify_filename("Main.java").subfolder == "Code/Programming"
    assert classifier.classify_filename("system.rs").subfolder == "Code/Programming"


def test_classify_unknown(classifier: Classifier):
    res = classifier.classify_filename("unknown_data.bin")
    assert res.category == "Other"
    assert res.subfolder == "Other"
    assert not res.is_matched

    res_no_ext = classifier.classify_filename("README")
    assert res_no_ext.category == "Other"


def test_case_insensitivity(classifier: Classifier):
    assert classifier.classify_filename("INVOICE.PDF").subfolder == "Documents/PDF"
    assert classifier.classify_filename("PHOTO.PNG").subfolder == "Images/PNG"
    assert classifier.classify_filename("SETUP.EXE").subfolder == "Software/EXE"


def test_custom_rule():
    config = AppConfig(
        rules=[
            RuleConfig(
                name="3D Models",
                category="Models",
                subfolder="3D/Models",
                extensions=["blend", "obj", "stl"],
            )
        ]
    )
    custom_classifier = Classifier(config)
    res = custom_classifier.classify_filename("character.blend")
    assert res.category == "Models"
    assert res.subfolder == "3D/Models"
    assert res.is_matched
