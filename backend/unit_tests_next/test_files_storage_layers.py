from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from bson import ObjectId

from infrastructure.local_object_storage import InvalidStoragePath, LocalObjectStorage, StoredObjectNotFound
from slices.files_storage.models import FilePrincipal, StoredFile, UploadedFile
from slices.files_storage.repository import MongoFilesRepository
from slices.files_storage.service import FileAccessDenied, FilesStorageService, UnknownFile
from slices.files_storage.web import files_storage_http_error, uploaded_file_payload
from slices.files_storage.domain import FileTooLarge, UnsupportedFileType


FILE = StoredFile("f", "owner", "path/f.pdf", "f.pdf", "application/pdf", 4)


class Repository:
    def __init__(self):
        self.file = FILE; self.user_reference = False; self.linked = False; self.submission = False; self.calls = []
    async def insert(self, stored_file, created_at): self.calls.append(("insert", stored_file, created_at))  # type: ignore[no-untyped-def]
    async def find_active(self, file_id): return self.file  # type: ignore[no-untyped-def]
    async def user_references_file(self, user_id, file_id): return self.user_reference  # type: ignore[no-untyped-def]
    async def partner_links_user(self, partner_id, user_id): return self.linked  # type: ignore[no-untyped-def]
    async def partner_submission_exists(self, partner_id, user_id): return self.submission  # type: ignore[no-untyped-def]
    async def protect_owner_files(self, user_id, deleted_at): self.calls.append(("protect", user_id, deleted_at))  # type: ignore[no-untyped-def]


class Storage:
    def __init__(self): self.calls = []
    def initialize(self): self.calls.append(("init",)); return "local"
    def put(self, path, data, content_type): self.calls.append(("put", path, data, content_type)); return len(data)  # type: ignore[no-untyped-def]
    def get(self, path): self.calls.append(("get", path)); return b"data", "fallback/type"  # type: ignore[no-untyped-def]


def test_service_upload_download_access_and_protection_lifecycle():
    async def scenario():
        repository, storage = Repository(), Storage()
        service = FilesStorageService(repository, storage, 10)
        assert service.initialize() == "local"
        upload = await service.upload(FilePrincipal("owner", "user"), "new", "folder/file.PDF", None, b"data", "now")
        assert upload == UploadedFile("new", "file.PDF", "gerdoctor/uploads/owner/new.pdf")
        assert (await service.download(FilePrincipal("owner", "user"), "f")).data == b"data"
        repository.user_reference = True
        assert (await service.download(FilePrincipal("reader", "user"), "f")).content_type == "application/pdf"
        repository.linked = True
        await service.download(FilePrincipal("partner", "partner", "p"), "f")
        repository.linked, repository.submission = False, True
        await service.download(FilePrincipal("partner", "partner", "p"), "f")
        await service.protect_owner_files("owner", "deleted")
        assert ("protect", "owner", "deleted") in repository.calls
    asyncio.run(scenario())


def test_service_rejects_unknown_and_unauthorized_files():
    async def scenario():
        repository, storage = Repository(), Storage()
        service = FilesStorageService(repository, storage, 10)
        repository.file = None
        with pytest.raises(UnknownFile): await service.download(FilePrincipal("u", "user"), "missing")
        repository.file = FILE
        with pytest.raises(FileAccessDenied): await service.download(FilePrincipal("u", "guest"), "f")
        with pytest.raises(FileAccessDenied): await service.download(FilePrincipal("u", "user"), "f")
        with pytest.raises(FileAccessDenied): await service.download(FilePrincipal("p", "partner", "partner"), "f")
    asyncio.run(scenario())


class Collection:
    def __init__(self, row=None): self.row = row; self.calls = []
    async def insert_one(self, document): self.calls.append(("insert", document))
    async def find_one(self, query, projection=None): self.calls.append(("find", query, projection)); return self.row
    async def update_many(self, query, operation): self.calls.append(("update_many", query, operation))


def test_mongo_repository_maps_metadata_and_access_relations():
    async def scenario():
        partner_id = str(ObjectId())
        database = SimpleNamespace(
            files=Collection({"id": "f", "user_id": "u", "storage_path": "p", "filename": "legacy.pdf"}),
            user_progress=Collection({"_id": 1}),
            partners=Collection({"linked_user_ids": ["u"]}),
            partner_submissions=Collection({"_id": 1}),
        )
        repository = MongoFilesRepository(database)
        await repository.insert(FILE, "now")
        loaded = await repository.find_active("f")
        assert loaded.original_filename == "legacy.pdf" and loaded.content_type == "application/octet-stream" and loaded.size == 0
        database.files.row = None
        assert await repository.find_active("missing") is None
        assert await repository.user_references_file("u", "f") is True
        assert await repository.partner_links_user(partner_id, "u") is True
        assert await repository.partner_links_user("bad", "u") is False
        assert await repository.partner_submission_exists(partner_id, "u") is True
        await repository.protect_owner_files("u", "deleted")
    asyncio.run(scenario())


def test_local_storage_confines_paths_and_roundtrips_bytes(tmp_path):
    storage = LocalObjectStorage(str(tmp_path))
    assert storage.initialize() == "local"
    assert storage.put("folder/file.bin", b"data", "ignored") == 4
    assert storage.get("folder/file.bin") == (b"data", "application/octet-stream")
    with pytest.raises(StoredObjectNotFound): storage.get("missing")
    with pytest.raises(InvalidStoragePath): storage.put("../escape", b"x", "text/plain")


def test_web_payload_and_error_contracts_are_stable():
    assert uploaded_file_payload(UploadedFile("f", "n", "p")) == {"id": "f", "filename": "n", "path": "p"}
    errors = [UnsupportedFileType(), FileTooLarge(), UnknownFile(), FileAccessDenied(), InvalidStoragePath(), StoredObjectNotFound(), ValueError()]
    assert [files_storage_http_error(error).status_code for error in errors] == [400, 413, 404, 403, 400, 404, 400]
