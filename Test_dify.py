import requests
import json

class DifyAPI:
    def __init__(self, base_url="http://localhost:8088", api_key=None):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_document_from_text(self, dataset_id, name="text", text="text", indexing_technique="high_quality", use_parent_child=True):
        """Create a Document from Text with support for parent-child chunking"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/document/create-by-text"
        
        if use_parent_child:
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
                            "separator": "###PARENT_SECTION###",  # Parent chunk separator
                            "max_tokens": 4000,  # Larger for parent chunks
                            "chunk_overlap": 100  # More overlap for context
                        },
                        "subchunk_segmentation": {
                            "separator": "###CHILD_SECTION###",  # Child chunk separator
                            "max_tokens": 4000,  # Smaller for child chunks
                            "chunk_overlap": 50  # Some overlap for context
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
        
        return requests.post(url, headers=self.headers, json=data)
    
    def create_empty_knowledge_base(self, name, permission="only_me"):
        """Create an Empty Knowledge Base"""
        url = f"{self.base_url}/v1/datasets"
        data = {
            "name": name,
            "permission": permission
        }
        return requests.post(url, headers=self.headers, json=data)
    
    def get_knowledge_base_list(self, page=1, limit=20):
        """Get Knowledge Base List"""
        url = f"{self.base_url}/v1/datasets"
        params = {"page": page, "limit": limit}
        return requests.get(url, headers=self.headers, params=params)
    
    def create_knowledge_metadata(self, dataset_id, metadata_type="string", name="test"):
        """Create a Knowledge Metadata"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/metadata"
        data = {
            "type": metadata_type,
            "name": name
        }
        return requests.post(url, headers=self.headers, json=data)
    
    def update_knowledge_metadata(self, dataset_id, metadata_id, name="test"):
        """Update a Knowledge Metadata"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/metadata/{metadata_id}"
        data = {"name": name}
        return requests.patch(url, headers=self.headers, json=data)
    
    def create_knowledge_base_type_tag(self, name):
        """Create New Knowledge Base Type Tag"""
        url = f"{self.base_url}/v1/datasets/tags"
        data = {"name": name}
        return requests.post(url, headers=self.headers, json=data)
    
    def get_knowledge_base_type_tags(self):
        """Get Knowledge Base Type Tags"""
        url = f"{self.base_url}/v1/datasets/tags"
        return requests.get(url, headers=self.headers)
    
    def bind_dataset_to_tag(self, tag_ids, target_id):
        """Bind Dataset to Knowledge Base Type Tag"""
        url = f"{self.base_url}/v1/datasets/tags/binding"
        data = {
            "tag_ids": tag_ids,
            "target_id": target_id
        }
        return requests.post(url, headers=self.headers, json=data)
    
    def unbind_dataset_from_tag(self, tag_id, target_id):
        """Unbind Dataset and Knowledge Base Type Tag"""
        url = f"{self.base_url}/v1/datasets/tags/unbinding"
        data = {
            "tag_id": tag_id,
            "target_id": target_id
        }
        return requests.post(url, headers=self.headers, json=data)
    
    def get_document_list(self, dataset_id, page=1, limit=100):
        """Get list of documents in a dataset"""
        url = f"{self.base_url}/v1/datasets/{dataset_id}/documents"
        params = {"page": page, "limit": limit}
        return requests.get(url, headers=self.headers, params=params)


# Example usage:
if __name__ == "__main__":
    api = DifyAPI(api_key="your_api_key_here")
    
    # Create an empty knowledge base
    response = api.create_empty_knowledge_base("My Knowledge Base")
    print(response.json())
    
    # Get knowledge base list
    response = api.get_knowledge_base_list()
    print(response.json())
    
    # Create a tag
    response = api.create_knowledge_base_type_tag("testtag1")
    print(response.json())
    
    # Bind dataset to tags (example with sample IDs)
    tag_ids = ["65cc29be-d072-4e26-adf4-2f727644da29", "1e5348f3-d3ff-42b8-a1b7-0a86d518001a"]
    target_id = "a932ea9f-fae1-4b2c-9b65-71c56e2cacd6"
    response = api.bind_dataset_to_tag(tag_ids, target_id)
    print(response.json())