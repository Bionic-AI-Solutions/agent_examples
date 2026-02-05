"""Artifact Service - Manages artifact file storage and retrieval

Handles moving artifacts from temporary outputs/ to persistent artifacts/ storage.
"""

import shutil
from pathlib import Path
from loguru import logger


class ArtifactService:
    """Service for managing research artifacts (charts, reports, infographics)"""

    def __init__(self, storage_path: str = "/app/artifacts"):
        self.storage_path = Path(storage_path)
        self.outputs_path = Path(__file__).parent.parent.parent / "outputs"

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Artifact storage initialized at: {self.storage_path}")

    async def save_artifact_from_outputs(
        self, task_id: str, filename: str
    ) -> str:
        """
        Move artifact from outputs/ directory to persistent artifacts/ storage.

        Args:
            task_id: Unique task identifier
            filename: Name of the artifact file

        Returns:
            Relative path of the saved artifact

        Raises:
            FileNotFoundError: If the artifact doesn't exist in outputs/
        """
        try:
            source_path = self.outputs_path / filename

            if not source_path.exists():
                raise FileNotFoundError(
                    f"Artifact not found in outputs: {filename}"
                )

            # Create task-specific directory
            task_dir = self.storage_path / task_id
            task_dir.mkdir(parents=True, exist_ok=True)

            # Copy artifact to persistent storage
            dest_path = task_dir / filename
            shutil.copy2(source_path, dest_path)

            logger.info(f"Artifact saved: {dest_path}")

            # Return relative path for database storage
            return str(dest_path.relative_to(self.storage_path))

        except Exception as e:
            logger.error(f"Error saving artifact {filename}: {e}")
            raise

    async def save_all_artifacts(
        self, task_id: str, artifacts: dict
    ) -> dict:
        """
        Save multiple artifacts for a task.

        Args:
            task_id: Unique task identifier
            artifacts: Dict of artifact types to filenames

        Returns:
            Dict of artifact types to relative paths
        """
        saved_artifacts = {}

        for artifact_type, filename in artifacts.items():
            try:
                relative_path = await self.save_artifact_from_outputs(
                    task_id, filename
                )
                saved_artifacts[artifact_type] = filename
                logger.info(
                    f"Saved {artifact_type} artifact: {filename}"
                )
            except FileNotFoundError as e:
                logger.warning(
                    f"Artifact {artifact_type} not found: {filename}"
                )
            except Exception as e:
                logger.error(
                    f"Error saving {artifact_type} artifact: {e}"
                )

        return saved_artifacts

    async def get_artifact(self, task_id: str, filename: str) -> bytes:
        """
        Retrieve artifact file contents.

        Args:
            task_id: Unique task identifier
            filename: Name of the artifact file

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If the artifact doesn't exist
        """
        filepath = self.storage_path / task_id / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Artifact not found: {task_id}/{filename}")

        return filepath.read_bytes()

    async def artifact_exists(self, task_id: str, filename: str) -> bool:
        """
        Check if an artifact exists.

        Args:
            task_id: Unique task identifier
            filename: Name of the artifact file

        Returns:
            True if artifact exists, False otherwise
        """
        filepath = self.storage_path / task_id / filename
        return filepath.exists()

    async def delete_task_artifacts(self, task_id: str) -> None:
        """
        Delete all artifacts for a task.

        Args:
            task_id: Unique task identifier
        """
        task_dir = self.storage_path / task_id

        if task_dir.exists():
            shutil.rmtree(task_dir)
            logger.info(f"Deleted artifacts for task: {task_id}")
