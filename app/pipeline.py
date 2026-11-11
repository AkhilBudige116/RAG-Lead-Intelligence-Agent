import uuid
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import UploadBatch, Company, Contact, Email, Sector
from app.ingestion.parser import parse_file, ParsedEmailData
from app.ingestion.validation import validate_file_upload
from app.extraction.extractor import LeadExtractor
from app.rag.retriever import SectorRetriever
from app.classification.engine import SectorClassifier
from app.dedup.consolidator import consolidate_lead, ConsolidationResult
from app.core.logging import logger


class PipelineProcessor:
    def __init__(self):
        self.extractor = LeadExtractor()
        self.retriever = SectorRetriever()
        self.classifier = SectorClassifier()

    def process_email_item(
        self,
        email_data: ParsedEmailData,
        batch_id: Optional[str],
        db: Session
    ) -> ConsolidationResult:
        """Processes a single parsed email through the full RAG & classification pipeline."""
        # 1. Entity Extraction
        lead = self.extractor.extract(email_data)

        # 2. RAG Knowledge Retrieval
        trace = self.retriever.retrieve(lead, body_snippet=email_data.body)

        # 3. LLM / AI Sector Classification
        classification, gate, matched_sector = self.classifier.classify_lead(lead, trace, db)

        # 4. Duplicate Detection & Consolidation
        result = consolidate_lead(
            lead=lead,
            raw_email=email_data,
            classification=classification,
            gate=gate,
            trace=trace,
            matched_sector=matched_sector,
            batch_id=batch_id,
            db=db
        )
        return result

    def process_batch_files(
        self,
        batch_id: str,
        files_data: List[tuple[str, bytes]]
    ) -> Dict[str, Any]:
        """
        Background task handler for processing uploaded files in a batch.
        """
        db = SessionLocal()
        try:
            batch = db.query(UploadBatch).filter(UploadBatch.id == batch_id).first()
            if not batch:
                logger.error(f"Batch {batch_id} not found in database.")
                return {"error": "Batch not found"}

            batch.status = "processing"
            db.commit()

            total_emails = 0
            processed = 0
            failed = 0

            # First pass: parse all files
            all_emails: List[ParsedEmailData] = []
            for filename, content in files_data:
                try:
                    is_valid, err = validate_file_upload(filename, content)
                    if not is_valid:
                        logger.warning(f"File {filename} invalid: {err}")
                        failed += 1
                        continue

                    parsed_items = parse_file(filename, content)
                    all_emails.extend(parsed_items)
                except Exception as e:
                    logger.error(f"Failed to parse file {filename}: {e}")
                    failed += 1

            batch.total_emails = len(all_emails) + failed
            db.commit()

            # Second pass: process each email through the pipeline
            for item in all_emails:
                try:
                    self.process_email_item(item, batch_id=batch_id, db=db)
                    processed += 1
                except Exception as e:
                    logger.error(f"Pipeline error processing email {item.raw_hash}: {e}")
                    failed += 1

                # Periodically update batch counts
                batch.processed_count = processed
                batch.failed_count = failed
                db.commit()

            batch.status = "completed" if failed == 0 else ("completed_with_errors" if processed > 0 else "failed")
            db.commit()
            logger.info(f"Batch {batch_id} completed: {processed} processed, {failed} failed.")

            return {
                "batch_id": batch_id,
                "total": batch.total_emails,
                "processed": processed,
                "failed": failed,
                "status": batch.status
            }
        except Exception as e:
            logger.error(f"Fatal error in batch {batch_id}: {e}")
            if batch:
                batch.status = "failed"
                batch.error_message = str(e)
                db.commit()
            return {"error": str(e)}
        finally:
            db.close()


pipeline_processor = PipelineProcessor()
