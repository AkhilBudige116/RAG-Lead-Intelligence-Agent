import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import UploadBatch
from app.pipeline import pipeline_processor
from app.core.logging import logger

router = APIRouter(prefix="/api/uploads", tags=["Uploads"])


@router.post("")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts multiple email files (.eml, .msg, .mbox, .csv, .json),
    creates an UploadBatch, and schedules background parsing and RAG processing.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    batch_id = str(uuid.uuid4())
    filenames = [f.filename for f in files]
    primary_filename = filenames[0] if len(filenames) == 1 else f"{len(filenames)} files ({filenames[0]}...)"

    batch = UploadBatch(
        id=batch_id,
        filename=primary_filename,
        total_emails=0,
        processed_count=0,
        failed_count=0,
        status="pending"
    )
    db.add(batch)
    db.commit()

    # Read file contents into memory
    files_data = []
    for f in files:
        content = await f.read()
        files_data.append((f.filename, content))

    # Trigger background processing
    background_tasks.add_task(
        pipeline_processor.process_batch_files,
        batch_id=batch_id,
        files_data=files_data
    )

    logger.info(f"Accepted batch upload {batch_id} with {len(files)} file(s).")
    return {
        "batch_id": batch_id,
        "message": f"Successfully uploaded {len(files)} file(s). Batch processing initiated.",
        "status": "pending"
    }
