"""
Navigation service for folder-aware navigation tree.

Generates and manages hierarchical navigation structure
mirroring the Git repository organization.
"""


from app.core.logging import get_logger
from app.schemas.navigation import NavigationNode, NavigationTree
from app.services.github_service import GitHubService

logger = get_logger(__name__)


class NavigationService:
    """
    Service for navigation tree operations.

    Generates hierarchical navigation structure from Git repository
    folder organization for intuitive document browsing.
    """

    def __init__(self) -> None:
        """Initialize navigation service."""
        self.github = GitHubService()

    async def build_navigation_tree(
        self,
        branch: str | None = None,
    ) -> NavigationTree:
        """
        Build complete navigation tree from repository.

        Args:
            branch: Branch name (defaults to main)

        Returns:
            Complete navigation tree
        """
        try:
            logger.info("Building navigation tree")

            # Get all files recursively
            files = await self.github.list_files(
                directory="",
                branch=branch,
                recursive=True,
            )

            # Build tree structure
            root = NavigationNode(
                id="root",
                label="Documentation",
                path="/",
                type="folder",
                children=[],
                order=0,
            )

            # Track folder nodes
            folders: dict[str, NavigationNode] = {"/": root}

            # Process each file
            for file_info in files:
                path = file_info["path"]
                parts = path.split("/")

                # Create folder nodes as needed
                current_path = ""
                for i, part in enumerate(parts[:-1]):  # Exclude filename
                    current_path = f"{current_path}/{part}" if current_path else part

                    if current_path not in folders:
                        folder_node = NavigationNode(
                            id=current_path,
                            label=part.replace("-", " ").replace("_", " ").title(),
                            path=current_path,
                            type="folder",
                            children=[],
                            order=i,
                        )

                        # Add to parent
                        parent_path = "/".join(parts[:i]) if i > 0 else "/"
                        if parent_path in folders:
                            folders[parent_path].children.append(folder_node)

                        folders[current_path] = folder_node

                # Create document node
                filename = parts[-1].replace(".md", "")
                doc_node = NavigationNode(
                    id=path,
                    label=filename.replace("-", " ").replace("_", " ").title(),
                    path=path,
                    type="document",
                    children=[],
                    order=len(parts) - 1,
                    metadata={"size": file_info["size"]},
                )

                # Add to parent folder
                parent_path = "/".join(parts[:-1]) if len(parts) > 1 else "/"
                if parent_path in folders:
                    folders[parent_path].children.append(doc_node)

            # Sort children in each folder
            self._sort_tree(root)

            # Count totals
            total_docs, total_folders = self._count_nodes(root)

            from datetime import datetime

            return NavigationTree(
                root=root,
                total_documents=total_docs,
                total_folders=total_folders,
                last_updated=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            logger.error(f"Error building navigation tree: {e}")
            raise

    def _sort_tree(self, node: NavigationNode) -> None:
        """
        Recursively sort tree nodes.

        Folders first (alphabetically), then documents (alphabetically).
        """
        # Sort children
        node.children.sort(key=lambda x: (x.type == "document", x.label.lower()))

        # Recursively sort children
        for child in node.children:
            if child.type == "folder":
                self._sort_tree(child)

    def _count_nodes(self, node: NavigationNode) -> tuple[int, int]:
        """
        Count documents and folders in tree.

        Returns:
            Tuple of (document count, folder count)
        """
        doc_count = 0
        folder_count = 0

        for child in node.children:
            if child.type == "document":
                doc_count += 1
            elif child.type == "folder":
                folder_count += 1
                child_docs, child_folders = self._count_nodes(child)
                doc_count += child_docs
                folder_count += child_folders

        return doc_count, folder_count

    async def get_breadcrumbs(self, path: str) -> list[dict[str, str]]:
        """
        Generate breadcrumb trail for a document path.

        Args:
            path: Document path

        Returns:
            List of breadcrumb items
        """
        breadcrumbs = [{"label": "Home", "path": "/"}]

        parts = path.split("/")
        current_path = ""

        for part in parts[:-1]:  # Exclude filename
            current_path = f"{current_path}/{part}" if current_path else part
            breadcrumbs.append({
                "label": part.replace("-", " ").replace("_", " ").title(),
                "path": current_path,
            })

        # Add current document
        if parts:
            filename = parts[-1].replace(".md", "")
            breadcrumbs.append({
                "label": filename.replace("-", " ").replace("_", " ").title(),
                "path": path,
            })

        return breadcrumbs
