"""
Resilient Dify API Client

This is an enhanced version of DifyAPI with built-in retry logic,
circuit breaker, and error handling.
"""

import requests
import json
import logging
import os
import sys
from typing import Optional
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.resilience_utils import with_retry, RetryConfig, CircuitBreaker

logger = logging.getLogger(__name__)


class ResilientDifyAPI:
    """Dify API client with built-in resilience features"""

    def __init__(
        self,
        base_url: str = "http://localhost:8088",
        api_key: Optional[str] = None,
        enable_retry: bool = True,
        enable_circuit_breaker: bool = True,
        retry_config: Optional[RetryConfig] = None
    ):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # Resilience configuration
        self.enable_retry = enable_retry
        self.enable_circuit_breaker = enable_circuit_breaker

        if retry_config is None:
            self.retry_config = RetryConfig(
                max_attempts=3,
                initial_delay=2.0,
                max_delay=30.0,
                exponential_base=2.0
            )
        else:
            self.retry_config = retry_config

        # Circuit breakers per endpoint type
        self.circuit_breakers = {
            'kb_creation': CircuitBreaker(failure_threshold=5, recovery_timeout=60.0),
            'doc_creation': CircuitBreaker(failure_threshold=5, recovery_timeout=60.0),
            'metadata': CircuitBreaker(failure_threshold=5, recovery_timeout=60.0),
            'retrieval': CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
        }

    def _make_request(
        self,
        method: str,
        url: str,
        circuit_key: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> requests.Response:
        """Make HTTP request with resilience features"""

        def _execute_request():
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=json_data)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=json_data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Raise for HTTP errors (4xx, 5xx)
            response.raise_for_status()
            return response

        # Apply circuit breaker if enabled
        if self.enable_circuit_breaker:
            breaker = self.circuit_breakers.get(circuit_key)
            if breaker:
                try:
                    return breaker.call(_execute_request)
                except Exception as e:
                    logger.error(f"Circuit breaker triggered for {circuit_key}: {e}")
                    raise
            else:
                return _execute_request()
        else:
            return _execute_request()

    # ========================================================================
    # KNOWLEDGE BASE OPERATIONS
    # ========================================================================

    @with_retry()
    def create_empty_knowledge_base(self, name: str, permission: str = "only_me") -> requests.Response:
        """Create an Empty Knowledge Base with retry"""
        url = f"{self.base_url}/v1/datasets"
        data = {"name": name, "permission": permission}

        logger.info(f"Creating knowledge base: {name}")
        response = self._make_request('POST', url, 'kb_creation', json_data=data)
        logger.info(f"✅ Knowledge base created: {name}")
        return response

    @with_retry()
    def get_knowledge_base_list(self, page: int = 1, limit: int = 20) -> requests.Response:
        """Get Knowledge Base List with retry"""
        url = f"{self.base_url}/v1/datasets"
        params = {"page": page, "limit": limit}

        response = self._make_request('GET', url, 'retrieval', params=params)
        return response

    @with_retry()
    def delete_knowledge_base(self, dataset_id: str) -> requests.Response:
        """Delete a knowledge base with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}"

        logger.info(f"Deleting knowledge base: {dataset_id}")
        response = self._make_request('DELETE', url, 'kb_creation')
        logger.info(f"✅ Knowledge base deleted: {dataset_id}")
        return response

    # ========================================================================
    # DOCUMENT OPERATIONS
    # ========================================================================

    @with_retry()
    def create_document_from_text(
        self,
        dataset_id: str,
        name: str = "text",
        text: str = "text",
        indexing_technique: str = "high_quality",
        use_parent_child: bool = True,
        custom_config: Optional[dict] = None
    ) -> requests.Response:
        """Create a Document from Text with retry and parent-child chunking support"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/document/create-by-text"

        # Use custom configuration if provided
        if custom_config:
            data = {
                "name": name,
                "text": text,
                "indexing_technique": indexing_technique,
                **custom_config
            }
        elif use_parent_child:
            # Parent-child hierarchical chunking configuration
            data = {
                "name": name,
                "text": text,
                "indexing_technique": indexing_technique,
                "doc_form": "hierarchical_model",
                "process_rule": {
                    "mode": "hierarchical",
                    "rules": {
                        "pre_processing_rules": [
                            {"id": "remove_extra_spaces", "enabled": False},
                            {"id": "remove_urls_emails", "enabled": False}
                        ],
                        "parent_mode": "paragraph",
                        "segmentation": {
                            "separator": "###PARENT_SECTION###",
                            "max_tokens": 4000,
                            "chunk_overlap": 100
                        },
                        "subchunk_segmentation": {
                            "separator": "###CHILD_SECTION###",
                            "max_tokens": 4000,
                            "chunk_overlap": 50
                        }
                    },
                }
            }
        else:
            # Traditional flat chunking configuration
            data = {
                "name": name,
                "text": text,
                "indexing_technique": indexing_technique,
                "doc_form": "text_model",
                "process_rule": {
                    "mode": "custom",
                    "rules": {
                        "pre_processing_rules": [
                            {"id": "remove_extra_spaces", "enabled": False},
                            {"id": "remove_urls_emails", "enabled": False}
                        ],
                        "segmentation": {
                            "separator": "###SECTION_BREAK###",
                            "max_tokens": 1024,
                            "chunk_overlap": 50
                        }
                    }
                }
            }

        logger.debug(f"Creating document: {name} in KB {dataset_id}")
        response = self._make_request('POST', url, 'doc_creation', json_data=data)
        logger.debug(f"✅ Document created: {name}")
        return response

    @with_retry()
    def update_document_by_text(
        self,
        dataset_id: str,
        document_id: str,
        name: Optional[str] = None,
        text: Optional[str] = None,
        indexing_technique: str = "high_quality",
        custom_config: Optional[dict] = None
    ) -> requests.Response:
        """Update a document by text with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/documents/{document_id}/update_by_text"

        data = {
            "indexing_technique": indexing_technique
        }

        if name:
            data["name"] = name
        if text:
            data["text"] = text
        if custom_config:
            data.update(custom_config)

        logger.info(f"Updating document: {document_id}")
        response = self._make_request('POST', url, 'doc_creation', json_data=data)
        logger.info(f"✅ Document updated: {document_id}")
        return response

    @with_retry()
    def get_document_list(self, dataset_id: str, page: int = 1, limit: int = 100) -> requests.Response:
        """Get list of documents in a dataset with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/documents"
        params = {"page": page, "limit": limit}

        response = self._make_request('GET', url, 'retrieval', params=params)
        return response

    @with_retry()
    def delete_document(self, dataset_id: str, document_id: str) -> requests.Response:
        """Delete a document with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/documents/{document_id}"

        logger.info(f"Deleting document: {document_id}")
        response = self._make_request('DELETE', url, 'doc_creation')
        logger.info(f"✅ Document deleted: {document_id}")
        return response

    @with_retry()
    def get_indexing_status(self, dataset_id: str, batch: str) -> requests.Response:
        """Get indexing status for a document batch with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/documents/{batch}/indexing-status"

        response = self._make_request('GET', url, 'retrieval')
        return response

    # ========================================================================
    # METADATA OPERATIONS
    # ========================================================================

    @with_retry()
    def create_knowledge_metadata(
        self,
        dataset_id: str,
        metadata_type: str = "string",
        name: str = "test"
    ) -> requests.Response:
        """Create a Knowledge Metadata with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/metadata"
        data = {"type": metadata_type, "name": name}

        response = self._make_request('POST', url, 'metadata', json_data=data)
        return response

    @with_retry()
    def update_knowledge_metadata(
        self,
        dataset_id: str,
        metadata_id: str,
        name: str = "test"
    ) -> requests.Response:
        """Update a Knowledge Metadata with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/metadata/{metadata_id}"
        data = {"name": name}

        response = self._make_request('PATCH', url, 'metadata', json_data=data)
        return response

    @with_retry()
    def get_metadata_list(self, dataset_id: str) -> requests.Response:
        """Get metadata list for a knowledge base with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/metadata"

        response = self._make_request('GET', url, 'retrieval')
        return response

    @with_retry()
    def delete_metadata(self, dataset_id: str, metadata_id: str) -> requests.Response:
        """Delete a metadata field with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/metadata/{metadata_id}"

        response = self._make_request('DELETE', url, 'metadata')
        return response

    @with_retry()
    def assign_document_metadata(
        self,
        dataset_id: str,
        document_id: str,
        metadata_list: list
    ) -> requests.Response:
        """Assign metadata to a document with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/documents/metadata"
        data = {
            "operation_data": [
                {
                    "document_id": document_id,
                    "metadata_list": metadata_list
                }
            ]
        }

        response = self._make_request('POST', url, 'metadata', json_data=data)
        return response

    # ========================================================================
    # RETRIEVAL OPERATIONS
    # ========================================================================

    @with_retry()
    def retrieve(self, dataset_id: str, query: str, top_k: int = 5) -> requests.Response:
        """Retrieve documents from knowledge base with retry"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/retrieve"
        data = {
            "query": query,
            "retrieval_model": {
                "top_k": top_k
            }
        }

        response = self._make_request('POST', url, 'retrieval', json_data=data)
        return response

    # ========================================================================
    # TAG OPERATIONS
    # ========================================================================

    @with_retry()
    def create_knowledge_base_type_tag(self, name: str) -> requests.Response:
        """Create New Knowledge Base Type Tag with retry"""
        url = f"{self.base_url}/v1/datasets/tags"
        data = {"name": name}

        response = self._make_request('POST', url, 'metadata', json_data=data)
        return response

    @with_retry()
    def get_knowledge_base_type_tags(self) -> requests.Response:
        """Get Knowledge Base Type Tags with retry"""
        url = f"{self.base_url}/v1/datasets/tags"

        response = self._make_request('GET', url, 'retrieval')
        return response

    @with_retry()
    def bind_dataset_to_tag(self, tag_ids: list, target_id: str) -> requests.Response:
        """Bind Dataset to Knowledge Base Type Tag with retry"""
        url = f"{self.base_url}/v1/datasets/tags/binding"
        data = {"tag_ids": tag_ids, "target_id": target_id}

        response = self._make_request('POST', url, 'metadata', json_data=data)
        return response

    @with_retry()
    def unbind_dataset_from_tag(self, tag_id: str, target_id: str) -> requests.Response:
        """Unbind Dataset and Knowledge Base Type Tag with retry"""
        url = f"{self.base_url}/v1/datasets/tags/unbinding"
        data = {"tag_id": tag_id, "target_id": target_id}

        response = self._make_request('POST', url, 'metadata', json_data=data)
        return response


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create resilient API client
    api = ResilientDifyAPI(
        base_url="http://localhost:8088",
        api_key="your_api_key_here",
        enable_retry=True,
        enable_circuit_breaker=True
    )

    try:
        # This will automatically retry on failures
        response = api.get_knowledge_base_list()
        print(f"Success: {response.status_code}")
    except Exception as e:
        print(f"Failed after retries: {e}")
