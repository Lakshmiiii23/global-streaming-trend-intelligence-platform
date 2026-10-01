import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import ClientError
from config.settings import settings

logger = logging.getLogger(__name__)

class BronzeStorageManager:
    """
    Manages Bronze Layer object storage (Cloudflare R2 / S3-compatible, with local fallback).
    
    In a Medallion Architecture:
    - Bronze represents the raw, immutable ingestion zone.
    - Data is stored in append-only JSON format.
    - Schema changes do not break bronze storage (schema-on-read).
    - If downstream logic fails, we can replay from Bronze anytime without re-scraping.
    """
    
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND
        self.bucket_name = settings.R2_BUCKET_NAME
        self.local_dir = settings.BRONZE_DIR
        self.s3_client = None
        
        if self.backend == "r2":
            if not (settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY):
                logger.warning(
                    "Cloudflare R2 credentials missing. Falling back to local storage backend."
                )
                self.backend = "local"
            else:
                try:
                    self.s3_client = boto3.client(
                        "s3",
                        endpoint_url=settings.R2_ENDPOINT_URL,
                        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                        region_name="auto"
                    )
                    logger.info("Initialized Cloudflare R2 S3 client for bucket: %s", self.bucket_name)
                except Exception as e:
                    logger.error("Failed to connect to Cloudflare R2: %s. Falling back to local.", e)
                    self.backend = "local"

    def save_batch(
        self, 
        data: List[Dict[str, Any]], 
        batch_id: str, 
        chart_date: Optional[str] = None
    ) -> str:
        """
        Save a batch of raw scraped data to the Bronze layer.
        
        Args:
            data: List of raw dictionaries scraped from charts.
            batch_id: Unique batch identifier (e.g. timestamp or uuid).
            chart_date: Date string (YYYY-MM-DD) for partitioning.
            
        Returns:
            The storage key / URI where the batch was written.
        """
        if not chart_date:
            chart_date = datetime.now().strftime("%Y-%m-%d")
            
        storage_key = f"bronze/{chart_date}/batch_{batch_id}.json"
        payload = {
            "metadata": {
                "batch_id": batch_id,
                "chart_date": chart_date,
                "record_count": len(data),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "storage_backend": self.backend
            },
            "records": data
        }
        json_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        
        if self.backend == "r2" and self.s3_client:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=storage_key,
                    Body=json_bytes,
                    ContentType="application/json"
                )
                logger.info("Successfully uploaded %d records to R2: %s", len(data), storage_key)
                return f"r2://{self.bucket_name}/{storage_key}"
            except ClientError as e:
                logger.error("R2 upload error: %s. Falling back to local disk.", e)
                
        # Fallback / Local Storage
        local_path = self.local_dir / chart_date / f"batch_{batch_id}.json"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(json_bytes)
        logger.info("Saved %d records to local bronze storage: %s", len(data), local_path)
        return str(local_path)

    def list_batches(self, chart_date: Optional[str] = None) -> List[str]:
        """List available bronze batch keys for a given date or all dates."""
        batches = []
        if self.backend == "r2" and self.s3_client:
            prefix = f"bronze/{chart_date}/" if chart_date else "bronze/"
            try:
                paginator = self.s3_client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                    for obj in page.get("Contents", []):
                        batches.append(obj["Key"])
                return batches
            except Exception as e:
                logger.error("Error listing R2 batches: %s", e)
                
        # Local listing
        search_dir = self.local_dir / chart_date if chart_date else self.local_dir
        if search_dir.exists():
            for p in search_dir.glob("**/*.json"):
                batches.append(str(p))
        return sorted(batches)

    def load_batch(self, key_or_path: str) -> Dict[str, Any]:
        """Load and return the raw batch JSON content from storage."""
        if key_or_path.startswith("r2://") or (self.backend == "r2" and self.s3_client and not Path(key_or_path).exists()):
            r2_key = key_or_path.replace(f"r2://{self.bucket_name}/", "")
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=r2_key)
            return json.loads(response["Body"].read().decode("utf-8"))
        
        # Local read
        with open(key_or_path, "r", encoding="utf-8") as f:
            return json.load(f)

def get_storage_manager() -> BronzeStorageManager:
    """Factory function for BronzeStorageManager."""
    return BronzeStorageManager()
