import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse
from starlette.datastructures import UploadFile

router = APIRouter(prefix="/documents", tags=["documents"])


def service(request: Request):
    if not request.app.state.ingestion_available:
        raise HTTPException(503, "database_unavailable")
    return request.app.state.ingestion


@router.post("", status_code=202)
async def upload(request: Request):
    svc = service(request)
    async with request.form(max_files=1, max_fields=0) as form:
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise HTTPException(422, "one_pdf_file_required")
        return await svc.accept(file)


@router.get("")
async def list_documents(request: Request):
    return await asyncio.to_thread(service(request).repo.list_documents)


@router.get("/{doc_id}")
async def get_document(doc_id: UUID, request: Request):
    row = await asyncio.to_thread(service(request).repo.get, doc_id)
    if not row:
        raise HTTPException(404, "document_not_found")
    return row


@router.get("/{doc_id}/file")
async def get_file(doc_id: UUID, request: Request):
    svc = service(request)
    row = await asyncio.to_thread(svc.repo.get, doc_id)
    if not row or row["state"] != "ready":
        raise HTTPException(404, "document_not_ready")
    path = svc.path(doc_id)
    if not path.is_file():
        raise HTTPException(404, "document_not_found")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="document.pdf",
        content_disposition_type="inline",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: UUID, request: Request):
    await service(request).delete(doc_id)
    return Response(status_code=204)
