"""
S3 Model Storage — persists ML model artifacts to S3.
Replaces local disk storage for Lambda compatibility.
"""
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

import boto3
import joblib


class S3ModelStorage:
    """Store/retrieve ML models from S3 bucket."""

    def __init__(self, bucket: str = None):
        self.bucket = bucket or os.getenv("S3_MODEL_BUCKET", "")
        self.s3 = boto3.client("s3")
        self._local_cache = {}

    def upload_artifacts(self, local_dir: str, version: str) -> str:
        """Upload all model artifacts from local directory to S3."""
        local_path = Path(local_dir)
        prefix = f"models/{version}/"

        for f in local_path.glob("*"):
            key = f"{prefix}{f.name}"
            self.s3.upload_file(str(f), self.bucket, key)

        # Upload metadata
        meta = {
            "version": version,
            "uploaded_at": datetime.utcnow().isoformat(),
            "files": [f.name for f in local_path.glob("*")],
        }
        self.s3.put_object(
            Bucket=self.bucket,
            Key=f"{prefix}metadata.json",
            Body=json.dumps(meta),
        )

        return f"s3://{self.bucket}/{prefix}"

    def download_artifacts(self, version: str, local_dir: str = None) -> str:
        """Download model artifacts from S3 to local directory."""
        local_dir = local_dir or f"/tmp/ml/artifacts/{version}"
        local_path = Path(local_dir)
        local_path.mkdir(parents=True, exist_ok=True)

        prefix = f"models/{version}/"
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                filename = key.replace(prefix, "")
                if filename:  # Skip directory marker
                    target = local_path / filename
                    self.s3.download_file(self.bucket, key, str(target))

        self._local_cache[version] = local_dir
        return local_dir

    def get_latest_version(self) -> Optional[str]:
        """Get the most recent model version from S3."""
        versions = self.list_versions()
        return versions[0] if versions else None

    def list_versions(self) -> list:
        """List all model versions in S3."""
        versions = set()
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix="models/"):
            for obj in page.get("Contents", []):
                # Extract version from path: models/{version}/...
                parts = obj["Key"].split("/")
                if len(parts) >= 2:
                    versions.add(parts[1])
        return sorted(versions, reverse=True)

    def load_model(self, version: str = "latest"):
        """Load model + scaler from S3 (downloads if not cached)."""
        if version == "latest":
            version = self.get_latest_version()
            if not version:
                raise FileNotFoundError("No model versions found in S3")

        local_dir = self._local_cache.get(version)
        if not local_dir or not Path(local_dir).exists():
            local_dir = self.download_artifacts(version)

        local = Path(local_dir)
        model = joblib.load(local / "result_model.pkl") if (local / "result_model.pkl").exists() else None
        scaler = joblib.load(local / "scaler.pkl") if (local / "scaler.pkl").exists() else None

        return model, scaler, version


# Singleton
storage = S3ModelStorage()