import pytest

from slices.files_storage.domain import (
    FileTooLarge, UnsupportedFileType, immediate_access, original_filename,
    safe_upload_extension, storage_path, validate_upload,
)
from slices.files_storage.models import FilePrincipal, StoredFile


FILE = StoredFile("f", "owner", "path", "file.pdf", "application/pdf", 1)


def test_upload_filename_extension_and_path_are_safe_and_stable():
    assert safe_upload_extension("folder/REPORT.PDF") == "pdf"
    assert safe_upload_extension("photo.gif") == "gif"
    assert safe_upload_extension("archive.backup.zip") == "zip"
    with pytest.raises(UnsupportedFileType): safe_upload_extension("no-extension")
    with pytest.raises(UnsupportedFileType): safe_upload_extension("payload.html")
    assert original_filename("folder/report.pdf", "f", "pdf") == "report.pdf"
    assert original_filename(None, "f", "pdf") == "f.pdf"
    assert storage_path("u", "f", "pdf") == "gerdoctor/uploads/u/f.pdf"


def test_upload_validation_rejects_active_content_and_oversize_data():
    validate_upload("application/pdf", 10, 10)
    with pytest.raises(UnsupportedFileType): validate_upload("TEXT/HTML", 1, 10)
    with pytest.raises(FileTooLarge): validate_upload("application/pdf", 11, 10)


@pytest.mark.parametrize("principal,stored_file,expected", [
    (FilePrincipal("admin", "admin"), FILE, True),
    (FilePrincipal("owner", "user"), FILE, True),
    (FilePrincipal("other", "user"), FILE, None),
    (FilePrincipal("partner", "partner", "p"), FILE, None),
    (FilePrincipal("partner", "partner"), FILE, False),
    (FilePrincipal("other", "guest"), FILE, False),
    (FilePrincipal("admin", "admin"), StoredFile("f", None, "p", "n", "c", 0), False),
])
def test_immediate_access_distinguishes_final_and_repository_decisions(principal, stored_file, expected):
    assert immediate_access(principal, stored_file) is expected
